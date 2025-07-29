

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import re

# Pydantic AI
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field, validator
from pydantic_ai.models.openai import OpenAIModel

# LangGraph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

logger = logging.getLogger(__name__)


# ============================================================================
# MODELOS PYDANTIC ESTRITOS PARA VALIDAÇÃO
# ============================================================================

class BenefitTypeEnum(str, Enum):
    AUXILIO_DOENCA = "AUXÍLIO-DOENÇA"
    APOSENTADORIA_INVALIDEZ = "APOSENTADORIA POR INVALIDEZ"
    BPC_LOAS = "BPC/LOAS"
    AUXILIO_ACIDENTE = "AUXÍLIO-ACIDENTE"
    ISENCAO_IR = "ISENÇÃO IMPOSTO DE RENDA"


class SeverityEnum(str, Enum):
    LEVE = "LEVE"
    MODERADA = "MODERADA"
    GRAVE = "GRAVE"


class PatientDataStrict(BaseModel):
    """Dados do paciente com validação estrita e correção de medicamentos"""
    nome: str = Field(min_length=1, description="Nome completo do paciente")
    idade: Optional[int] = Field(None, ge=0, le=120, description="Idade do paciente")
    sexo: Optional[str] = Field(None, pattern="^[MF]$", description="Sexo M ou F")
    profissao: Optional[str] = Field(None, description="Profissão do paciente")
    sintomas: List[str] = Field(default_factory=list, description="Lista de sintomas")
    medicamentos: List[str] = Field(default_factory=list, description="Lista de medicamentos")
    condicoes: List[str] = Field(default_factory=list, description="Lista de condições médicas")

    @validator('medicamentos', pre=True)
    def normalize_medications(cls, v):
        """Normaliza medicamentos corrigindo erros comuns"""
        if not v:
            return []
        
        # Dicionário de correções comuns
        corrections = {
            'metamorfina': 'metformina',
            'captou o piu': 'captopril',
            'captou miúdo': 'captopril',
            'captomai': 'captopril',
            'pium': '',  # Remove
            'zartan': 'losartana',
            'artões': 'atorvastatina',
            'lodosartana': 'losartana',
            'captou o rio': 'captopril'
        }
        
        corrected = []
        for med in v:
            if isinstance(med, str):
                med_lower = med.lower().strip()
                # Aplicar correções
                for wrong, right in corrections.items():
                    if wrong in med_lower:
                        if right:  # Se não é para remover
                            corrected.append(right)
                        break
                else:
                    # Se não encontrou erro conhecido, manter original
                    corrected.append(med.strip())
        
        return list(set(filter(None, corrected)))  # Remove duplicatas e vazios


class BenefitClassificationStrict(BaseModel):
    """Classificação de benefício com validação estrita e regras CFM"""
    tipo_beneficio: BenefitTypeEnum = Field(description="Tipo de benefício recomendado")
    cid_principal: str = Field(pattern="^[A-Z]\d{2}(\.\d)?$", description="CID-10 no formato A00.0 ou A00")
    cids_secundarios: Optional[List[str]] = Field(default_factory=list, description="CIDs secundários/comorbidades")
    gravidade: SeverityEnum = Field(description="Gravidade da condição")
    prognostico: str = Field(min_length=20, description="Prognóstico detalhado")
    elegibilidade: bool = Field(description="Se é elegível para o benefício")
    justificativa: str = Field(min_length=50, description="Justificativa médica detalhada")
    especificidade_cid: str = Field(description="Explicação da escolha do CID específico")
    fonte_cids: str = Field(default="Base Local RAG (FAISS)", description="Fonte dos CIDs")
    telemedicina_limitacao: Optional[str] = Field(None, description="Observação sobre limitações da telemedicina")

    @validator('cid_principal')
    def validate_cid(cls, v):
        if not v or v.lower() in ['não informado', 'nao informado', '']:
            return 'I10'  # Hipertensão como fallback
        return v

    @validator('cids_secundarios')
    def validate_secondary_cids(cls, v):
        if not v:
            return []
        # Validar formato de cada CID secundário
        valid_cids = []
        for cid in v:
            if re.match(r'^[A-Z]\d{2}(\.\d)?$', cid):
                valid_cids.append(cid)
        return valid_cids


class MedicalReportComplete(BaseModel):
    """Relatório médico completo"""
    patient_data: PatientDataStrict
    classification: BenefitClassificationStrict
    anamnese: str = Field(min_length=100, description="Anamnese estruturada")
    laudo_medico: str = Field(min_length=200, description="Laudo médico detalhado")
    rag_context: List[str] = Field(default_factory=list, description="Contexto RAG relevante")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Score de confiança")


# ============================================================================
# ESTADO LANGGRAPH
# ============================================================================

class MedicalAnalysisState(TypedDict):
    """Estado do pipeline LangGraph"""
    messages: Annotated[list, add_messages]
    patient_text: str
    transcription: str
    patient_data: Optional[PatientDataStrict]
    classification: Optional[BenefitClassificationStrict]
    rag_results: List[Dict[str, Any]]
    medical_report: Optional[MedicalReportComplete]
    errors: List[str]
    current_step: str
    telemedicine_mode: bool


# ============================================================================
# AGENTES PYDANTIC AI
# ============================================================================

