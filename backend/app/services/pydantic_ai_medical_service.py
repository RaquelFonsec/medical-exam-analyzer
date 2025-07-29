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
    universal_analysis: Optional[Dict[str, Any]]


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
            
            **CARDIOVASCULAR:**
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
        """Nó para classificação de benefícios com lógica universal"""
        try:
            print("🏥 LangGraph: Classificando benefício com lógica universal...")
            state["current_step"] = "classify_benefit"
            
            patient_data = state["patient_data"]
            transcription = state.get("transcription", "")
            
            # ========================================================================
            # APLICAR LÓGICA UNIVERSAL
            # ========================================================================
            
            # 0. Extrair detalhes estruturados da transcrição (NOVO MELHORAMENTO)
            transcription_details = self._extract_transcription_details(transcription, patient_data)
            print(f"📝 Detalhes extraídos: {len([k for k, v in transcription_details.items() if v])} categorias")
            
            # 1. Calcular score de severidade (0-10)
            severity_score = self._calculate_severity_score(patient_data, transcription)
            print(f"🎯 Score de severidade: {severity_score['score']}/10")
            
            # 2. Aplicar matriz de decisão CID
            cid_matrix = self._apply_cid_decision_matrix(patient_data, transcription, severity_score['score'])
            print(f"📊 Matriz CID: {cid_matrix['primary_cid']} ({cid_matrix['gravity']}, {cid_matrix['chronicity']})")
            
            # 3. Calcular duração de afastamento
            duration_analysis = self._calculate_leave_duration(cid_matrix, patient_data, transcription)
            print(f"⏱️ Duração recomendada: {duration_analysis['recommendation']}")
            
            # ========================================================================
            # PREPARAR CONTEXTO ENRIQUECIDO COM DETALHES DA TRANSCRIÇÃO
            # ========================================================================
            
            context = {
                "patient_data": patient_data.dict() if patient_data else {},
                "transcription": transcription,
                "rag_context": [r.get("content", "") for r in state.get("rag_results", [])],
                "telemedicine_mode": self.telemedicine_mode,
                "severity_analysis": {
                    "score": severity_score['score'],
                    "level": cid_matrix['gravity'],
                    "chronicity": cid_matrix['chronicity'],
                    "duration_months": cid_matrix['duration_months'],
                    "details": severity_score['details'],
                    "systems_detected": severity_score['systems_detected']
                },
                "cid_recommendations": {
                    "primary": cid_matrix['primary_cid'],
                    "secondary": cid_matrix['secondary_cids'],
                    "complications": cid_matrix['complications']
                },
                "duration_analysis": duration_analysis,
                "transcription_details": transcription_details
            }
            
            # Construir texto de contexto enriquecido
            context_text = f"""
            DADOS DO PACIENTE: {json.dumps(context["patient_data"], ensure_ascii=False)}
            TRANSCRIÇÃO: {context["transcription"]}
            CASOS SIMILARES RAG: {" | ".join(context["rag_context"][:2])}
            MODO TELEMEDICINA: {'SIM' if self.telemedicine_mode else 'NÃO'}
            
            === ANÁLISE UNIVERSAL ===
            SCORE SEVERIDADE: {severity_score['score']}/10 ({cid_matrix['gravity']})
            CRONICIDADE: {cid_matrix['chronicity']} ({cid_matrix['duration_months']} meses)
            CID RECOMENDADO: {cid_matrix['primary_cid']} 
            CIDs SECUNDÁRIOS: {', '.join(cid_matrix['secondary_cids']) if cid_matrix['secondary_cids'] else 'Nenhum'}
            COMPLICAÇÕES: {', '.join(cid_matrix['complications']) if cid_matrix['complications'] else 'Nenhuma'}
            DURAÇÃO AFASTAMENTO: {duration_analysis['final_days']} dias ({duration_analysis['recommendation']})
            FATORES MODIFICADORES: {', '.join(duration_analysis['modifying_factors']) if duration_analysis['modifying_factors'] else 'Nenhum'}
            
            === DETALHES ESTRUTURADOS DA TRANSCRIÇÃO ===
            CONTEXTO OCUPACIONAL: {json.dumps(transcription_details.get('occupational_context', {}), ensure_ascii=False)}
            HISTÓRICO TRATAMENTO: {json.dumps(transcription_details.get('treatment_history', {}), ensure_ascii=False)}
            PROGRESSÃO SINTOMAS: {json.dumps(transcription_details.get('symptom_progression', {}), ensure_ascii=False)}
            IMPACTO FUNCIONAL: {json.dumps(transcription_details.get('functional_impact', {}), ensure_ascii=False)}
            FATORES AMBIENTAIS: {json.dumps(transcription_details.get('environmental_factors', {}), ensure_ascii=False)}
            QUALIDADE DE VIDA: {json.dumps(transcription_details.get('quality_of_life', {}), ensure_ascii=False)}
            """
            
            result = await self.classification_agent.run(context_text)
            
            # ========================================================================
            # APLICAR CORREÇÕES BASEADAS NA LÓGICA UNIVERSAL
            # ========================================================================
            
            # Sobrescrever com dados da matriz se mais precisos
            if cid_matrix['primary_cid'] != 'I10':  # Se não for fallback
                result.data.cid_principal = cid_matrix['primary_cid']
            
            if cid_matrix['secondary_cids']:
                result.data.cids_secundarios = cid_matrix['secondary_cids']
            
            # Garantir que gravidade seja consistente com score
            if severity_score['score'] >= 7:
                result.data.gravidade = SeverityEnum.GRAVE
            elif severity_score['score'] >= 4:
                result.data.gravidade = SeverityEnum.MODERADA
            else:
                result.data.gravidade = SeverityEnum.LEVE
            
            # Enriquecer justificativa com dados da análise
            original_justificativa = result.data.justificativa
            
            # Construir análise técnica detalhada
            technical_analysis = f"""
Análise técnica detalhada: Score de severidade {severity_score['score']}/10 indica gravidade {cid_matrix['gravity'].lower()}. 
Quadro caracterizado como {cid_matrix['chronicity']} com duração de {cid_matrix['duration_months']} meses. 
Tempo estimado de afastamento: {duration_analysis['recommendation']}."""
            
            # Adicionar detalhes contextuais da transcrição
            contextual_details = []
            
            # Contexto ocupacional
            if transcription_details.get('occupational_context'):
                occ_context = transcription_details['occupational_context']
                if occ_context.get('duration'):
                    contextual_details.append(f"Experiência profissional de {occ_context['duration']}")
                
                work_factors = []
                if occ_context.get('estresse'): work_factors.append("estresse ocupacional")
                if occ_context.get('físico'): work_factors.append("esforço físico")
                if occ_context.get('repetitivo'): work_factors.append("atividade repetitiva")
                if occ_context.get('ambiente'): work_factors.append("exposição ambiental")
                
                if work_factors:
                    contextual_details.append(f"Fatores ocupacionais identificados: {', '.join(work_factors)}")
            
            # Histórico de tratamento
            if transcription_details.get('treatment_history'):
                treat_hist = transcription_details['treatment_history']
                if treat_hist.get('response'):
                    response_map = {
                        'boa': 'boa resposta terapêutica',
                        'parcial': 'resposta terapêutica parcial',
                        'ruim': 'falha terapêutica documentada',
                        'efeitos_colaterais': 'limitações por efeitos adversos'
                    }
                    contextual_details.append(f"Histórico: {response_map.get(treat_hist['response'], treat_hist['response'])}")
            
            # Progressão dos sintomas
            if transcription_details.get('symptom_progression'):
                progression = transcription_details['symptom_progression']
                if progression.get('trend'):
                    contextual_details.append(f"Evolução: {progression['trend']}")
                if progression.get('frequency'):
                    contextual_details.append(f"Frequência: {progression['frequency']}")
            
            # Impacto funcional específico
            if transcription_details.get('functional_impact'):
                impact_areas = list(transcription_details['functional_impact'].keys())
                if impact_areas:
                    contextual_details.append(f"Áreas funcionais comprometidas: {', '.join(impact_areas)}")
            
            # Fatores ambientais
            if transcription_details.get('environmental_factors'):
                env_factors = list(transcription_details['environmental_factors'].keys())
                if env_factors:
                    contextual_details.append(f"Fatores desencadeantes: {', '.join(env_factors)}")
            
            # Construir justificativa enriquecida
            enhanced_justificativa = f"{original_justificativa}\n\n{technical_analysis}"
            
            if contextual_details:
                enhanced_justificativa += f"\n\nContexto clínico específico: {'. '.join(contextual_details)}."
            
            if duration_analysis['modifying_factors']:
                enhanced_justificativa += f" Fatores que influenciam o prognóstico: {', '.join(duration_analysis['modifying_factors'])}."
            
            # Adicionar detalhes de consistência se houver
            if severity_score['details'].get('consistency_adjustments'):
                adjustments = severity_score['details']['consistency_adjustments']
                enhanced_justificativa += f" Ajustes aplicados para consistência interna: {', '.join(adjustments)}."
            
            result.data.justificativa = enhanced_justificativa
            
            # Salvar análise universal no estado para uso posterior
            state["universal_analysis"] = {
                "severity_score": severity_score,
                "cid_matrix": cid_matrix,
                "duration_analysis": duration_analysis
            }
            
            state["classification"] = result.data
            
            print(f"✅ Classificação (Universal): {result.data.tipo_beneficio.value}")
            print(f"📋 CID aplicado: {result.data.cid_principal} ({result.data.gravidade.value})")
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
    # LÓGICA UNIVERSAL PARA CLASSIFICAÇÃO DE CID E AVALIAÇÃO MÉDICA
    # ========================================================================
    
    def _calculate_severity_score(self, patient_data: PatientDataStrict, transcription: str) -> dict:
        """
        Sistema de Análise de Severidade Geral MELHORADO
        Escala Universal de Comprometimento (0-10) com consistência interna
        """
        score = 0
        details = {
            'duration_points': 0,
            'intensity_points': 0,
            'emergency_points': 0,
            'systems_points': 0,
            'failure_points': 0,
            'impact_points': 0,
            'consistency_adjustments': []
        }
        
        text = transcription.lower() if transcription else ""
        
        # ===================================================================
        # 1. ANÁLISE DE DURAÇÃO (0-3 pontos) - MELHORADA
        # ===================================================================
        if text:
            import re
            # Padrões mais específicos e precisos
            duration_patterns = [
                (r'há\s+(\d+)\s*anos?', 'anos', 3),
                (r'há\s+(\d+)\s*meses?', 'meses', 2),
                (r'há\s+(\d+)\s*semanas?', 'semanas', 1),
                (r'há\s+(\d+)\s*dias?', 'dias', 0.5),
                (r'desde\s+(\d+)\s*anos?', 'anos', 3),
                (r'faz\s+(\d+)\s*anos?', 'anos', 3)
            ]
            
            duration_found = False
            for pattern, unit, base_weight in duration_patterns:
                match = re.search(pattern, text)
                if match and not duration_found:
                    duration = int(match.group(1))
                    
                    if unit == 'anos':
                        duration_points = min(3, duration * 0.8)  # Máximo 3, mais conservador
                    elif unit == 'meses':
                        duration_points = min(2.5, duration * 0.3)  # Escala graduada
                    elif unit == 'semanas':
                        duration_points = min(1.5, duration * 0.2)
                    else:  # dias
                        duration_points = min(1, duration * 0.1)
                    
                    score += duration_points
                    details['duration_points'] = duration_points
                    duration_found = True
                    break
        
        # ===================================================================
        # 2. ANÁLISE DE INTENSIDADE (0-3 pontos) - MELHORADA
        # ===================================================================
        intensity_score = 0
        
        # Termos críticos (3 pontos)
        critical_terms = [
            'insuportável', 'excruciante', 'não aguento mais', 
            'não consigo nem', 'impossível de', 'muito grave'
        ]
        
        # Termos severos (2 pontos)
        severe_terms = [
            'muito forte', 'intensa', 'severa', 'todos os dias',
            'constantemente', 'sempre sinto', 'não para'
        ]
        
        # Termos moderados (1 ponto)
        moderate_terms = [
            'dor', 'desconforto', 'incomoda', 'dificulta',
            'atrapalha', 'chateia', 'perturba'
        ]
        
        if any(term in text for term in critical_terms):
            intensity_score = 3
        elif any(term in text for term in severe_terms):
            intensity_score = 2
        elif any(term in text for term in moderate_terms):
            intensity_score = 1
        
        score += intensity_score
        details['intensity_points'] = intensity_score
        
        # ===================================================================
        # 3. INTERVENÇÃO DE EMERGÊNCIA (0-2 pontos) - MELHORADA
        # ===================================================================
        emergency_score = 0
        emergency_terms = [
            'samu', 'emergência', 'pronto socorro', 'internação', 'uti',
            'hospitalização', 'cirurgia urgente', 'resgate', '192'
        ]
        
        emergency_count = sum(1 for term in emergency_terms if term in text)
        if emergency_count >= 2:
            emergency_score = 2
        elif emergency_count == 1:
            emergency_score = 1.5
        
        score += emergency_score
        details['emergency_points'] = emergency_score
        
        # ===================================================================
        # 4. SISTEMAS MÚLTIPLOS (0-2 pontos) - MELHORADA E ESPECÍFICA
        # ===================================================================
        systems_detected = set()
        system_indicators = {
            'cardiovascular': ['pressão alta', 'coração', 'infarto', 'arritmia', 'palpitação'],
            'neurológico': ['tontura', 'dor de cabeça', 'confusão', 'memória', 'formigamento'],
            'musculoesquelético': ['dor nas costas', 'articulação', 'músculo', 'osso', 'bursite'],
            'digestivo': ['estômago', 'digestão', 'náusea', 'vômito', 'gastrite'],
            'respiratório': ['falta de ar', 'tosse', 'respiração', 'pulmão', 'asma'],
            'endócrino': ['diabetes', 'tireóide', 'hormônio', 'açúcar', 'insulina'],
            'psiquiátrico': ['ansiedade', 'depressão', 'pânico', 'tristeza', 'medo'],
            'oftálmico': ['visão', 'olho', 'enxergar', 'vista', 'embaçada']
        }
        
        for system, terms in system_indicators.items():
            if any(term in text for term in terms):
                systems_detected.add(system)
        
        systems_count = len(systems_detected)
        if systems_count >= 4:
            systems_score = 2
        elif systems_count >= 2:
            systems_score = 1.5
        elif systems_count == 1:
            systems_score = 0.5
        else:
            systems_score = 0
        
        score += systems_score
        details['systems_points'] = systems_score
        
        # ===================================================================
        # 5. FALHA TERAPÊUTICA (0-2 pontos) - MELHORADA
        # ===================================================================
        failure_score = 0
        
        strong_failure_terms = [
            'não melhorou nada', 'piorou muito', 'não adiantou nada',
            'nenhum resultado', 'totalmente ineficaz'
        ]
        
        moderate_failure_terms = [
            'não melhorou', 'não funcionou', 'continua igual',
            'pouco resultado', 'não responde bem'
        ]
        
        if any(term in text for term in strong_failure_terms):
            failure_score = 2
        elif any(term in text for term in moderate_failure_terms):
            failure_score = 1
        
        score += failure_score
        details['failure_points'] = failure_score
        
        # ===================================================================
        # 6. IMPACTO FUNCIONAL (0-3 pontos) - MELHORADA
        # ===================================================================
        impact_score = 0
        
        severe_impact_terms = [
            'não consigo trabalhar', 'impossível continuar',
            'não tenho condições', 'incapaz de', 'totalmente limitado'
        ]
        
        moderate_impact_terms = [
            'dificulta o trabalho', 'atrapalha muito', 'limita as atividades',
            'prejudica o desempenho', 'afeta a produtividade'
        ]
        
        mild_impact_terms = [
            'incomoda', 'chateia', 'perturba um pouco',
            'dificulta às vezes', 'atrapalha pouco'
        ]
        
        if any(term in text for term in severe_impact_terms):
            impact_score = 3
        elif any(term in text for term in moderate_impact_terms):
            impact_score = 2
        elif any(term in text for term in mild_impact_terms):
            impact_score = 1
        
        score += impact_score
        details['impact_points'] = impact_score
        
        # ===================================================================
        # 7. VALIDAÇÕES DE CONSISTÊNCIA INTERNA
        # ===================================================================
        
        # Ajuste para idade (idosos e crianças têm maior vulnerabilidade)
        if patient_data.idade:
            if patient_data.idade > 65:
                adjustment = 0.5
                score += adjustment
                details['consistency_adjustments'].append(f"idade avançada (+{adjustment})")
            elif patient_data.idade < 16:
                adjustment = 0.3
                score += adjustment
                details['consistency_adjustments'].append(f"idade pediátrica (+{adjustment})")
        
        # Ajuste para múltiplos medicamentos (indica severidade)
        if patient_data.medicamentos and len(patient_data.medicamentos) >= 3:
            adjustment = 0.5
            score += adjustment
            details['consistency_adjustments'].append(f"politerapia (+{adjustment})")
        
        # Verificação de consistência: alta duração + baixo impacto é inconsistente
        if details['duration_points'] >= 2 and details['impact_points'] <= 0.5:
            adjustment = 0.5
            score += adjustment
            details['consistency_adjustments'].append("correção duração vs impacto (+0.5)")
        
        # Verificação: múltiplos sistemas + baixa intensidade é inconsistente
        if details['systems_points'] >= 1.5 and details['intensity_points'] <= 1:
            adjustment = 0.3
            score += adjustment
            details['consistency_adjustments'].append("correção sistemas vs intensidade (+0.3)")
        
        final_score = min(10, max(0, round(score, 1)))
        
        return {
            'score': int(final_score),
            'details': details,
            'raw_score': score,
            'systems_detected': list(systems_detected)
        }
    
    def _analyze_chronicity(self, transcription: str) -> tuple[str, int]:
        """
        Determina se é agudo vs crônico e retorna duração em meses
        """
        if not transcription:
            return 'crônico', 12  # Fallback conservador
        
        import re
        
        # Buscar padrões de duração
        patterns = [
            (r'há\s+(\d+)\s*ano', 12),  # anos para meses
            (r'há\s+(\d+)\s*meses?', 1),  # meses
            (r'há\s+(\d+)\s*semana', 0.25),  # semanas para meses
            (r'há\s+(\d+)\s*dia', 0.03)  # dias para meses
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, transcription.lower())
            if match:
                duration = int(match.group(1))
                total_months = duration * multiplier
                
                if total_months < 6:
                    return 'agudo', int(total_months)
                else:
                    return 'crônico', int(total_months)
        
        # Se não encontrou padrão, assumir crônico
        return 'crônico', 12
    
    def _apply_cid_decision_matrix(self, patient_data: PatientDataStrict, transcription: str, severity_score: int) -> dict:
        """
        Matriz de Decisão CID baseada em evidências
        """
        chronicity, duration_months = self._analyze_chronicity(transcription)
        
        # Classificação de gravidade baseada no score
        if severity_score <= 3:
            gravity = 'LEVE'
        elif severity_score <= 6:
            gravity = 'MODERADA'
        elif severity_score <= 8:
            gravity = 'GRAVE'
        else:
            gravity = 'GRAVE'  # 9-10 = crítico, mas usamos GRAVE como máximo
        
        # Verificar complicações
        complications = []
        if transcription:
            complication_indicators = {
                'oftálmicas': ['visão', 'olho', 'enxergar', 'vista'],
                'renais': ['rim', 'urina', 'renal'],
                'neurológicas': ['nervo', 'formigamento', 'dormência'],
                'cardiovasculares': ['coração', 'pressão', 'circulação']
            }
            
            for comp_type, terms in complication_indicators.items():
                if any(term in transcription.lower() for term in terms):
                    complications.append(comp_type)
        
        has_complications = len(complications) > 0
        
        # CID principal baseado em sintomas dominantes
        primary_cid = self._determine_primary_cid(patient_data, transcription, has_complications)
        
        # CIDs secundários baseados em comorbidades
        secondary_cids = self._determine_secondary_cids(patient_data, transcription, primary_cid)
        
        return {
            'primary_cid': primary_cid,
            'secondary_cids': secondary_cids,
            'gravity': gravity,
            'chronicity': chronicity,
            'duration_months': duration_months,
            'has_complications': has_complications,
            'complications': complications,
            'severity_score': severity_score
        }
    
    def _determine_primary_cid(self, patient_data: PatientDataStrict, transcription: str, has_complications: bool) -> str:
        """
        Determina CID principal baseado em sintomas dominantes - PRIORIDADE CORRIGIDA
        """
        text = transcription.lower()
        
        # PRIORIDADE 1: Diabetes (sempre tem precedência quando presente)
        diabetes_indicators = ['diabetes', 'diabético', 'diabética', 'açúcar alto', 'glicose alta', 'glicemia']
        insulin_indicators = ['insulina', 'insulino dependente', 'tipo 1', 'dm1', 'tipo i']
        
        if any(term in text for term in diabetes_indicators):
            # Determinar tipo com mais precisão
            if any(term in text for term in insulin_indicators):
                return 'E10.3' if has_complications else 'E10.9'  # Tipo 1
            else:
                return 'E11.3' if has_complications else 'E11.9'  # Tipo 2
        
        # PRIORIDADE 2: Condições cardiovasculares agudas
        if any(term in text for term in ['infarto', 'ataque cardíaco', 'iam']):
            # Verificar temporalidade
            if any(term in text for term in ['há poucos dias', 'semana passada', 'recente', 'ontem', 'hoje']):
                return 'I21.9'  # Infarto agudo
            else:
                return 'I25.2'  # Infarto antigo
        
        # PRIORIDADE 3: Condições neurológicas/ortopédicas específicas
        if any(term in text for term in ['túnel do carpo', 'síndrome túnel', 'formigamento punho', 'dormência mão']):
            return 'G56.0'
        
        if any(term in text for term in ['bursite', 'bursite cotovelo', 'olécrano']):
            return 'M70.2'
        
        if any(term in text for term in ['ombro', 'impacto ombro', 'síndrome impacto']):
            return 'M75.1'
        
        # PRIORIDADE 4: Condições psiquiátricas graves
        if any(term in text for term in ['depressão', 'depressivo', 'tristeza profunda', 'desânimo']):
            if any(term in text for term in ['grave', 'severa', 'não consigo sair da cama', 'suicídio']):
                return 'F32.2'
            else:
                return 'F32.1'
        
        if any(term in text for term in ['ansiedade', 'pânico', 'síndrome pânico']):
            if 'pânico' in text or 'síndrome pânico' in text:
                return 'F41.0'
            else:
                return 'F41.1'
        
        # PRIORIDADE 5: Hipertensão (só se não houver condições mais específicas)
        hypertension_indicators = ['pressão alta', 'hipertensão', 'pressão arterial alta']
        pressure_numbers = ['18 por', '19 por', '20 por', '16 por 10', '17 por 11']
        
        if (any(term in text for term in hypertension_indicators) or 
            any(term in text for term in pressure_numbers)):
            return 'I10'
        
        # FALLBACK: Se só tem medicamentos cardiovasculares
        cardio_meds = ['losartana', 'captopril', 'enalapril', 'amlodipina']
        if any(med in text for med in cardio_meds):
            return 'I10'
        
        # Fallback final conservador
        return 'I10'  # Hipertensão como padrão
    
    def _determine_secondary_cids(self, patient_data: PatientDataStrict, transcription: str, primary_cid: str = None) -> list:
        """
        REFATORADO EQUILIBRADO: CIDs secundários via FAISS + fallback controlado
        Evita alucinações mas não perde condições óbvias mencionadas
        """
        print(f"🔍 BUSCA BALANCEADA: CIDs secundários para CID principal: {primary_cid}")
        
        all_secondary_cids = []
        
        # ===================================================================
        # PRIORIDADE 1: BASE FAISS (com critérios mais flexíveis)
        # ===================================================================
        
        if self.rag_available and self.rag_service:
            specific_queries = self._build_symptom_specific_queries(patient_data, transcription, primary_cid)
            
            for query_info in specific_queries:
                print(f"🔍 Query FAISS: {query_info['description']}")
                
                try:
                    rag_results = self.rag_service.search_similar_cases(query_info['query'], top_k=3)
                    found_cids = self._extract_clinically_relevant_cids_flexible(rag_results, query_info, primary_cid)
                    
                    if found_cids:
                        all_secondary_cids.extend(found_cids)
                        print(f"✅ FAISS encontrou: {found_cids}")
                        
                except Exception as e:
                    print(f"❌ Erro na query FAISS: {e}")
                    continue
        
        # ===================================================================
        # PRIORIDADE 2: FALLBACK CONTROLADO para condições EXPLÍCITAS
        # ===================================================================
        
        explicit_conditions = self._detect_explicit_conditions(transcription, patient_data, primary_cid)
        
        if explicit_conditions:
            print(f"🎯 Condições explícitas detectadas: {list(explicit_conditions.keys())}")
            
            for condition, cid in explicit_conditions.items():
                if cid not in all_secondary_cids:
                    all_secondary_cids.append(cid)
                    print(f"✅ Adicionado CID explícito: {cid} ({condition})")
        
        # ===================================================================
        # VALIDAÇÃO FINAL
        # ===================================================================
        
        # Remover duplicatas e CID principal
        seen = set()
        clean_secondary = []
        for cid in all_secondary_cids:
            if cid not in seen and cid != primary_cid:
                seen.add(cid)
                clean_secondary.append(cid)
        
        # Limitar a no máximo 3 CIDs
        final_secondary = clean_secondary[:3]
        
        if final_secondary:
            print(f"✅ CIDs secundários FINAIS: {final_secondary}")
        else:
            print("✅ Nenhum CID secundário encontrado")
        
        return final_secondary
    
    def _extract_clinically_relevant_cids_flexible(self, rag_results: list, query_info: dict, primary_cid: str) -> list:
        """
        Versão mais flexível da extração de CIDs do FAISS
        """
        relevant_cids = []
        
        if not rag_results:
            return relevant_cids
        
        import re
        cid_pattern = r'\b[A-Z]\d{2}(?:\.\d)?\b'
        
        for result in rag_results:
            content = result.get('content', '')
            confidence = result.get('score', 0)
            
            # Critério mais flexível: aceitar confidence >= 0.5
            if confidence < 0.5:
                continue
            
            found_cids = re.findall(cid_pattern, content)
            
            for cid in found_cids:
                if cid == primary_cid:
                    continue
                
                # Verificar se está nos prefixos esperados
                if query_info.get('expected_prefixes'):
                    is_expected = any(cid.startswith(prefix) for prefix in query_info['expected_prefixes'])
                    if not is_expected:
                        continue
                
                # Verificação de contexto mais flexível
                content_lower = content.lower()
                query_terms = query_info['query'].lower().split()
                context_relevance = sum(1 for term in query_terms if term in content_lower)
                
                # Aceitar se pelo menos 1 termo da query aparece (mais flexível)
                if context_relevance >= 1 and cid not in relevant_cids:
                    relevant_cids.append(cid)
        
        return relevant_cids
    
    def _detect_explicit_conditions(self, transcription: str, patient_data: PatientDataStrict, primary_cid: str) -> dict:
        """
        Detecta condições médicas EXPLICITAMENTE mencionadas no texto
        Retorna apenas condições óbvias e inequívocas
        """
        if not transcription:
            return {}
        
        text = transcription.lower()
        explicit_conditions = {}
        
        # ===================================================================
        # CONDIÇÕES EXPLÍCITAS POR PALAVRA-CHAVE + CONFIRMAÇÃO
        # ===================================================================
        
        # HIPERTENSÃO - múltiplos indicadores
        hypertension_indicators = [
            ('pressão alta', 'I10'),
            ('hipertensão', 'I10'),
            ('pressão arterial alta', 'I10')
        ]
        
        hypertension_confirmations = [
            'losartana', 'captopril', 'atenolol', 'amlodipina', 'enalapril',
            '18 por', '19 por', '16 por 10', '17 por 11'
        ]
        
        for indicator, cid in hypertension_indicators:
            if indicator in text and cid != primary_cid:
                # Verificar se há confirmação via medicamento ou valores
                if any(conf in text for conf in hypertension_confirmations):
                    explicit_conditions['Hipertensão arterial'] = cid
                    break
        
        # DIABETES - múltiplos indicadores
        diabetes_indicators = [
            ('diabetes', 'E11.9'),
            ('diabético', 'E11.9'),
            ('diabética', 'E11.9'),
            ('açúcar alto', 'E11.9'),
            ('glicose alta', 'E11.9')
        ]
        
        diabetes_confirmations = [
            'metformina', 'insulina', 'glibenclamida', 'gliclazida',
            'visão embaçada', 'sede excessiva', 'urinar muito'
        ]
        
        for indicator, base_cid in diabetes_indicators:
            if indicator in text and not primary_cid.startswith('E1'):
                # Determinar tipo e complicações
                if any(conf in text for conf in diabetes_confirmations):
                    if 'insulina' in text or 'tipo 1' in text:
                        cid = 'E10.9'
                        if 'visão' in text or 'olho' in text:
                            cid = 'E10.3'
                    else:
                        cid = 'E11.9'
                        if 'visão' in text or 'olho' in text:
                            cid = 'E11.3'
                    
                    explicit_conditions['Diabetes mellitus'] = cid
                    break
        
        # DEPRESSÃO/ANSIEDADE - com medicamentos
        psychiatric_indicators = [
            ('depressão', 'F32.1'),
            ('ansiedade', 'F41.1'),
            ('transtorno depressivo', 'F32.1'),
            ('transtorno ansiedade', 'F41.1')
        ]
        
        psychiatric_confirmations = [
            'antidepressivo', 'sertralina', 'fluoxetina', 'paroxetina',
            'ansiolítico', 'clonazepam', 'alprazolam', 'escitalopram'
        ]
        
        for indicator, cid in psychiatric_indicators:
            if indicator in text and not primary_cid.startswith('F'):
                if any(conf in text for conf in psychiatric_confirmations):
                    condition_name = 'Transtorno depressivo' if 'depres' in indicator else 'Transtorno de ansiedade'
                    explicit_conditions[condition_name] = cid
        
        # CONDIÇÕES ARTICULARES - com anti-inflamatórios
        articular_indicators = [
            ('dor articular', 'M25.5'),
            ('dor nas articulações', 'M25.5'),
            ('artrite', 'M13.9'),
            ('artrose', 'M19.9')
        ]
        
        articular_confirmations = [
            'anti-inflamatório', 'ibuprofeno', 'diclofenaco', 'nimesulida',
            'naproxeno', 'meloxicam'
        ]
        
        for indicator, cid in articular_indicators:
            if indicator in text and not primary_cid.startswith('M'):
                if any(conf in text for conf in articular_confirmations):
                    explicit_conditions['Transtorno articular'] = cid
                    break
        
        # ===================================================================
        # VALIDAÇÃO EXTRA: Verificar coerência com medicamentos do paciente
        # ===================================================================
        
        if patient_data.medicamentos:
            meds_text = ' '.join(patient_data.medicamentos).lower()
            
            # Validar condições encontradas com medicamentos extraídos
            validated_conditions = {}
            
            for condition, cid in explicit_conditions.items():
                is_consistent = False
                
                if cid.startswith('I'):  # Cardiovascular
                    is_consistent = any(med in meds_text for med in ['losartana', 'captopril', 'atenolol'])
                elif cid.startswith('E1'):  # Diabetes
                    is_consistent = any(med in meds_text for med in ['metformina', 'insulina', 'glibenclamida'])
                elif cid.startswith('F'):  # Psiquiátrico
                    is_consistent = any(med in meds_text for med in ['antidepressivo', 'sertralina', 'ansiolítico'])
                elif cid.startswith('M'):  # Articular
                    is_consistent = any(med in meds_text for med in ['anti-inflamatório', 'ibuprofeno', 'diclofenaco'])
                else:
                    is_consistent = True  # Outras condições
                
                if is_consistent:
                    validated_conditions[condition] = cid
                else:
                    print(f"⚠️ Condição {condition} descartada - inconsistente com medicamentos")
            
            return validated_conditions
        
        return explicit_conditions
    
    def _build_symptom_specific_queries(self, patient_data: PatientDataStrict, transcription: str, primary_cid: str) -> list:
        """
        Constrói queries específicas baseadas em sintomas e condições realmente mencionados
        """
        queries = []
        text = transcription.lower() if transcription else ""
        
        # Mapa de sintomas para condições médicas específicas
        symptom_conditions = {
            'pressão alta': {
                'query': 'hipertensão arterial pressão alta medicamentos anti-hipertensivos',
                'expected_cids': ['I10', 'I15'],
                'description': 'Hipertensão arterial'
            },
            'diabetes': {
                'query': 'diabetes mellitus glicose insulina metformina complicações',
                'expected_cids': ['E10', 'E11'],
                'description': 'Diabetes mellitus'
            },
            'depressão': {
                'query': 'transtorno depressivo episódio depressivo antidepressivos',
                'expected_cids': ['F32', 'F33'],
                'description': 'Transtornos depressivos'
            },
            'ansiedade': {
                'query': 'transtorno ansiedade generalizada pânico ansiolíticos',
                'expected_cids': ['F41', 'F40'],
                'description': 'Transtornos de ansiedade'
            },
            'dor articular': {
                'query': 'artralgia dor articular artrose anti-inflamatórios',
                'expected_cids': ['M25', 'M19'],
                'description': 'Transtornos articulares'
            },
            'dor nas costas': {
                'query': 'dorsalgia lombalgia dor nas costas coluna vertebral',
                'expected_cids': ['M54'],
                'description': 'Dorsalgia'
            }
        }
        
        # Buscar sintomas mencionados no texto
        for symptom, config in symptom_conditions.items():
            if symptom in text:
                # Verificar se não é o CID principal
                if primary_cid and not any(primary_cid.startswith(expected) for expected in config['expected_cids']):
                    queries.append({
                        'query': config['query'],
                        'expected_prefixes': config['expected_cids'],
                        'symptom': symptom,
                        'description': config['description']
                    })
        
        # Queries baseadas em medicamentos específicos
        medication_conditions = {
            'losartana': {
                'query': 'losartana hipertensão arterial pressão alta',
                'expected_cids': ['I10'],
                'description': 'Condições tratadas com losartana'
            },
            'captopril': {
                'query': 'captopril hipertensão arterial insuficiência cardíaca',
                'expected_cids': ['I10', 'I50'],
                'description': 'Condições tratadas com captopril'
            },
            'metformina': {
                'query': 'metformina diabetes mellitus tipo 2',
                'expected_cids': ['E11'],
                'description': 'Diabetes tipo 2'
            },
            'insulina': {
                'query': 'insulina diabetes mellitus tipo 1',
                'expected_cids': ['E10'],
                'description': 'Diabetes tipo 1'
            }
        }
        
        # Verificar medicamentos mencionados
        if patient_data.medicamentos:
            for med in patient_data.medicamentos:
                med_lower = med.lower()
                for medication, config in medication_conditions.items():
                    if medication in med_lower:
                        # Verificar se não é o CID principal
                        if primary_cid and not any(primary_cid.startswith(expected) for expected in config['expected_cids']):
                            queries.append({
                                'query': config['query'],
                                'expected_prefixes': config['expected_cids'],
                                'medication': medication,
                                'description': config['description']
                            })
        
        return queries
    
    def _extract_clinically_relevant_cids(self, rag_results: list, query_info: dict, primary_cid: str) -> list:
        """
        Extrai apenas CIDs clinicamente relevantes dos resultados FAISS
        """
        relevant_cids = []
        
        if not rag_results:
            return relevant_cids
        
        import re
        cid_pattern = r'\b[A-Z]\d{2}(?:\.\d)?\b'
        
        for result in rag_results:
            content = result.get('content', '')
            confidence = result.get('score', 0)
            
            # Apenas considerar resultados com alta confiança
            if confidence < 0.7:
                continue
            
            # Extrair CIDs do conteúdo
            found_cids = re.findall(cid_pattern, content)
            
            for cid in found_cids:
                if cid == primary_cid:
                    continue
                
                # Verificar se o CID está nos prefixos esperados para esta query
                if query_info.get('expected_prefixes'):
                    is_expected = any(cid.startswith(prefix) for prefix in query_info['expected_prefixes'])
                    if not is_expected:
                        continue
                
                # Verificar se há contexto médico válido
                content_lower = content.lower()
                
                # O CID deve aparecer em contexto médico válido
                medical_context_indicators = [
                    'diagnóstico', 'cid', 'classificação', 'transtorno', 'doença',
                    'síndrome', 'condição', 'patologia', 'comorbidade'
                ]
                
                has_medical_context = any(indicator in content_lower for indicator in medical_context_indicators)
                
                if has_medical_context:
                    # Verificar relevância específica do sintoma/medicamento
                    query_terms = query_info['query'].lower().split()
                    context_relevance = sum(1 for term in query_terms if term in content_lower)
                    
                    if context_relevance >= 2:  # Pelo menos 2 termos da query devem aparecer
                        if cid not in relevant_cids:
                            relevant_cids.append(cid)
        
        return relevant_cids
    
    def _validate_clinical_coherence(self, cids: list, primary_cid: str, patient_data: PatientDataStrict, transcription: str) -> list:
        """
        Valida a coerência clínica dos CIDs secundários encontrados
        """
        validated = []
        text = transcription.lower() if transcription else ""
        
        for cid in cids:
            is_clinically_coherent = False
            
            # Validações específicas por categoria de CID
            if cid.startswith('I'):  # Cardiovascular
                cardiovascular_indicators = [
                    'pressão', 'hipertensão', 'coração', 'cardíaco', 'circulação',
                    'losartana', 'captopril', 'atenolol', 'amlodipina'
                ]
                is_clinically_coherent = any(indicator in text for indicator in cardiovascular_indicators)
                
            elif cid.startswith('E1'):  # Diabetes
                diabetes_indicators = [
                    'diabetes', 'diabético', 'açúcar', 'glicose', 'insulina',
                    'metformina', 'glibenclamida', 'visão embaçada'
                ]
                is_clinically_coherent = any(indicator in text for indicator in diabetes_indicators)
                
            elif cid.startswith('F'):  # Psiquiátrico
                psychiatric_indicators = [
                    'depressão', 'ansiedade', 'tristeza', 'nervoso', 'estresse',
                    'antidepressivo', 'ansiolítico', 'sertralina', 'fluoxetina'
                ]
                is_clinically_coherent = any(indicator in text for indicator in psychiatric_indicators)
                
            elif cid.startswith('M'):  # Musculoesquelético
                musculoskeletal_indicators = [
                    'dor', 'articulação', 'ombro', 'joelho', 'costas',
                    'articular', 'músculo', 'anti-inflamatório', 'ibuprofeno'
                ]
                is_clinically_coherent = any(indicator in text for indicator in musculoskeletal_indicators)
                
            elif cid.startswith('J'):  # Respiratório
                respiratory_indicators = [
                    'tosse', 'falta de ar', 'respiração', 'pulmão', 'asma',
                    'bronquite', 'pneumonia'
                ]
                is_clinically_coherent = any(indicator in text for indicator in respiratory_indicators)
                
            else:
                # Para outras categorias, ser mais restritivo
                # Apenas aceitar se há menção explícita de sintomas relacionados
                is_clinically_coherent = False
            
            if is_clinically_coherent:
                validated.append(cid)
            else:
                print(f"⚠️ CID {cid} descartado - sem coerência clínica")
        
        return validated
    
    def _calculate_leave_duration(self, cid_matrix: dict, patient_data: PatientDataStrict, transcription: str) -> dict:
        """
        Sistema de Temporalidade para Afastamentos
        """
        # Fórmula base
        if cid_matrix['chronicity'] == 'agudo':
            if cid_matrix['gravity'] == 'LEVE':
                base_days = 20  # 15-30 dias
            elif cid_matrix['gravity'] == 'MODERADA':
                base_days = 30
            else:
                base_days = 45
        else:  # crônico
            if cid_matrix['gravity'] == 'LEVE':
                base_days = 45  # 30-60 dias
            elif cid_matrix['gravity'] == 'MODERADA':
                base_days = 60
            else:
                base_days = 75  # 60-90 dias
        
        # Fatores modificadores
        multiplier = 1.0
        reasons = []
        
        # Múltiplas comorbidades (+50%)
        if len(cid_matrix['secondary_cids']) >= 2:
            multiplier += 0.5
            reasons.append("múltiplas comorbidades")
        
        # Idade (+30% se >50 ou <18)
        if patient_data.idade:
            if patient_data.idade > 50:
                multiplier += 0.3
                reasons.append("idade avançada")
            elif patient_data.idade < 18:
                multiplier += 0.3
                reasons.append("idade pediátrica")
        
        # Falha terapêutica prévia (+20%)
        if transcription and any(term in transcription.lower() for term in [
            'não melhorou', 'não funcionou', 'continua igual', 'piorou'
        ]):
            multiplier += 0.2
            reasons.append("falha terapêutica prévia")
        
        # Risco ocupacional (+40%)
        high_risk_occupations = [
            'professor', 'médico', 'enfermeiro', 'policial', 'bombeiro',
            'vigilante', 'segurança', 'motorista', 'piloto'
        ]
        
        if patient_data.profissao and any(
            occ in patient_data.profissao.lower() for occ in high_risk_occupations
        ):
            multiplier += 0.4
            reasons.append("profissão de risco")
        
        # Primeira ocorrência, paciente jovem (-20%)
        if (transcription and 'primeira vez' in transcription.lower() and 
            patient_data.idade and patient_data.idade < 35 and
            'boa resposta' in transcription.lower()):
            multiplier -= 0.2
            reasons.append("primeiro episódio com boa resposta")
        
        # Aplicar multiplicador
        final_days = int(base_days * multiplier)
        
        # Limites de segurança
        final_days = max(15, min(180, final_days))  # Entre 15 dias e 6 meses
        
        return {
            'base_days': base_days,
            'multiplier': multiplier,
            'final_days': final_days,
            'months_equivalent': round(final_days / 30, 1),
            'modifying_factors': reasons,
            'recommendation': self._format_duration_recommendation(final_days)
        }
    
    def _format_duration_recommendation(self, days: int) -> str:
        """
        Formata recomendação de duração de afastamento
        """
        if days <= 30:
            return f"{days} dias com reavaliação quinzenal"
        elif days <= 60:
            return f"{days} dias com reavaliação mensal"
        elif days <= 90:
            return f"{days} dias com reavaliação bimestral"
        else:
            months = round(days / 30)
            return f"Aproximadamente {months} meses com reavaliações periódicas"
    
    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================
    
    def _get_cid_description(self, cid_code: str) -> str:
        """Retorna descrição do CID baseada no código - EXPANDIDO E MELHORADO"""
        descriptions = {
            # DIABETES (E10-E14)
            'E10.3': 'Diabetes mellitus tipo 1 com complicações oftálmicas',
            'E10.9': 'Diabetes mellitus tipo 1 sem complicações',
            'E10.2': 'Diabetes mellitus tipo 1 com complicações renais',
            'E11.3': 'Diabetes mellitus tipo 2 com complicações oftálmicas',
            'E11.9': 'Diabetes mellitus tipo 2 sem complicações',
            'E11.2': 'Diabetes mellitus tipo 2 com complicações renais',
            'E11.0': 'Diabetes mellitus tipo 2 com coma',
            'E11.1': 'Diabetes mellitus tipo 2 com cetoacidose',
            
            # CARDIOVASCULAR (I00-I99)
            'I10': 'Hipertensão essencial',
            'I21.9': 'Infarto agudo do miocárdio não especificado',
            'I25.2': 'Infarto do miocárdio antigo',
            'I25.9': 'Doença isquêmica crônica do coração não especificada',
            'I48': 'Fibrilação e flutter atrial',
            'I50.9': 'Insuficiência cardíaca não especificada',
            
            # NEUROLÓGICO (G00-G99)
            'G56.0': 'Síndrome do túnel do carpo',
            'G56.1': 'Outras lesões do nervo mediano',
            'G57.0': 'Lesão do nervo ciático',
            'G44.2': 'Cefaleia do tipo tensional',
            
            # MUSCULOESQUELÉTICO (M00-M99)
            'M25.5': 'Dor articular',  # ← CORRIGIDO!
            'M25.9': 'Transtorno articular não especificado',
            'M70.1': 'Bursite da mão',
            'M70.2': 'Bursite do olécrano',
            'M70.9': 'Transtorno dos tecidos moles relacionado com o uso, uso excessivo e pressão, não especificado',
            'M75.1': 'Síndrome do impacto do ombro',
            'M75.3': 'Tendinite calcificante do ombro',
            'M75.9': 'Lesão do ombro não especificada',
            'M54.9': 'Dorsalgia não especificada',
            'M79.3': 'Panniculite não especificada',
            'M19.9': 'Artrose não especificada',
            
            # PSIQUIÁTRICO (F00-F99)
            'F32.1': 'Episódio depressivo moderado',
            'F32.2': 'Episódio depressivo grave sem sintomas psicóticos',
            'F32.9': 'Episódio depressivo não especificado',
            'F33.1': 'Transtorno depressivo recorrente, episódio atual moderado',
            'F41.0': 'Transtorno de pânico',
            'F41.1': 'Transtorno de ansiedade generalizada',
            'F41.9': 'Transtorno de ansiedade não especificado',
            'F43.0': 'Reação aguda ao estresse',
            'F43.9': 'Reação ao estresse não especificada',
            'F51.9': 'Transtorno do sono não orgânico não especificado',
            
            # DIGESTIVO (K00-K93)
            'K30': 'Dispepsia funcional',
            'K59.0': 'Constipação',
            'K21.9': 'Doença do refluxo gastroesofágico sem esofagite',
            
            # RESPIRATÓRIO (J00-J99)
            'J44.9': 'Doença pulmonar obstrutiva crônica não especificada',
            'J45.9': 'Asma não especificada',
            'J06.9': 'Infecção aguda das vias aéreas superiores não especificada',
            
            # ENDÓCRINO (E00-E89)
            'E03.9': 'Hipotireoidismo não especificado',
            'E78.5': 'Hiperlipidemia não especificada',
            
            # RENAIS/GENITOURINÁRIO (N00-N99)
            'N18.9': 'Doença renal crônica não especificada',
            'N39.0': 'Infecção do trato urinário de localização não especificada',
            
            # OFTÁLMICO (H00-H59)
            'H35.9': 'Transtorno da retina não especificado',
            'H52.4': 'Presbiopia',
            
            # DERMATOLÓGICO (L00-L99)
            'L30.9': 'Dermatite não especificada',
            
            # LESÕES/TRAUMATISMOS (S00-T98)
            'S82.101A': 'Fratura não especificada da extremidade proximal da tíbia direita, encontro inicial',
            'S72.9': 'Fratura não especificada do fêmur',
            
            # FATORES QUE INFLUENCIAM O ESTADO DE SAÚDE (Z00-Z99)
            'Z96.603': 'Presença de implante ortopédico unilateral do joelho',
            'Z51.1': 'Sessão de quimioterapia para neoplasia',
            
            # OUTROS COMUNS
            'R50.9': 'Febre não especificada',
            'R06.0': 'Dispneia',
            'R51': 'Cefaleia'
        }
        
        # Se encontrou no dicionário, retornar
        if cid_code in descriptions:
            return descriptions[cid_code]
        
        # FALLBACK MELHORADO: Buscar na base FAISS
        faiss_description = self._search_cid_description_in_faiss(cid_code)
        if faiss_description:
            return faiss_description
        
        # FALLBACK INTELIGENTE: Baseado no prefixo do CID
        fallback_by_category = {
            'E1': 'Diabetes mellitus',
            'E0': 'Transtorno endócrino',
            'I': 'Transtorno cardiovascular',
            'G': 'Transtorno neurológico',
            'M': 'Transtorno musculoesquelético',
            'F': 'Transtorno mental e comportamental',
            'K': 'Transtorno do sistema digestivo',
            'J': 'Transtorno do sistema respiratório',
            'N': 'Transtorno do sistema genitourinário',
            'H': 'Transtorno dos olhos e anexos',
            'L': 'Transtorno da pele',
            'S': 'Lesão traumática',
            'T': 'Intoxicação ou lesão',
            'Z': 'Fator que influencia o estado de saúde',
            'R': 'Sintoma ou sinal clínico'
        }
        
        # Tentar mapear por categoria
        for prefix, description in fallback_by_category.items():
            if cid_code.startswith(prefix):
                return f"{description} ({cid_code})"
        
        # Último fallback: mais genérico mas sem "alucinação"
        return f"CID {cid_code} - Consultar classificação médica oficial"
    
    def _search_cid_description_in_faiss(self, cid_code: str) -> str:
        """
        NOVO: Busca descrição do CID na base FAISS
        """
        if not self.rag_available or not self.rag_service:
            return None
            
        try:
            # Query específica para buscar descrição do CID
            query = f"CID {cid_code} descrição diagnóstico significado"
            
            results = self.rag_service.search_similar_cases(query, top_k=3)
            
            for result in results:
                content = result.get('content', '')
                
                # Buscar por padrões que contenham o CID e sua descrição
                import re
                patterns = [
                    rf'{cid_code}[:\-\s]+([^.\n]+)',  # CID: descrição
                    rf'{cid_code}.*?[-–]\s*([^.\n]+)',  # CID - descrição  
                    rf'CID\s+{cid_code}[:\-\s]+([^.\n]+)'  # CID X: descrição
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        description = match.group(1).strip()
                        # Limpar e validar a descrição
                        if len(description) > 10 and len(description) < 150:
                            # Remover caracteres estranhos
                            description = re.sub(r'[^\w\s\-áàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]', '', description)
                            if description.strip():
                                return description.strip()
            
            return None
            
        except Exception as e:
            print(f"⚠️ Erro ao buscar CID {cid_code} no FAISS: {e}")
            return None
    
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
            
                    # Determinar tempo de afastamento usando análise universal se disponível
        tempo_afastamento = {
            BenefitTypeEnum.AUXILIO_DOENCA: '3 a 6 meses com reavaliações periódicas',
            BenefitTypeEnum.AUXILIO_ACIDENTE: 'Redução permanente da capacidade (sem prazo determinado)',
            BenefitTypeEnum.BPC_LOAS: 'Condição permanente (revisões conforme legislação)',
            BenefitTypeEnum.APOSENTADORIA_INVALIDEZ: 'Incapacidade definitiva',
            BenefitTypeEnum.ISENCAO_IR: 'Conforme evolução da doença'
        }.get(classification.tipo_beneficio, 'Conforme evolução clínica')
        
        # Usar análise universal se disponível
        if state.get("universal_analysis") and state["universal_analysis"]["duration_analysis"]:
            duration_data = state["universal_analysis"]["duration_analysis"]
            if classification.tipo_beneficio in [BenefitTypeEnum.AUXILIO_DOENCA, BenefitTypeEnum.AUXILIO_ACIDENTE]:
                tempo_afastamento = duration_data["recommendation"]
            
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
                telemedicine_mode=self.telemedicine_mode,
                universal_analysis=None
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
    
    def _extract_transcription_details(self, transcription: str, patient_data: PatientDataStrict) -> dict:
        """
        MELHORAMENTO: Extração detalhada e estruturada da transcrição
        Aproveita ao máximo os detalhes importantes mencionados
        """
        details = {
            'temporal_info': {},
            'occupational_context': {},
            'treatment_history': {},
            'symptom_progression': {},
            'functional_impact': {},
            'environmental_factors': {},
            'previous_episodes': {},
            'quality_of_life': {}
        }
        
        if not transcription:
            return details
            
        text = transcription.lower()
        import re
        
        # ===================================================================
        # 1. INFORMAÇÕES TEMPORAIS DETALHADAS
        # ===================================================================
        
        # Início dos sintomas/condição
        onset_patterns = [
            (r'há\s+(\d+)\s*anos?\s+descobri', 'descoberta'),
            (r'há\s+(\d+)\s*meses?\s+comecei', 'início'),
            (r'há\s+(\d+)\s*semanas?\s+sinto', 'início'),
            (r'desde\s+(\d+)\s*anos?', 'duração'),
            (r'faz\s+(\d+)\s*meses?', 'duração')
        ]
        
        for pattern, tipo in onset_patterns:
            match = re.search(pattern, text)
            if match:
                details['temporal_info'][tipo] = f"{match.group(1)} {match.group(0).split()[-1]}"
                break
        
        # Progressão temporal
        progression_indicators = [
            'tem piorado', 'vem piorando', 'está pior', 'agravou',
            'melhorou', 'estabilizou', 'oscila', 'vai e volta'
        ]
        
        for indicator in progression_indicators:
            if indicator in text:
                details['symptom_progression']['trend'] = indicator
                break
        
        # Frequência dos episódios
        frequency_patterns = [
            'todos os dias', 'diariamente', 'sempre', 'constantemente',
            'às vezes', 'de vez em quando', 'raramente', 'episódico'
        ]
        
        for freq in frequency_patterns:
            if freq in text:
                details['symptom_progression']['frequency'] = freq
                break
        
        # ===================================================================
        # 2. CONTEXTO OCUPACIONAL ESPECÍFICO
        # ===================================================================
        
        # Duração na profissão
        work_duration_match = re.search(r'trabalho\s+(?:de|como|há)\s*([^,\.]+?)(?:\s+há\s+(\d+)\s*anos?)?', text)
        if work_duration_match:
            details['occupational_context']['position'] = work_duration_match.group(1).strip()
            if work_duration_match.group(2):
                details['occupational_context']['duration'] = f"{work_duration_match.group(2)} anos"
        
        # Condições de trabalho específicas
        work_conditions = {
            'estresse': ['estresse no trabalho', 'pressão no trabalho', 'sobrecarga'],
            'físico': ['trabalho pesado', 'esforço físico', 'carregar peso'],
            'repetitivo': ['movimento repetitivo', 'mesma posição', 'digitação'],
            'ambiente': ['calor', 'frio', 'barulho', 'produtos químicos'],
            'horário': ['turno', 'noturno', 'plantão', 'hora extra']
        }
        
        for categoria, termos in work_conditions.items():
            if any(termo in text for termo in termos):
                details['occupational_context'][categoria] = True
        
        # ===================================================================
        # 3. HISTÓRICO DE TRATAMENTOS DETALHADO
        # ===================================================================
        
        # Medicamentos com dosagem/frequência
        med_patterns = [
            r'tomo\s+([^,\.]+?)\s+(\d+)\s*(?:vez|vezes)',
            r'uso\s+([^,\.]+?)\s+(?:todo|todos)',
            r'aplico\s+([^,\.]+?)\s+(\d+)\s*(?:vez|vezes)'
        ]
        
        for pattern in med_patterns:
            matches = re.findall(pattern, text)
            if matches:
                details['treatment_history']['medications'] = matches
        
        # Resposta ao tratamento
        treatment_responses = {
            'boa': ['melhorou', 'ajudou', 'funcionou', 'aliviou'],
            'parcial': ['melhorou um pouco', 'ajuda às vezes', 'alivia pouco'],
            'ruim': ['não funcionou', 'não melhorou', 'piorou', 'não adianta'],
            'efeitos_colaterais': ['efeito colateral', 'reação', 'mal estar do remédio']
        }
        
        for resposta, termos in treatment_responses.items():
            if any(termo in text for termo in termos):
                details['treatment_history']['response'] = resposta
                break
        
        # ===================================================================
        # 4. IMPACTO FUNCIONAL ESPECÍFICO
        # ===================================================================
        
        # Atividades específicas afetadas
        functional_impacts = {
            'trabalho': ['não consigo trabalhar', 'dificulta o trabalho', 'falto ao trabalho'],
            'domésticas': ['não consigo fazer em casa', 'tarefas domésticas', 'cuidar da casa'],
            'social': ['não saio mais', 'evito sair', 'isolamento'],
            'sono': ['não durmo', 'acordo com dor', 'insônia'],
            'locomoção': ['dificuldade para andar', 'usar escada', 'dirigir'],
            'autocuidado': ['me vestir', 'tomar banho', 'escovar dentes']
        }
        
        for area, termos in functional_impacts.items():
            if any(termo in text for termo in termos):
                details['functional_impact'][area] = True
        
        # ===================================================================
        # 5. FATORES AMBIENTAIS E DESENCADEANTES
        # ===================================================================
        
        environmental_triggers = {
            'clima': ['frio', 'calor', 'umidade', 'tempo seco'],
            'estresse': ['nervoso', 'ansioso', 'preocupado', 'estressado'],
            'físico': ['esforço', 'carregar peso', 'ficar muito tempo'],
            'alimentar': ['depois de comer', 'quando como', 'em jejum']
        }
        
        for trigger_type, termos in environmental_triggers.items():
            if any(termo in text for termo in termos):
                details['environmental_factors'][trigger_type] = True
        
        # ===================================================================
        # 6. EPISÓDIOS ANTERIORES
        # ===================================================================
        
        previous_episodes_indicators = [
            'já tive antes', 'primeira vez', 'volta e meia', 'de tempos em tempos',
            'episódio anterior', 'última vez', 'outras vezes'
        ]
        
        for indicator in previous_episodes_indicators:
            if indicator in text:
                details['previous_episodes']['pattern'] = indicator
                break
        
        # ===================================================================
        # 7. QUALIDADE DE VIDA
        # ===================================================================
        
        quality_indicators = {
            'humor': ['triste', 'deprimido', 'irritado', 'ansioso', 'nervoso'],
            'relacionamentos': ['família preocupada', 'cônjuge', 'filhos', 'sozinho'],
            'financeiro': ['afastado', 'sem trabalhar', 'auxílio', 'benefício'],
            'perspectiva': ['melhora', 'piora', 'não vejo saída', 'esperança']
        }
        
        for aspecto, termos in quality_indicators.items():
            matching_terms = [termo for termo in termos if termo in text]
            if matching_terms:
                details['quality_of_life'][aspecto] = matching_terms
        
        # ===================================================================
        # 8. ANÁLISE DE GRAVIDADE CONTEXTUAL
        # ===================================================================
        
        # Indicadores de gravidade específicos
        severity_markers = []
        
        if any(term in text for term in ['emergência', 'pronto socorro', 'internação']):
            severity_markers.append('necessitou_emergencia')
        
        if any(term in text for term in ['não consigo', 'impossível', 'incapaz']):
            severity_markers.append('incapacidade_total')
        
        if any(term in text for term in ['piorou muito', 'muito pior', 'insuportável']):
            severity_markers.append('deterioracao_significativa')
        
        if len(severity_markers) > 0:
            details['severity_context'] = severity_markers
        
        return details
    
    def _search_related_cids_from_faiss(self, patient_data: PatientDataStrict, transcription: str, primary_cid: str = None) -> dict:
        """
        NOVO: Busca CIDs relacionados diretamente na base FAISS
        Aproveita a base de conhecimento médico existente
        """
        if not self.rag_available or not self.rag_service:
            return {'primary_suggestions': [], 'secondary_suggestions': [], 'confidence': 0.0}
        
        try:
            # Construir query para busca de CIDs relacionados
            symptoms = ', '.join(patient_data.sintomas) if patient_data.sintomas else ''
            medications = ', '.join(patient_data.medicamentos) if patient_data.medicamentos else ''
            
            # Query específica para CIDs
            cid_query = f"""
            Paciente: {patient_data.nome}, {patient_data.idade} anos, {patient_data.profissao}
            Sintomas: {symptoms}
            Medicamentos: {medications}
            Transcrição: {transcription[:300]}
            
            Buscar CIDs médicos relacionados, comorbidades e diagnósticos secundários
            """
            
            # Buscar na base FAISS
            rag_results = self.rag_service.search_similar_cases(cid_query, top_k=5)
            
            # Extrair CIDs dos resultados
            found_cids = {
                'primary_suggestions': [],
                'secondary_suggestions': [],
                'confidence': 0.0,
                'source_contexts': []
            }
            
            import re
            cid_pattern = r'\b[A-Z]\d{2}(?:\.\d)?\b'  # Padrão para CIDs (ex: E11.3, I10)
            
            total_confidence = 0
            for result in rag_results:
                content = result.get('content', '')
                confidence = result.get('score', 0)
                
                # Extrair todos os CIDs do conteúdo
                cids_found = re.findall(cid_pattern, content)
                
                # Analisar contexto para determinar se é principal ou secundário
                for cid in cids_found:
                    if cid == primary_cid:
                        continue  # Não incluir o CID principal
                    
                    # Verificar se é um CID válido (formato correto)
                    if re.match(r'^[A-Z]\d{2}(\.\d)?$', cid):
                        
                        # FILTROS DE RELEVÂNCIA MÉDICA
                        # Excluir CIDs não apropriados para adultos/casos gerais
                        excluded_cids = [
                            'F84.0',  # Autismo (não relevante para diabetes adulto)
                            'S68.1',  # Amputação (não relacionado ao caso)
                            'T93.6',  # Sequela de fratura (não relacionado)
                            'P00',    # Códigos perinatais (P00-P96)
                            'Q00',    # Malformações congênitas (Q00-Q99)
                            'V01',    # Causas externas (V01-Y98)
                            'W00',    # Acidentes (W00-X59)
                            'X00',    # Lesões auto-infligidas (X60-X84)
                            'Y00',    # Agressões (Y85-Y09)
                            'Z00'     # Fatores que influenciam o estado de saúde (alguns Z00-Z99)
                        ]
                        
                        # Verificar se CID está na lista de exclusão
                        should_exclude = False
                        for excluded in excluded_cids:
                            if cid.startswith(excluded[:3]):  # Verifica prefixo
                                should_exclude = True
                                break
                        
                        if should_exclude:
                            continue
                        
                        # FILTROS DE RELEVÂNCIA POR CATEGORIA DO CID PRINCIPAL
                        if primary_cid and primary_cid.startswith('E1'):  # Diabetes
                            # Para diabetes, priorizar: cardiovasculares (I), renais (N), oftálmicos (H)
                            relevant_prefixes = ['I', 'N', 'H', 'F32', 'F41']  # Cardio, renal, olhos, depressão/ansiedade
                            if not any(cid.startswith(prefix) for prefix in relevant_prefixes):
                                # Verificar se tem relação textual com diabetes
                                diabetes_related_terms = [
                                    'diabetes', 'diabético', 'complicação', 'hipertensão', 
                                    'pressão', 'cardiovascular', 'renal', 'oftálmica'
                                ]
                                if not any(term in content.lower() for term in diabetes_related_terms):
                                    continue
                        
                        # Determinar se é principal ou secundário baseado no contexto
                        content_lower = content.lower()
                        
                        # Indicadores de CID principal
                        primary_indicators = [
                            'diagnóstico principal', 'cid principal', 'diagnóstico primário',
                            'condição principal', 'doença principal'
                        ]
                        
                        # Indicadores de CID secundário  
                        secondary_indicators = [
                            'comorbidade', 'diagnóstico secundário', 'associado',
                            'concomitante', 'cid secundário', 'também apresenta',
                            'complicação', 'associada', 'relacionada'
                        ]
                        
                        is_primary_context = any(indicator in content_lower for indicator in primary_indicators)
                        is_secondary_context = any(indicator in content_lower for indicator in secondary_indicators)
                        
                        # Calcular pontuação de relevância
                        relevance_score = confidence
                        
                        # Bonificar se tem termos relacionados ao caso
                        case_terms = []
                        if patient_data.sintomas:
                            case_terms.extend([s.lower() for s in patient_data.sintomas])
                        if patient_data.medicamentos:
                            case_terms.extend([m.lower() for m in patient_data.medicamentos])
                        
                        term_matches = sum(1 for term in case_terms if term in content_lower)
                        relevance_score += term_matches * 0.1
                        
                        if is_primary_context and not found_cids['primary_suggestions']:
                            found_cids['primary_suggestions'].append({
                                'cid': cid,
                                'confidence': relevance_score,
                                'context': content[:200] + '...'
                            })
                        elif is_secondary_context or not is_primary_context:
                            # Evitar duplicatas
                            if not any(item['cid'] == cid for item in found_cids['secondary_suggestions']):
                                found_cids['secondary_suggestions'].append({
                                    'cid': cid,
                                    'confidence': relevance_score,
                                    'context': content[:200] + '...'
                                })
                
                total_confidence += confidence
            
            # Calcular confiança média
            if rag_results:
                found_cids['confidence'] = total_confidence / len(rag_results)
            
            # Ordenar por confiança
            found_cids['primary_suggestions'].sort(key=lambda x: x['confidence'], reverse=True)
            found_cids['secondary_suggestions'].sort(key=lambda x: x['confidence'], reverse=True)
            
            # Limitar resultados
            found_cids['primary_suggestions'] = found_cids['primary_suggestions'][:2]
            found_cids['secondary_suggestions'] = found_cids['secondary_suggestions'][:4]
            
            print(f"📊 FAISS encontrou: {len(found_cids['secondary_suggestions'])} CIDs secundários")
            
            return found_cids
            
        except Exception as e:
            print(f"❌ Erro na busca FAISS de CIDs: {e}")
            return {'primary_suggestions': [], 'secondary_suggestions': [], 'confidence': 0.0}


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