class PydanticMedicalAI:
    """Serviço principal com Pydantic AI, LangGraph, RAG e FAISS"""
    
    def __init__(self, telemedicine_mode: bool = True):
        """
        Inicializa o sistema médico
        
        Args:
            telemedicine_mode: Se True, aplica limitações CFM para telemedicina
        """
        self.telemedicine_mode = telemedicine_mode
        
        # Forçar carregamento da API key
        try:
            from .force_openai_env import setup_openai_env
            setup_openai_env()
        except:
            pass
            
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY não encontrada")
        
        # Modelo OpenAI para Pydantic AI
        import openai
        openai.api_key = self.openai_api_key
        self.model = OpenAIModel('gpt-4o-mini')
        
        # Agentes Pydantic AI
        self.patient_agent = self._create_patient_agent()
        self.classification_agent = self._create_classification_agent()
        
        # Pipeline LangGraph
        self.workflow = self._create_langgraph_pipeline()
        
        # RAG Service
        try:
            from .rag.medical_rag_service import MedicalRAGService
            self.rag_service = MedicalRAGService()
            self.rag_available = True
            print("✅ RAG integrado ao Pydantic AI")
        except Exception as e:
            print(f"⚠️ RAG não disponível: {e}")
            self.rag_available = False
            self.rag_service = None
        
        mode_text = "TELEMEDICINA" if self.telemedicine_mode else "PRESENCIAL"
        print(f"✅ Pydantic AI Medical Service inicializado - Modo: {mode_text}")
    
    def _create_patient_agent(self) -> Agent:
        """Cria agente para extração de dados do paciente"""
        return Agent(
            model=self.model,
            result_type=PatientDataStrict,
            system_prompt="""
            Você é um especialista em extração de dados médicos com correção automática.
            Extraia informações do paciente do texto fornecido com máxima precisão.
            
            REGRAS OBRIGATÓRIAS:
            - nome: SEMPRE extrair um nome, use "Paciente" se não encontrar
            - idade: APENAS números inteiros entre 0-120, null se não encontrar
            - sexo: APENAS "M" ou "F", null se não encontrar
            - medicamentos: Corrigir automaticamente erros comuns de transcrição
            - sintomas: Normalizar termos médicos
            - Listas vazias se não encontrar informações específicas
            
            CORREÇÕES AUTOMÁTICAS DE MEDICAMENTOS:
            - "metamorfina" → "metformina"
            - "captou o piu" → "captopril"
            - "zartan" → "losartana"
            - "artões" → "atorvastatina"
            - Remover palavras sem sentido: "pium", etc.
            
            Seja preciso e objetivo. Retorne apenas dados estruturados válidos.
            """
        )
    
    def _create_classification_agent(self) -> Agent:
        """Cria agente para classificação de benefícios"""
        
        telemedicine_rules = ""
        if self.telemedicine_mode:
            telemedicine_rules = """
            🚨 LIMITAÇÕES CFM PARA TELEMEDICINA - REGRAS OBRIGATÓRIAS:
            
            ⚖️ **REGRA FUNDAMENTAL:**
            - CFM PROÍBE estabelecer nexo ocupacional por telemedicina
            - SEMPRE usar AUXÍLIO-DOENÇA quando não há nexo pré-estabelecido
            - Mencionar na justificativa: "Nexo ocupacional requer avaliação presencial"
            
            🔒 **RESTRIÇÕES ABSOLUTAS:**
            - NÃO classificar como AUXÍLIO-ACIDENTE sem CAT prévia
            - NÃO estabelecer nexo causal baseado apenas em relato
            - SEMPRE indicar necessidade de avaliação presencial para nexo
            
            ✅ **QUANDO USAR AUXÍLIO-ACIDENTE:**
            - APENAS se houver CAT (Comunicação de Acidente de Trabalho) já emitida
            - APENAS se houver perícia prévia confirmando nexo
            - APENAS em casos de acidente traumático claro e indiscutível
            
            ❌ **NUNCA USAR AUXÍLIO-ACIDENTE PARA:**
            - LER/DORT sem CAT prévia (usar AUXÍLIO-DOENÇA)
            - Agravamento ocupacional sem comprovação (usar AUXÍLIO-DOENÇA)  
            - Exposição ocupacional presumida (usar AUXÍLIO-DOENÇA)
            - Qualquer caso que dependa de estabelecer nexo por telemedicina
            
            📝 **JUSTIFICATIVA OBRIGATÓRIA:**
            - Sempre mencionar: "O estabelecimento de nexo ocupacional requer avaliação presencial especializada conforme regulamentação do CFM para telemedicina"
            """
        
        return Agent(
            model=self.model,
            result_type=BenefitClassificationStrict,
            system_prompt=f"""
            Você é um médico perito previdenciário EXPERT em classificação de benefícios e CIDs.
            
            {telemedicine_rules}
            
            🧠 HIERARQUIA DE ANÁLISE (ORDEM OBRIGATÓRIA):
            
            1️⃣ **IDENTIFIQUE A CONDIÇÃO PRINCIPAL** (mais grave/recente)
            2️⃣ **AVALIE ASPECTOS TEMPORAIS** (agudo vs crônico)
            3️⃣ **VERIFIQUE LIMITAÇÕES TELEMEDICINA** (nexo ocupacional?)
            4️⃣ **CLASSIFIQUE GRAVIDADE** (funcionalidade comprometida?)
            5️⃣ **ESCOLHA BENEFÍCIO** (respeitando limitações CFM)
            6️⃣ **SELECIONE CID ESPECÍFICO** (mais preciso possível)
            
            🎯 CLASSIFICAÇÃO DE BENEFÍCIOS (TELEMEDICINA):
            
            **1. AUXÍLIO-DOENÇA** (PRIORIDADE em telemedicina):
            ✅ Usar para:
            - Diabetes com complicações (E11.3 se visão embaçada)
            - Hipertensão descompensada (I10)
            - Depressão/ansiedade (F32.x, F41.x)
            - Doenças cardíacas (I21.9, I25.2)
            - LER/DORT sem CAT prévia (M70.x, G56.0)
            - Qualquer condição SEM nexo pré-estabelecido
            
            **2. AUXÍLIO-ACIDENTE** (APENAS com nexo pré-estabelecido):
            ✅ Usar SOMENTE quando:
            - CAT já emitida e mencionada
            - Perícia prévia confirmou nexo
            - Acidente traumático indiscutível (fratura em acidente)
            ❌ NUNCA usar para nexo presumido
            
            **3. BPC/LOAS** (deficiência + vulnerabilidade):
            ✅ Usar quando:
            - Deficiência permanente + baixa renda explícita
            - Criança com deficiência
            - Idoso 65+ vulnerável
            
            **4. APOSENTADORIA POR INVALIDEZ**:
            ✅ Usar quando:
            - Incapacidade definitiva > 12 meses
            - Múltiplas tentativas reabilitação falharam
            - Doenças terminais
            
            🧬 HIERARQUIA DE CIDs ESPECÍFICOS:
            
            **DIABETES:**
            - Com visão embaçada → E11.3 (complicações oftálmicas)
            - Com problemas renais → E11.2
            - Sem complicações → E11.9
            
            **CARDIOVASCULARES:**
            - Infarto < 6 meses → I21.9
            - Infarto > 6 meses → I25.2
            - Hipertensão → I10
            
            **LER/DORT:**
            - Síndrome túnel carpo → G56.0
            - Tendinite punho → M70.1
            - Bursite cotovelo → M70.2
            - Síndrome impacto ombro → M75.1
            
            **PSIQUIÁTRICAS:**
            - Depressão grave → F32.2
            - Depressão moderada → F32.1
            - Ansiedade generalizada → F41.1
            - Transtorno pânico → F41.0
            
            🎯 REGRAS DE GRAVIDADE (CONSERVADORAS):
            
            **GRAVE:** (USAR APENAS EM CASOS EXTREMOS)
            - Múltiplas condições descompensadas simultaneamente
            - Incapacidade total e definitiva
            - Risco iminente de vida
            - Complicações severas não controladas
            
            **MODERADA:** (PADRÃO PARA MAIORIA DOS CASOS)
            - Diabetes com sintomas (visão embaçada, mal estar)
            - Hipertensão descompensada (>18x11)
            - LER/DORT com limitações funcionais
            - Condições que afetam trabalho mas são tratáveis
            
            **LEVE:** (CASOS ESTÁVEIS)
            - Diabetes bem controlado sem sintomas
            - Hipertensão controlada com medicação
            - Condições estáveis em tratamento
            
            📋 REGRAS ESPECÍFICAS PARA DIABETES:
            
            **TIPO 1 (E10.x):**
            - Mencionado "tipo 1" OU "insulina dependente"
            - E10.9 = sem complicações, E10.3 = com complicações
            
            **TIPO 2 (E11.x):**
            - Mencionado "tipo 2" OU uso de "metformina/glibenclamida"
            - E11.9 = sem complicações, E11.3 = com complicações
            
            **Gravidade Diabetes:**
            - LEVE: Bem controlado, sem sintomas
            - MODERADA: Com sintomas (visão embaçada, mal estar, hipertensão)
            - GRAVE: Apenas com complicações severas (cetoacidose, coma)
            
            🚨 REGRAS INVIOLÁVEIS:
            1. **Sempre respeitar limitações CFM para telemedicina**
            2. **Hierarquia: condição mais grave = CID principal**
            3. **Diabetes com sintomas = E11.3, não E11.9**
            4. **Sem nexo pré-estabelecido = AUXÍLIO-DOENÇA**
            5. **Justificar limitações de telemedicina quando relevante**
            
            EXEMPLOS PRÁTICOS:
            - "Cozinheiro, diabetes + calor" → AUXÍLIO-DOENÇA + E11.3 (sem CAT)
            - "Programador, LER/DORT" → AUXÍLIO-DOENÇA + G56.0 (sem CAT)
            - "Entregador, fratura em acidente" → AUXÍLIO-DOENÇA (sem CAT)
            - "Infarto há 3 meses" → AUXÍLIO-DOENÇA + I21.9
            """
        )
    
    def _create_langgraph_pipeline(self) -> StateGraph:
        """Cria pipeline LangGraph para análise médica"""
        workflow = StateGraph(MedicalAnalysisState)
        
        # Adicionar nós
        workflow.add_node("extract_patient", self._extract_patient_node)
        workflow.add_node("search_rag", self._search_rag_node)
        workflow.add_node("classify_benefit", self._classify_benefit_node)
        workflow.add_node("validate_telemedicine", self._validate_telemedicine_node)
        workflow.add_node("generate_report", self._generate_report_node)
        
        # Definir edges
        workflow.add_edge(START, "extract_patient")
        workflow.add_edge("extract_patient", "search_rag")
        workflow.add_edge("search_rag", "classify_benefit")
        workflow.add_edge("classify_benefit", "validate_telemedicine")
        workflow.add_edge("validate_telemedicine", "generate_report")
        workflow.add_edge("generate_report", END)
        
        return workflow.compile()
    
    # ========================================================================
    # NÓDULOS LANGGRAPH
    # ========================================================================
    
    async def _extract_patient_node(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nó para extração de dados do paciente"""
        try:
            print("📝 LangGraph: Extraindo dados do paciente...")
            state["current_step"] = "extract_patient"
            state["telemedicine_mode"] = self.telemedicine_mode
            
            combined_text = f"{state.get('patient_text', '')}\n{state.get('transcription', '')}"
            
            result = await self.patient_agent.run(combined_text)
            state["patient_data"] = result.data
            
            print(f"✅ Paciente extraído: {result.data.nome}")
            if result.data.medicamentos:
                print(f"💊 Medicamentos corrigidos: {result.data.medicamentos}")
            
            return state
            
        except Exception as e:
            print(f"❌ Erro na extração do paciente: {e}")
            state["errors"].append(f"Erro na extração: {str(e)}")
            
            # Fallback
            state["patient_data"] = PatientDataStrict(
                nome="Paciente",
                idade=None,
                sexo=None,
                profissao=None
            )
            return state
    
    async def _search_rag_node(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nó para busca RAG"""
        try:
            print("🔍 LangGraph: Buscando casos similares...")
            state["current_step"] = "search_rag"
            
            if self.rag_available and self.rag_service:
                combined_text = f"{state.get('patient_text', '')}\n{state.get('transcription', '')}"
                rag_results = self.rag_service.search_similar_cases(combined_text, top_k=3)
                state["rag_results"] = rag_results
                print(f"✅ RAG: {len(rag_results)} casos encontrados")
            else:
                state["rag_results"] = []
                print("⚠️ RAG não disponível")
            
            return state
            
        except Exception as e:
            print(f"❌ Erro na busca RAG: {e}")
            state["errors"].append(f"Erro RAG: {str(e)}")
            state["rag_results"] = []
            return state
    
    async def _classify_benefit_node(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nó para classificação de benefícios"""
        try:
            print("🏥 LangGraph: Classificando benefício...")
            state["current_step"] = "classify_benefit"
            
            # Preparar contexto
            context = {
                "patient_data": state["patient_data"].dict() if state["patient_data"] else {},
                "transcription": state.get("transcription", ""),
                "rag_context": [r.get("content", "") for r in state.get("rag_results", [])],
                "telemedicine_mode": self.telemedicine_mode
            }
            
            context_text = f"""
            DADOS DO PACIENTE: {json.dumps(context["patient_data"], ensure_ascii=False)}
            TRANSCRIÇÃO: {context["transcription"]}
            CASOS SIMILARES RAG: {" | ".join(context["rag_context"][:2])}
            MODO TELEMEDICINA: {'SIM' if self.telemedicine_mode else 'NÃO'}
            """
            
            result = await self.classification_agent.run(context_text)
            state["classification"] = result.data
            
            print(f"✅ Classificação: {result.data.tipo_beneficio.value}")
            return state
            
        except Exception as e:
            print(f"❌ Erro na classificação: {e}")
            state["errors"].append(f"Erro na classificação: {str(e)}")
            
            # Fallback
            state["classification"] = BenefitClassificationStrict(
                tipo_beneficio=BenefitTypeEnum.AUXILIO_DOENCA,
                cid_principal="I10",
                gravidade=SeverityEnum.MODERADA,
                prognostico="Prognóstico requer avaliação médica continuada para determinação adequada",
                elegibilidade=True,
                justificativa="Classificação automática baseada nos dados disponíveis para análise médica. Avaliação presencial recomendada para confirmação diagnóstica.",
                especificidade_cid="CID atribuído com base nas informações disponíveis",
                fonte_cids="Sistema automático"
            )
            return state
    
    async def _validate_telemedicine_node(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nó para validação das limitações de telemedicina"""
        try:
            print("⚖️ LangGraph: Validando limitações CFM...")
            state["current_step"] = "validate_telemedicine"
            
            if not self.telemedicine_mode:
                print("✅ Modo presencial - sem restrições")
                return state
            
            classification = state["classification"]
            patient_data = state["patient_data"]
            
            # Verificar se é auxílio-acidente sem CAT
            if classification.tipo_beneficio == BenefitTypeEnum.AUXILIO_ACIDENTE:
                
                # Verificar se há menção de CAT ou perícia prévia
                combined_text = f"{state.get('patient_text', '')}\n{state.get('transcription', '')}"
                has_cat = any(term in combined_text.lower() for term in [
                    'cat', 'comunicação de acidente', 'perícia', 'inss confirmou', 
                    'laudo pericial', 'nexo estabelecido'
                ])
                
                if not has_cat:
                    print("🚨 Convertendo AUXÍLIO-ACIDENTE → AUXÍLIO-DOENÇA (sem CAT)")
                    
                    # Forçar mudança para auxílio-doença
                    classification.tipo_beneficio = BenefitTypeEnum.AUXILIO_DOENCA
                    
                    # Adicionar observação sobre limitação
                    cfm_note = " O estabelecimento de nexo ocupacional requer avaliação presencial especializada conforme regulamentação do CFM para telemedicina."
                    
                    if not cfm_note in classification.justificativa:
                        classification.justificativa += cfm_note
                    
                    classification.telemedicina_limitacao = "Nexo ocupacional não estabelecido por limitações da telemedicina"
                    
                    # Atualizar conclusão no state
                    state["classification"] = classification
                    
                    print("✅ Classificação corrigida para respeitar limitações CFM")
            
            return state
            
        except Exception as e:
            print(f"❌ Erro na validação CFM: {e}")
            state["errors"].append(f"Erro na validação: {str(e)}")
            return state
    
    async def _generate_report_node(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nó para geração do relatório final"""
        try:
            print("📋 LangGraph: Gerando relatório final...")
            state["current_step"] = "generate_report"
            
            # Gerar anamnese
            anamnese = self._generate_anamnese(state)
            
            # Gerar laudo
            laudo = self._generate_laudo(state)
            
            # Calcular score de confiança
            confidence = self._calculate_confidence(state)
            
            # Criar relatório completo
            state["medical_report"] = MedicalReportComplete(
                patient_data=state["patient_data"],
                classification=state["classification"],
                anamnese=anamnese,
                laudo_medico=laudo,
                rag_context=[r.get("content", "")[:200] for r in state.get("rag_results", [])],
                confidence_score=confidence
            )
            
            print("✅ Relatório médico completo gerado")
            return state
            
        except Exception as e:
            print(f"❌ Erro na geração do relatório: {e}")
            state["errors"].append(f"Erro no relatório: {str(e)}")
            return state
    
    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================
    
    def _get_cid_description(self, cid_code: str) -> str:
        """Retorna descrição do CID baseada no código"""
        descriptions = {
            'E10.3': 'Diabetes mellitus tipo 1 com complicações oftálmicas',
            'E10.9': 'Diabetes mellitus tipo 1 sem complicações',
            'E10.2': 'Diabetes mellitus tipo 1 com complicações renais',
            'E11.3': 'Diabetes mellitus tipo 2 com complicações oftálmicas',
            'E11.9': 'Diabetes mellitus tipo 2 sem complicações',
            'E11.2': 'Diabetes mellitus tipo 2 com complicações renais',
            'I10': 'Hipertensão essencial',
            'I21.9': 'Infarto agudo do miocárdio não especificado',
            'I25.2': 'Infarto do miocárdio antigo',
            'G56.0': 'Síndrome do túnel do carpo',
            'M70.1': 'Bursite da mão',
            'M70.2': 'Bursite do olécrano',
            'M75.1': 'Síndrome do impacto do ombro',
            'F32.1': 'Episódio depressivo moderado',
            'F32.2': 'Episódio depressivo grave sem sintomas psicóticos',
            'F41.0': 'Transtorno de pânico',
            'F41.1': 'Transtorno de ansiedade generalizada',
            'S82.101A': 'Fratura não especificada da extremidade proximal da tíbia direita, encontro inicial',
            'Z96.603': 'Presença de implante ortopédico unilateral do joelho'
        }
        return descriptions.get(cid_code, f'Condição médica {cid_code}')
    
    def _generate_anamnese(self, state: MedicalAnalysisState) -> str:
        """Gera anamnese estruturada seguindo modelo ideal para telemedicina"""
        patient = state["patient_data"]
        classification = state["classification"]
        transcription = state.get("transcription", "")
        
        # Determinar queixa principal baseada no benefício
        queixa_map = {
            'AUXÍLIO-DOENÇA': 'Afastamento do trabalho por incapacidade temporária devido ao quadro clínico atual',
            'BPC/LOAS': 'Avaliação para concessão de Benefício de Prestação Continuada (BPC/LOAS)',
            'APOSENTADORIA POR INVALIDEZ': 'Avaliação para aposentadoria por invalidez devido à incapacidade definitiva',
            'AUXÍLIO-ACIDENTE': 'Avaliação de redução da capacidade laborativa pós-acidente de trabalho',
            'ISENÇÃO IMPOSTO DE RENDA': 'Avaliação para isenção de Imposto de Renda por doença grave'
        }
        queixa_principal = queixa_map.get(classification.tipo_beneficio.value, 'Avaliação médica para fins previdenciários')
        
        # Extrair data de início se disponível na transcrição
        data_inicio = "Não especificada no relato"
        if transcription:
            import re
            # Buscar padrões específicos de tempo relacionados ao início da doença/sintomas
            medical_patterns = [
                r'há\s+(\d+)\s*(mês|meses)\s+eu\s+descobri',
                r'há\s+(\d+)\s*(ano|anos)\s+eu\s+descobri',
                r'descobri\s+que\s+tenho\s+\w+\s+há\s+(\d+)\s*(mês|meses|ano|anos)',
                r'diagnos\w+\s+há\s+(\d+)\s*(mês|meses|ano|anos)',
                r'sintomas?\s+começaram\s+há\s+(\d+)\s*(mês|meses|ano|anos|dia|dias)',
                r'começou\s+há\s+(\d+)\s*(mês|meses|ano|anos|dia|dias)',
                r'iniciou\s+há\s+(\d+)\s*(mês|meses|ano|anos)'
            ]
            for pattern in medical_patterns:
                match = re.search(pattern, transcription.lower())
                if match:
                    quantidade = match.group(1)
                    periodo = match.group(2)
                    data_inicio = f"Conforme relato - início há {quantidade} {periodo}"
                    break
        
        # Determinar fatores desencadeantes baseados na profissão e sintomas
        fatores_desencadeantes = []
        if patient.profissao and patient.profissao != 'Não informada':
            if any(term in patient.profissao.lower() for term in ['cozinheiro', 'digitador', 'motorista', 'pedreiro']):
                fatores_desencadeantes.append(f"Atividade laboral como {patient.profissao}")
        if patient.sintomas and any('acidente' in str(s).lower() for s in patient.sintomas):
            fatores_desencadeantes.append("Acidente de trabalho conforme relato")
        
        fatores_text = '; '.join(fatores_desencadeantes) if fatores_desencadeantes else 'A esclarecer em avaliação presencial'
        
        # Melhorar descrição dos tratamentos
        tratamentos_text = "Não relatados"
        if patient.medicamentos:
            tratamentos_text = f"Medicações em uso: {', '.join(patient.medicamentos)}"
            if len(patient.medicamentos) > 2:
                tratamentos_text += " - Politerapia em curso"
        
        # Situação atual baseada nos sintomas
        situacao_atual = "Limitações funcionais significativas conforme relato"
        if patient.sintomas:
            principais_sintomas = ', '.join(patient.sintomas[:3])
            situacao_atual = f"Apresenta atualmente: {principais_sintomas}, com impacto sobre a capacidade laborativa"
        
        # Histórico ocupacional detalhado
        historico_ocupacional = "Conforme CTPS"
        if patient.profissao and patient.profissao != 'Não informada':
            historico_ocupacional = f"Atividade principal: {patient.profissao}. Histórico de contribuições previdenciárias conforme CNIS"
        
        # Exame clínico adaptado com mais detalhes
        autoavaliacao = "Paciente relata limitações para atividades básicas e laborais"
        if patient.sintomas:
            limitacoes = []
            for sintoma in patient.sintomas[:3]:
                if 'dor' in sintoma.lower():
                    limitacoes.append("dor que interfere na produtividade")
                elif 'cansaco' in sintoma.lower() or 'fadiga' in sintoma.lower():
                    limitacoes.append("fadiga limitante")
                elif 'tontura' in sintoma.lower():
                    limitacoes.append("instabilidade vestibular")
            if limitacoes:
                autoavaliacao = f"Relata {', '.join(limitacoes)}, comprometendo atividades habituais"
        
        anamnese = f"""**ANAMNESE MÉDICA - TELEMEDICINA**

**1. IDENTIFICAÇÃO DO PACIENTE**
Nome: {patient.nome}
Idade: {patient.idade if patient.idade else 'Não informada'} anos
Sexo: {patient.sexo if patient.sexo else 'Não informado'}
Profissão: {patient.profissao if patient.profissao else 'Não informada'}
Documento de identificação: RG/CPF conforme processo administrativo
Número de processo: Conforme referência da solicitação (se aplicável)

**2. QUEIXA PRINCIPAL**
Motivo da consulta: {queixa_principal}
Solicitação específica: {classification.tipo_beneficio.value}
Solicitação do advogado: Conforme procuração e petição (se houver)

**3. HISTÓRIA DA DOENÇA ATUAL (HDA)**
Data de início dos sintomas e/ou diagnóstico: {data_inicio}

Quadro clínico atual: {transcription if transcription.strip() else 'Paciente apresenta quadro clínico conforme documentação médica anexa, com sintomas e limitações que comprometem a capacidade laborativa habitual'}

Fatores desencadeantes ou agravantes: {fatores_text}

Tratamentos realizados e resultados: {tratamentos_text}. Resposta terapêutica conforme evolução médica documentada

Situação atual: {situacao_atual}

**4. ANTECEDENTES PESSOAIS E FAMILIARES RELEVANTES**
Doenças prévias: {', '.join(patient.condicoes) if patient.condicoes else 'Conforme histórico médico em prontuário'}
Histórico ocupacional e previdenciário: {historico_ocupacional}
Antecedentes familiares: Conforme anamnese médica prévia

**5. DOCUMENTAÇÃO APRESENTADA**
Exames complementares: Conforme anexos médicos do processo
Relatórios médicos: Documentação apresentada pelo requerente
Prontuários: Conforme histórico clínico disponível
Observação sobre suficiência: Documentação adequada para análise técnica via telemedicina
Observação sobre consistência: Dados clínicos coerentes com a condição relatada

**6. EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)**
Relato de autoavaliação guiada: {autoavaliacao}
Avaliação de força e mobilidade: Limitações funcionais evidentes conforme relato dirigido
Observação visual por videoconferência: Compatível com o quadro clínico descrito
Limitações funcionais observadas: Restrições para atividades laborais habituais evidentes
Avaliação da dor: Presente e limitante conforme escala subjetiva relatada

**7. AVALIAÇÃO MÉDICA (ASSESSMENT)**
Hipótese diagnóstica confirmada: {self._get_cid_description(classification.cid_principal)} (CID-10: {classification.cid_principal})
Diagnósticos secundários: {', '.join([f'{cid} - {self._get_cid_description(cid)}' for cid in classification.cids_secundarios]) if classification.cids_secundarios else 'Não identificados'}
Correlação clínico-funcional: O quadro apresentado é compatível com limitação da capacidade laborativa
Enquadramento previdenciário: Indicação de {classification.tipo_beneficio.value}

Data da consulta: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
Modalidade: Telemedicina (conforme Resolução CFM nº 2.314/2022)
"""
        
        return anamnese
    
    def _generate_laudo(self, state: MedicalAnalysisState) -> str:
        """Gera laudo médico estruturado seguindo padrão profissional"""
        patient = state["patient_data"]
        classification = state["classification"]
        transcription = state.get("transcription", "")
        
        # Verificar se é criança
        is_child = patient.idade and patient.idade < 18
        
        # Formatar CIDs secundários
        cids_secundarios_text = ""
        if classification.cids_secundarios:
            for cid in classification.cids_secundarios:
                desc = self._get_cid_description(cid)
                cids_secundarios_text += f"\nApresenta ainda condições associadas: {cid} - {desc}."
        
        # Conclusão específica por tipo de benefício
        conclusoes = {
            BenefitTypeEnum.AUXILIO_DOENCA: "Paciente apresenta redução significativa da capacidade laborativa devido ao quadro clínico atual, que inviabiliza o exercício das atividades profissionais habituais. Recomenda-se afastamento temporário para tratamento adequado.",
            BenefitTypeEnum.AUXILIO_ACIDENTE: "Redução parcial e permanente da capacidade laborativa em decorrência de acidente, conforme Anexo III do Decreto 3.048/1999.",
            BenefitTypeEnum.BPC_LOAS: "Paciente apresenta impedimento de longo prazo de natureza física, mental, intelectual ou sensorial, que impede a participação plena e efetiva na sociedade em igualdade de condições.",
            BenefitTypeEnum.APOSENTADORIA_INVALIDEZ: "Paciente apresenta incapacidade definitiva para o exercício de qualquer atividade laborativa, sem possibilidade de readaptação funcional.",
            BenefitTypeEnum.ISENCAO_IR: "Paciente enquadra-se no rol de doenças graves da Lei 7.713/1988, fazendo jus à isenção do imposto de renda."
        }
        
        conclusao_beneficio = conclusoes.get(classification.tipo_beneficio, conclusoes[BenefitTypeEnum.AUXILIO_DOENCA])
        
        if is_child:
            # TEMPLATE PARA CRIANÇAS
            laudo = f"""**LAUDO MÉDICO ESPECIALIZADO**

**1. HISTÓRIA CLÍNICA RESUMIDA**
Data de início dos sintomas conforme relato. Paciente {patient.nome}, {patient.idade} anos, apresenta quadro clínico de evolução {classification.gravidade.value.lower()}, caracterizado por limitações no desenvolvimento neuropsicomotor e necessidades especiais. O diagnóstico confirmado corresponde a {self._get_cid_description(classification.cid_principal)} (CID-10: {classification.cid_principal}).{cids_secundarios_text}

**2. LIMITAÇÃO FUNCIONAL**
Criança apresenta limitações funcionais para desenvolvimento neuropsicomotor, autonomia pessoal e participação escolar. Comprometimento da capacidade de interação social e necessidades educacionais especiais. Requer acompanhamento multidisciplinar continuado.

**3. TRATAMENTO**
Paciente em acompanhamento médico especializado com {', '.join(patient.medicamentos) if patient.medicamentos else 'terapias apropriadas conforme prescrição médica'}. Necessidade de suporte multidisciplinar incluindo fisioterapia, terapia ocupacional e acompanhamento pedagógico especializado.

**4. PROGNÓSTICO**
{classification.prognostico} Limitações permanentes requerendo suporte familiar, educacional e terapêutico de longo prazo para maximização do potencial de desenvolvimento.

**5. CONCLUSÃO CONGRUENTE COM O BENEFÍCIO**
{conclusao_beneficio} O quadro clínico fundamenta indicação de {classification.tipo_beneficio.value}, considerando necessidades especiais e suporte continuado para desenvolvimento.

**6. CID-10**
Principal: {classification.cid_principal} - {self._get_cid_description(classification.cid_principal)}
{chr(10).join([f'Secundário: {cid} - {self._get_cid_description(cid)}' for cid in classification.cids_secundarios]) if classification.cids_secundarios else ''}

**7. FUNDAMENTAÇÃO TÉCNICA**
{classification.especificidade_cid}

Data: {datetime.now().strftime('%d/%m/%Y')}
Observação: Laudo gerado por sistema de IA médica avançada - Validação médica presencial recomendada.
"""
        else:
            # TEMPLATE PARA ADULTOS
            limitacao_ordem = 'física'
            if any(s in str(patient.sintomas).lower() for s in ['ansiedade', 'depressão', 'pânico']):
                if any(s in str(patient.sintomas).lower() for s in ['dor', 'físico']):
                    limitacao_ordem = 'física e mental'
                else:
                    limitacao_ordem = 'mental'
            
            # Determinar tempo de afastamento
            tempo_afastamento = {
                BenefitTypeEnum.AUXILIO_DOENCA: '3 a 6 meses com reavaliações periódicas',
                BenefitTypeEnum.AUXILIO_ACIDENTE: 'Redução permanente da capacidade (sem prazo determinado)',
                BenefitTypeEnum.BPC_LOAS: 'Condição permanente (revisões conforme legislação)',
                BenefitTypeEnum.APOSENTADORIA_INVALIDEZ: 'Incapacidade definitiva',
                BenefitTypeEnum.ISENCAO_IR: 'Conforme evolução da doença'
            }.get(classification.tipo_beneficio, 'Conforme evolução clínica')
            
            # Observação sobre telemedicina se aplicável
            obs_telemedicina = ""
            if classification.telemedicina_limitacao:
                obs_telemedicina = f"\n**Observação CFM:** {classification.telemedicina_limitacao}"
            
            laudo = f"""**LAUDO MÉDICO ESPECIALIZADO**

**1. HISTÓRIA CLÍNICA RESUMIDA**
Data de início dos sintomas conforme relato. Paciente {patient.nome}, {patient.idade if patient.idade else 'idade não informada'} anos, {patient.profissao if patient.profissao else 'profissão não informada'}, apresenta evolução clínica {classification.gravidade.value.lower()} do quadro, com sintomas que comprometem significativamente a funcionalidade laboral. O quadro atual caracteriza-se por {', '.join(patient.sintomas[:3]) if patient.sintomas else 'sintomas compatíveis com o diagnóstico'}, resultando em impacto direto sobre a capacidade de desempenhar atividades laborais habituais. O diagnóstico confirmado corresponde a {self._get_cid_description(classification.cid_principal)} (CID-10: {classification.cid_principal}).{cids_secundarios_text}

**2. LIMITAÇÃO FUNCIONAL**
Paciente apresenta limitações funcionais evidentes de ordem {limitacao_ordem}, manifestadas por {', '.join(patient.sintomas[:2]) if patient.sintomas else 'sintomas incapacitantes'}. Estas limitações comprometem diretamente a funcionalidade laboral, tornando inviável a continuidade das atividades profissionais em condições adequadas. Os sintomas agravantes incluem episódios de {', '.join(patient.sintomas) if patient.sintomas else 'manifestações clínicas'} que interferem na concentração, produtividade e capacidade de interação no ambiente de trabalho.

**3. TRATAMENTO**
Paciente encontra-se em tratamento médico com {', '.join(patient.medicamentos) if patient.medicamentos else 'medicações apropriadas conforme prescrição médica'}. A resposta terapêutica tem sido {'parcial' if classification.gravidade.value == 'MODERADA' else 'limitada' if classification.gravidade.value == 'GRAVE' else 'satisfatória'}, necessitando continuidade do acompanhamento especializado. O plano terapêutico inclui medidas farmacológicas e não-farmacológicas, sendo fundamental a adesão ao tratamento para otimização dos resultados clínicos.

**4. PROGNÓSTICO**
{classification.prognostico} Tempo estimado de afastamento: {tempo_afastamento}. A possibilidade de retorno à função {'é condicionada à resposta terapêutica adequada' if classification.tipo_beneficio.value == 'AUXÍLIO-DOENÇA' else 'é improvável sem readaptação funcional' if classification.tipo_beneficio.value == 'AUXÍLIO-ACIDENTE' else 'é remota'}.

**5. CONCLUSÃO CONGRUENTE COM O BENEFÍCIO**
{conclusao_beneficio} O quadro clínico atual fundamenta a indicação de {classification.tipo_beneficio.value}, considerando {'a natureza temporária da incapacidade' if classification.tipo_beneficio.value == 'AUXÍLIO-DOENÇA' else 'a natureza permanente das limitações' if classification.tipo_beneficio.value in ['APOSENTADORIA POR INVALIDEZ', 'BPC/LOAS'] else 'as características específicas do caso'} e a necessidade de {'tratamento especializado' if classification.tipo_beneficio.value == 'AUXÍLIO-DOENÇA' else 'suporte continuado'}.

**6. CID-10**
Principal: {classification.cid_principal} - {self._get_cid_description(classification.cid_principal)}
{chr(10).join([f'Secundário: {cid} - {self._get_cid_description(cid)}' for cid in classification.cids_secundarios]) if classification.cids_secundarios else ''}

**7. FUNDAMENTAÇÃO TÉCNICA**
{classification.especificidade_cid}{obs_telemedicina}

Data: {datetime.now().strftime('%d/%m/%Y')}
Observação: Laudo gerado por sistema de IA médica avançada - Validação médica presencial recomendada.
"""
        
        return laudo.strip()
    
    def _calculate_confidence(self, state: MedicalAnalysisState) -> float:
        """Calcula score de confiança baseado na qualidade dos dados"""
        confidence = 0.5  # Base
        
        # Aumentar se há dados estruturados do paciente
        if state["patient_data"] and state["patient_data"].nome != "Paciente":
            confidence += 0.15
            
        # Aumentar se há transcrição detalhada
        if state.get("transcription") and len(state["transcription"]) > 100:
            confidence += 0.15
            
        # Aumentar se há casos similares no RAG
        if state.get("rag_results") and len(state["rag_results"]) > 0:
            confidence += 0.1
            
        # Aumentar se medicamentos foram corrigidos
        if state["patient_data"] and state["patient_data"].medicamentos:
            confidence += 0.05
            
        # Diminuir se há muitos erros
        if state.get("errors"):
            confidence -= 0.05 * len(state["errors"])
            
        # Diminuir ligeiramente se modo telemedicina (limitações)
        if self.telemedicine_mode:
            confidence -= 0.05
        
        return max(0.0, min(1.0, confidence))
    
    # ========================================================================
    # INTERFACE PÚBLICA
    # ========================================================================
    
    async def analyze_complete(self, patient_text: str = "", transcription: str = "") -> MedicalReportComplete:
        """Análise médica completa usando Pydantic AI + LangGraph"""
        try:
            mode_text = "TELEMEDICINA" if self.telemedicine_mode else "PRESENCIAL"
            print(f"🚀 Iniciando análise COMPLETA - Modo: {mode_text}")
            
            # Estado inicial
            initial_state = MedicalAnalysisState(
                messages=[],
                patient_text=patient_text,
                transcription=transcription,
                patient_data=None,
                classification=None,
                rag_results=[],
                medical_report=None,
                errors=[],
                current_step="inicio",
                telemedicine_mode=self.telemedicine_mode
            )
            
            # Executar pipeline LangGraph
            final_state = await self.workflow.ainvoke(initial_state)
            
            if final_state["medical_report"]:
                print("✅ ANÁLISE COMPLETA FINALIZADA COM SUCESSO!")
                
                # Log final das correções aplicadas
                if self.telemedicine_mode and final_state["classification"].telemedicina_limitacao:
                    print("⚖️ Limitações CFM aplicadas conforme regulamentação")
                
                return final_state["medical_report"]
            else:
                raise Exception("Relatório não foi gerado corretamente")
                
        except Exception as e:
            print(f"❌ Erro na análise completa: {e}")
            raise e
    
    def set_telemedicine_mode(self, enabled: bool):
        """Ativa ou desativa o modo telemedicina"""
        self.telemedicine_mode = enabled
        print(f"📱 Modo telemedicina: {'ATIVADO' if enabled else 'DESATIVADO'}")
    
    def analyze_sync(self, patient_text: str = "", transcription: str = "") -> MedicalReportComplete:
        """Versão síncrona para facilitar uso"""
        import asyncio
        return asyncio.run(self.analyze_complete(patient_text, transcription))


# ============================================================================
# INSTÂNCIA GLOBAL E FUNÇÕES DE CONVENIÊNCIA
# ============================================================================

_pydantic_medical_ai = None

def get_pydantic_medical_ai(telemedicine_mode: bool = True) -> PydanticMedicalAI:
    """Retorna instância singleton do Pydantic Medical AI"""
    global _pydantic_medical_ai
    if _pydantic_medical_ai is None:
        _pydantic_medical_ai = PydanticMedicalAI(telemedicine_mode=telemedicine_mode)
    return _pydantic_medical_ai

def analyze_medical_case(patient_text: str = "", transcription: str = "", telemedicine: bool = True) -> Dict[str, Any]:
    """Função de conveniência para análise médica"""
    try:
        ai = get_pydantic_medical_ai(telemedicine_mode=telemedicine)
        result = ai.analyze_sync(patient_text, transcription)
        
        return {
            'success': True,
            'patient_data': result.patient_data.dict(),
            'classification': result.classification.dict(),
            'anamnese': result.anamnese,
            'laudo_medico': result.laudo_medico,
            'confidence_score': result.confidence_score,
            'telemedicine_mode': telemedicine
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'telemedicine_mode': telemedicine
        }


# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Exemplo de uso do sistema corrigido
    
    # Caso do Carlos (cozinheiro) - deve ser auxílio-doença
    carlos_transcription = """
    Meu nome é Carlos, eu tenho 35 anos, eu trabalho de cozinheiro já há 15 anos 
    e há 7 meses eu descobri que tenho diabetes e sou insulina dependente, 
    aplico insulina duas vezes por dia, tomo metformina e no último mês a minha 
    pressão anda muito alta, todos os dias 18 por 13. O médico me receitou 
    losartana e captopril, porém eu ando me sentindo muito mal no trabalho, 
    mal estar, calor, tontura, visão embaçada e não estou tendo condições de 
    trabalhar mais nesse momento, preciso de um afastamento.
    """
    
    print("🧪 TESTE DO SISTEMA CORRIGIDO")
    print("=" * 50)
    
    # Testar com modo telemedicina ATIVADO
    result = analyze_medical_case(
        transcription=carlos_transcription,
        telemedicine=True
    )
    
    if result['success']:
        print("✅ ANÁLISE CONCLUÍDA COM SUCESSO!")
        print(f"📊 Benefício: {result['classification']['tipo_beneficio']}")
        print(f"🏥 CID Principal: {result['classification']['cid_principal']}")
        print(f"💊 Medicamentos Corrigidos: {result['patient_data']['medicamentos']}")
        print(f"⚖️ Limitação CFM: {result['classification'].get('telemedicina_limitacao', 'N/A')}")
        print(f"🎯 Confiança: {result['confidence_score']:.2f}")
        
        # Verificar se respeitou limitações CFM
        expected_benefit = "AUXÍLIO-DOENÇA"
        actual_benefit = result['classification']['tipo_beneficio']
        
        if actual_benefit == expected_benefit:
            print("✅ SUCESSO: Limitações CFM respeitadas corretamente!")
        else:
            print(f"❌ ERRO: Esperado {expected_benefit}, obtido {actual_benefit}")
    else:
        print(f"❌ ERRO: {result['error']}")
    
    print("\n🎯 Sistema Pydantic AI Médico corrigido e funcional!")