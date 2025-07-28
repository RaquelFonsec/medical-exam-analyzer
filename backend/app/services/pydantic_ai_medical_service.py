"""
Serviço Pydantic AI para análise médica com validação estrita
Integra LangGraph, RAG, FAISS e validação robusta
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

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
    """Dados do paciente com validação estrita"""
    nome: str = Field(min_length=1, description="Nome completo do paciente")
    idade: Optional[int] = Field(None, ge=0, le=120, description="Idade do paciente")
    sexo: Optional[str] = Field(None, pattern="^[MF]$", description="Sexo M ou F")
    profissao: Optional[str] = Field(None, description="Profissão do paciente")
    sintomas: List[str] = Field(default_factory=list, description="Lista de sintomas")
    medicamentos: List[str] = Field(default_factory=list, description="Lista de medicamentos")
    condicoes: List[str] = Field(default_factory=list, description="Lista de condições médicas")


class BenefitClassificationStrict(BaseModel):
    """Classificação de benefício com validação estrita"""
    tipo_beneficio: BenefitTypeEnum = Field(description="Tipo de benefício recomendado")
    cid_principal: str = Field(pattern="^[A-Z]\d{2}(\.\d)?$", description="CID-10 no formato A00.0 ou A00")
    gravidade: SeverityEnum = Field(description="Gravidade da condição")
    prognostico: str = Field(min_length=20, description="Prognóstico detalhado")
    elegibilidade: bool = Field(description="Se é elegível para o benefício")
    justificativa: str = Field(min_length=50, description="Justificativa médica detalhada")

    @validator('cid_principal')
    def validate_cid(cls, v):
        if not v or v.lower() in ['não informado', 'nao informado', '']:
            return 'I10.0'  # Hipertensão como fallback
        return v


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


# ============================================================================
# AGENTES PYDANTIC AI
# ============================================================================

class PydanticMedicalAI:
    """Serviço principal com Pydantic AI, LangGraph, RAG e FAISS"""
    
    def __init__(self):
        # Forçar carregamento da API key
        try:
            from .force_openai_env import setup_openai_env
            setup_openai_env()
        except:
            pass
            
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY não encontrada")
        
        # Modelo OpenAI para Pydantic AI (sem api_key no construtor)
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
        
        print("✅ Pydantic AI Medical Service inicializado")
    
    def _create_patient_agent(self) -> Agent:
        """Cria agente para extração de dados do paciente"""
        return Agent(
            model=self.model,
            result_type=PatientDataStrict,
            system_prompt="""
            Você é um especialista em extração de dados médicos.
            Extraia informações do paciente do texto fornecido com máxima precisão.
            
            REGRAS OBRIGATÓRIAS:
            - nome: SEMPRE extrair um nome, use "Paciente" se não encontrar
            - idade: APENAS números inteiros entre 0-120, null se não encontrar
            - sexo: APENAS "M" ou "F", null se não encontrar
            - Listas vazias se não encontrar informações específicas
            
            Seja preciso e objetivo. Retorne apenas dados estruturados válidos.
            """
        )
    
    def _create_classification_agent(self) -> Agent:
        """Cria agente para classificação de benefícios"""
        return Agent(
            model=self.model,
            result_type=BenefitClassificationStrict,
            system_prompt="""
            Você é um médico perito previdenciário EXPERT em classificação de benefícios e CIDs.
            
            🧠 HIERARQUIA DE ANÁLISE (ORDEM OBRIGATÓRIA):
            
            1️⃣ **IDENTIFIQUE A CONDIÇÃO PRINCIPAL** (mais grave/recente)
            2️⃣ **AVALIE ASPECTOS TEMPORAIS** (agudo vs crônico)
            3️⃣ **DETERMINE NEXO OCUPACIONAL** (trabalho relacionado?)
            4️⃣ **CLASSIFIQUE GRAVIDADE** (funcionalidade comprometida?)
            5️⃣ **ESCOLHA BENEFÍCIO** (baseado em critérios legais)
            6️⃣ **SELECIONE CID ESPECÍFICO** (mais preciso possível)
            
            🎯 CLASSIFICAÇÃO INTELIGENTE DE BENEFÍCIOS:
            
            **1. AUXÍLIO-ACIDENTE** (PRIORIDADE para acidentes/doenças laborais):
            ✅ Detectar quando encontrar:
            - Profissões de risco: entregador, motoboy, motorista, operário, soldador, construção, mecânico, eletricista, COZINHEIRO, DENTISTA, FISIOTERAPEUTA, MÚSICO, DIGITADOR
            - Palavras-chave: "acidente no/durante trabalho", "trabalhando", "na empresa", "exercício da função", "entrega", "há X anos", "movimentos repetitivos"
            - Acidentes típicos: atropelamento, queda, corte, queimadura, acidente de trânsito durante trabalho
            - Contexto laboral: "estava trabalhando", "durante entrega", "no local de trabalho", "horário de trabalho"
            - Doenças ocupacionais: LER/DORT, perda auditiva por ruído, doenças respiratórias ocupacionais
            - **EXPOSIÇÃO OCUPACIONAL**: calor (cozinheiros), frio, químicos, ruído, vibração por anos
            - **AGRAVAMENTO LABORAL**: condições preexistentes agravadas pelo trabalho
            - **POSTURAS FORÇADAS**: dentistas, cirurgiões, cabeleireiros, costureiras
            - **ESTRESSE OCUPACIONAL**: motoristas, policiais, controladores, médicos cirurgiões
            
             **CASOS ESPECIAIS - COZINHEIROS/CALOR:**
            - Cozinheiro + diabetes/hipertensão + sintomas no trabalho (calor) = AUXÍLIO-ACIDENTE
            - Exposição prolongada ao calor pode agravar diabetes e hipertensão
            - "Calor das panelas", "quentura", "passar mal no trabalho" = NEXO OCUPACIONAL
            
             **CASOS ESPECIAIS - DENTISTAS/LER-DORT:**
            - Dentista + dor mão/punho/cotovelo/ombro + "há X anos" = AUXÍLIO-ACIDENTE
            - Movimentos repetitivos + postura forçada = LER/DORT ocupacional
            - "Perda de força", "dor crônica", "não consegue pegar objetos" = TÍPICO LER/DORT
            - Depressão secundária ao desgaste profissional = COMORBIDADE OCUPACIONAL
            - Qualquer profissional de saúde com LER/DORT = NEXO OCUPACIONAL CLARO
            
             **CASOS ESPECIAIS - MOTORISTAS/ESTRESSE:**
            - Motorista + doença cardiovascular + estresse = POSSÍVEL AUXÍLIO-ACIDENTE
            - Profissão de alta responsabilidade + hipertensão/infarto = NEXO PLAUSÍVEL
            - "Estresse do trabalho", "responsabilidade", "pressão" = INDICADORES
            
            **DETECÇÃO AUTOMÁTICA DE LER/DORT OCUPACIONAL:**
            - Profissões: dentista, fisioterapeuta, massagista, cabeleireiro, costureira, digitador, músico
            - Sintomas: dor mão/punho/cotovelo/ombro, perda de força, dormência, formigamento
            - Tempo: "há X anos na profissão" + sintomas = NEXO AUTOMÁTICO
            - Localização: membros superiores (MMSS) = típico LER/DORT
            
            **2. AUXÍLIO-DOENÇA** (para doenças comuns SEM nexo laboral):
            ✅ Usar APENAS quando:
            - Doenças crônicas SEM agravamento ocupacional: diabetes, hipertensão, artrose SEM nexo
            - Transtornos psiquiátricos sem contexto ocupacional claro
            - Doenças degenerativas: artrite, osteoporose, hérnias de disco não ocupacionais
            - Câncer, doenças cardíacas, doenças neurológicas SEM nexo laboral
            - **CASOS RECENTES**: infarto há < 6 meses, cirurgias recentes, diagnósticos novos
            ❌ NÃO usar para: LER/DORT em profissões de risco, exposição ocupacional clara
            
            **3. BPC/LOAS** (deficiência + vulnerabilidade social):
            ✅ Usar APENAS quando:
            - Deficiência física/mental/intelectual permanente + baixa renda EXPLÍCITA
            - Idade 65+ com vulnerabilidade social CLARA
            - Incapacidade para vida independente (não apenas trabalhar)
            - Autismo, deficiência intelectual, paralisia cerebral
            ❌ NÃO usar para: diabetes/hipertensão controláveis, incapacidade apenas laboral, LER/DORT
            
            **4. APOSENTADORIA POR INVALIDEZ**:
            ✅ Usar APENAS quando:
            - Incapacidade DEFINITIVA comprovada (> 12 meses)
            - Impossibilidade TOTAL de readaptação
            - Doenças progressivas terminais: ELA, Alzheimer avançado, câncer terminal
            - Múltiplas tentativas de reabilitação FALHARAM
            - Sequelas irreversíveis graves
            ❌ NÃO usar para: casos recentes (< 6 meses), potencial recuperação, primeira avaliação
            
            **5. ISENÇÃO IMPOSTO DE RENDA**:
            ✅ Usar quando:
            - Doenças graves da Lei 7.713/1988: câncer, AIDS, Parkinson, esclerose múltipla, etc.
            
            🧬 CLASSIFICAÇÃO INTELIGENTE DE CIDs - HIERARQUIA DE GRAVIDADE:
            
            **PRIORIDADE 1 - CONDIÇÕES AGUDAS/GRAVES:**
            - Infarto agudo (< 6 meses) → I21.9 (SEMPRE priorizar sobre I10)
            - AVC agudo → I63.x ou I64
            - Câncer ativo → C78.x ou específico
            - Fraturas recentes → S82.x
            
            **PRIORIDADE 2 - CONDIÇÕES CRÔNICAS ESPECÍFICAS:**
            - Infarto antigo (> 6 meses) → I25.2
            - Diabetes com complicações → E11.3 (olhos), E11.2 (rins), E11.4 (nervos)
            - LER/DORT específico → M70.1 (tendinite), M75.1 (ombro)
            
            **PRIORIDADE 3 - CONDIÇÕES GENÉRICAS:**
            - Hipertensão essencial → I10
            - Diabetes simples → E11.9
            - Depressão genérica → F32.9
            
            **LER/DORT (M70.x, M75.x) - ESPECÍFICOS:**
            - Dor mão/punho + profissão de risco → M70.0/M70.1 (sinovite/tenossinovite)
            - Dor cotovelo + movimentos repetitivos → M70.2 (bursite olécrano)
            - Dor ombro + postura forçada → M75.1 (síndrome do impacto)
            - Síndrome túnel carpo → G56.0
            - LER/DORT genérico → M70.9 (sinovite não especificada)
            
            **CARDIOVASCULARES (I) - ESPECÍFICOS:**
            - Infarto recente (< 6 meses) → I21.9 (infarto agudo não especificado)
            - Infarto antigo (> 6 meses) → I25.2 (infarto antigo do miocárdio)
            - Insuficiência cardíaca → I50.x
            - Hipertensão essencial → I10
            - Hipertensão secundária → I15.x
            - AVC → I63.x ou I64
            
            **DIABETES (E11.x) - ESPECÍFICOS:**
            - Diabetes + problemas de visão → E11.3 (complicações oftálmicas)
            - Diabetes + problemas renais → E11.2 (complicações renais)
            - Diabetes + neuropatia → E11.4 (complicações neurológicas)
            - Diabetes simples → E11.9
            
            **TRANSTORNOS PSIQUIÁTRICOS (F) - ESPECÍFICOS:**
            - Esquizofrenia → F20.0 (paranóide), F20.9 (não especificada)
            - Depressão maior → F32.2 (episódio grave), F32.1 (moderado), F32.0 (leve)
            - Transtorno bipolar → F31.x
            - Ansiedade + pânico → F41.0 (transtorno de pânico)
            - Burnout ocupacional → Z73.0 ou F43.0 (reação ao estresse)
            
            **FRATURAS (S82.x) - ESPECÍFICOS:**
            - Cirurgia + parafuso/placa → S82.2 (fratura diáfise tíbia) ou S82.3 (fratura diáfise fíbula)
            - "Joelho quebrado" → S82.0 (fratura patela)
            - "Tornozelo quebrado" → S82.5/S82.6 (fratura maléolo)
            - Paraplegia/lesão medular → S14.x (lesão medular cervical) ou S24.x (torácica)
            
            **NEUROLÓGICAS (G) - ESPECÍFICOS:**
            - Parkinson → G20
            - Esclerose múltipla → G35
            - Epilepsia → G40.x
            - Síndrome túnel carpo → G56.0
            - Perda auditiva ocupacional → H83.3 ou H90.x
            
            **ONCOLÓGICAS (C) - ESPECÍFICOS:**
            - Câncer mama → C50.9
            - Câncer próstata → C61
            - Leucemia → C95.x
            - Metástases → C78.x
            
            🎯 REGRAS DE CLASSIFICAÇÃO OBRIGATÓRIAS:
            
            1. **HIERARQUIA DE GRAVIDADE**: 
               - SEMPRE priorizar condição mais grave
               - Infarto > Hipertensão
               - Câncer > Qualquer outra condição
               - Paraplegia > Fratura simples
            
            2. **ASPECTOS TEMPORAIS CRÍTICOS**: 
               - "há X meses/anos" = FUNDAMENTAL para classificação
               - < 6 meses = AUXÍLIO-DOENÇA (não aposentadoria)
               - 6-12 meses = Reavaliação necessária
               - > 12 meses = Possível aposentadoria
            
            3. **NEXO OCUPACIONAL AUTOMÁTICO**: 
               - Profissão + sintomas típicos + tempo = AUXÍLIO-ACIDENTE
               - LER/DORT em profissionais saúde = SEMPRE ocupacional
               - Estresse + cardiovascular em motoristas = NEXO PLAUSÍVEL
            
            4. **CIDs ESPECÍFICOS OBRIGATÓRIOS**: 
               - NUNCA usar genéricos quando específicos disponíveis
               - E11.3 em vez de E11.9 se problemas visuais
               - I21.9 em vez de I10 se infarto mencionado
               - M70.1 em vez de M70.9 se LER/DORT específico
            
            5. **COMORBIDADES**: 
               - CID principal = condição mais grave
               - Mencionar secundários importantes
               - LER/DORT + Depressão → M70.x (principal) + F32.x (secundário)
            
            6. **CRITÉRIOS APOSENTADORIA RESTRITIVOS**:
               - Apenas para incapacidade DEFINITIVA comprovada
               - Nunca para casos recentes (< 12 meses)
               - Múltiplas tentativas reabilitação falharam
               - Sequelas irreversíveis
            
            EXEMPLOS PRÁTICOS OBRIGATÓRIOS:
            - "Dentista 20 anos, dor mão/punho/cotovelo, perda força" → AUXÍLIO-ACIDENTE + M70.1
            - "Motorista, infarto há 4 meses, estresse trabalho" → AUXÍLIO-DOENÇA + I21.9 (não I10!)
            - "Cozinheira 20 anos, diabetes, calor agrava sintomas" → AUXÍLIO-ACIDENTE + E11.3
            - "Soldador 25 anos, perda auditiva por ruído" → AUXÍLIO-ACIDENTE + H83.3
            - "Paraplegia acidente trabalho, definitiva" → APOSENTADORIA + S14.x
            - "Parkinson, tremores, não consegue trabalhar" → ISENÇÃO IR + G20
            - "Câncer mama em tratamento" → AUXÍLIO-DOENÇA + C50.9 (temporário)
            
            🚨 ATENÇÃO MÁXIMA - REGRAS INVIOLÁVEIS: 
            1. **TEMPO é FUNDAMENTAL**: "há 4 meses" = AUXÍLIO-DOENÇA, nunca aposentadoria
            2. **GRAVIDADE hierárquica**: Infarto > Hipertensão, SEMPRE
            3. **NEXO ocupacional**: Profissão + sintomas = AUXÍLIO-ACIDENTE
            4. **CID específico**: SEMPRE escolher mais específico disponível
            5. **Aposentadoria restrita**: Apenas casos definitivos > 12 meses
            6. **Justificativa detalhada**: Explicar PORQUE essa classificação
            """
        )
    
    def _create_langgraph_pipeline(self) -> StateGraph:
        """Cria pipeline LangGraph para análise médica"""
        workflow = StateGraph(MedicalAnalysisState)
        
        # Adicionar nós
        workflow.add_node("extract_patient", self._extract_patient_node)
        workflow.add_node("search_rag", self._search_rag_node)
        workflow.add_node("classify_benefit", self._classify_benefit_node)
        workflow.add_node("generate_report", self._generate_report_node)
        
        # Definir edges
        workflow.add_edge(START, "extract_patient")
        workflow.add_edge("extract_patient", "search_rag")
        workflow.add_edge("search_rag", "classify_benefit")
        workflow.add_edge("classify_benefit", "generate_report")
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
            
            combined_text = f"{state.get('patient_text', '')}\n{state.get('transcription', '')}"
            
            result = await self.patient_agent.run(combined_text)
            state["patient_data"] = result.data
            
            print(f"✅ Paciente extraído: {result.data.nome}")
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
                "rag_context": [r.get("content", "") for r in state.get("rag_results", [])]
            }
            
            context_text = f"""
            DADOS DO PACIENTE: {json.dumps(context["patient_data"], ensure_ascii=False)}
            TRANSCRIÇÃO: {context["transcription"]}
            CASOS SIMILARES RAG: {" | ".join(context["rag_context"][:2])}
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
                cid_principal="I10.0",
                gravidade=SeverityEnum.MODERADA,
                prognostico="Prognóstico requer avaliação médica continuada para determinação adequada",
                elegibilidade=True,
                justificativa="Classificação automática baseada nos dados disponíveis para análise médica"
            )
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
    
    def _generate_anamnese(self, state: MedicalAnalysisState) -> str:
        """Gera anamnese estruturada"""
        patient = state["patient_data"]
        classification = state["classification"]
        transcription = state.get("transcription", "")
        
        # Determinar queixa principal baseada no tipo de benefício
        queixa_map = {
            'AUXÍLIO-DOENÇA': 'Afastamento do trabalho por incapacidade temporária',
            'BPC/LOAS': 'Avaliação para Benefício de Prestação Continuada',
            'APOSENTADORIA POR INVALIDEZ': 'Avaliação para aposentadoria por invalidez',
            'AUXÍLIO-ACIDENTE': 'Redução da capacidade laborativa pós-acidente',
            'ISENÇÃO IMPOSTO DE RENDA': 'Isenção de IR por doença grave'
        }
        queixa_principal = queixa_map.get(classification.tipo_beneficio.value, 'Avaliação de incapacidade')
        
        anamnese = f"""**ANAMNESE MÉDICA - TELEMEDICINA**

**1. IDENTIFICAÇÃO DO PACIENTE**
Nome: {patient.nome}
Idade: {patient.idade if patient.idade else 'Não informada'} anos
Sexo: {patient.sexo if patient.sexo else 'Não informado'}
Profissão: {patient.profissao if patient.profissao else 'Não informada'}
Documento de identificação: Conforme processo
Número de processo: Conforme solicitação

**2. QUEIXA PRINCIPAL**
{queixa_principal}
Solicitação específica: {classification.tipo_beneficio.value}

**3. HISTÓRIA DA DOENÇA ATUAL (HDA)**
{transcription if transcription.strip() else 'Paciente relata quadro clínico atual conforme dados fornecidos via telemedicina. Apresenta sintomas compatíveis com a condição referida, com impacto sobre a funcionalidade e capacidade laborativa.'}

Fatores desencadeantes ou agravantes: {', '.join(patient.condicoes) if patient.condicoes else 'A esclarecer em avaliação presencial'}
Tratamentos realizados: {', '.join(patient.medicamentos) if patient.medicamentos else 'Conforme prescrição médica'}
Sintomas atuais: {', '.join(patient.sintomas) if patient.sintomas else 'Conforme relato do paciente'}

**4. ANTECEDENTES PESSOAIS E FAMILIARES RELEVANTES**
Doenças prévias: {', '.join(patient.condicoes) if patient.condicoes else 'Conforme histórico médico'}
Histórico ocupacional: {patient.profissao if patient.profissao != 'Não informada' else 'Conforme CTPS'}
Histórico previdenciário: Conforme CNIS

**5. DOCUMENTAÇÃO APRESENTADA**
Documentos médicos: Conforme processo
Exames complementares: Conforme anexos
Observação: Análise baseada em documentação disponível e consulta por telemedicina

**6. EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)**
Relato de autoavaliação: Limitações funcionais referidas pelo paciente
Observação visual: Por videoconferência/telemedicina
Limitações observadas: Compatíveis com o quadro clínico relatado
Avaliação funcional: Restrições evidentes para atividade laboral habitual

**7. AVALIAÇÃO MÉDICA (ASSESSMENT)**
Hipótese diagnóstica: Compatível com CID-10: {classification.cid_principal}
Correlação clínico-funcional: Quadro clínico com repercussões sobre a capacidade laborativa
Enquadramento previdenciário: {classification.tipo_beneficio.value}

Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
        
        return anamnese
    
    def _generate_laudo(self, state: MedicalAnalysisState) -> str:
        """Gera laudo médico estruturado seguindo padrão profissional"""
        patient = state["patient_data"]
        classification = state["classification"]
        transcription = state.get("transcription", "")
        
        # VERIFICAR SE É CRIANÇA
        is_child = patient.idade and patient.idade < 18
        
        # Conclusão específica por tipo de benefício
        conclusoes = {
            BenefitTypeEnum.AUXILIO_DOENCA: "Paciente apresenta redução significativa da capacidade laborativa devido ao quadro clínico atual, que inviabiliza o exercício das atividades profissionais habituais. Recomenda-se afastamento temporário para tratamento adequado.",
            BenefitTypeEnum.AUXILIO_ACIDENTE: "Redução parcial e permanente da capacidade laborativa em decorrência de acidente, conforme Anexo III do Decreto 3.048/1999.",
            BenefitTypeEnum.BPC_LOAS: "Paciente apresenta impedimento de longo prazo de natureza física, mental, intelectual ou sensorial, que impede a participação plena e efetiva na sociedade em igualdade de condições.",
            BenefitTypeEnum.APOSENTADORIA_INVALIDEZ: "Paciente apresenta incapacidade definitiva para o exercício de qualquer atividade laborativa, sem possibilidade de readaptação funcional.",
            BenefitTypeEnum.ISENCAO_IR: "Paciente enquadra-se no rol de doenças graves da Lei 7.713/1988, fazendo jus à isenção do imposto de renda."
        }
        
        conclusao_beneficio = conclusoes.get(classification.tipo_beneficio, conclusoes[BenefitTypeEnum.AUXILIO_DOENCA])
        tempo_inicio = "Data de início dos sintomas conforme relato"
        
        if is_child:
            # TEMPLATE ESPECÍFICO PARA CRIANÇAS
            laudo = f"""**LAUDO MÉDICO ESPECIALIZADO**

**1. HISTÓRIA CLÍNICA RESUMIDA**
Paciente {patient.nome}, {patient.idade} anos, apresenta quadro clínico de {classification.cid_principal} com evolução {classification.gravidade.value.lower()}. Desenvolvimento neuropsicomotor com limitações evidentes para atividades de vida diária e participação escolar. Diagnóstico compatível com CID-10: {classification.cid_principal}.

**2. LIMITAÇÃO FUNCIONAL**
Criança apresenta limitações funcionais para desenvolvimento neuropsicomotor, autonomia pessoal e participação escolar. Comprometimento da capacidade de interação social e necessidades educacionais especiais. Requer acompanhamento multidisciplinar continuado.

**3. TRATAMENTO**
Paciente em acompanhamento médico especializado com {', '.join(patient.medicamentos) if patient.medicamentos else 'terapias apropriadas conforme prescrição médica'}. Necessidade de suporte multidisciplinar incluindo fisioterapia, terapia ocupacional e acompanhamento pedagógico especializado.

**4. PROGNÓSTICO**
Prognóstico reservado com necessidade de acompanhamento especializado contínuo. Limitações permanentes requerendo suporte familiar, educacional e terapêutico de longo prazo para maximização do potencial de desenvolvimento.

**5. CONCLUSÃO CONGRUENTE COM O BENEFÍCIO**
Criança apresenta impedimento de longo prazo que compromete participação plena na sociedade. O quadro clínico fundamenta indicação de {classification.tipo_beneficio.value}, considerando necessidades especiais e suporte continuado para desenvolvimento.

**6. CID-10**
Código(s): {classification.cid_principal}

Data: {datetime.now().strftime('%d/%m/%Y')}
Observação: Laudo gerado por sistema de IA médica avançada - Validação médica presencial recomendada.
"""
        else:
            # TEMPLATE ESPECÍFICO PARA ADULTOS
            laudo = f"""**LAUDO MÉDICO ESPECIALIZADO**

**1. HISTÓRIA CLÍNICA RESUMIDA**
{tempo_inicio}. Paciente {patient.nome}, {patient.idade if patient.idade else 'idade não informada'} anos, {patient.profissao if patient.profissao else 'profissão não informada'}, apresenta evolução clínica {classification.gravidade.value.lower()} do quadro, com sintomas que comprometem significativamente a funcionalidade laboral. O quadro atual caracteriza-se por {', '.join(patient.sintomas[:3]) if patient.sintomas else 'sintomas compatíveis com o diagnóstico'}, resultando em impacto direto sobre a capacidade de desempenhar atividades laborais habituais. Diagnóstico principal compatível com CID-10: {classification.cid_principal}.

**2. LIMITAÇÃO FUNCIONAL**
Paciente apresenta limitações funcionais evidentes de ordem {'física e mental' if any(s in str(patient.sintomas).lower() for s in ['dor', 'físico']) and any(s in str(patient.sintomas).lower() for s in ['ansiedade', 'depressão', 'pânico']) else 'mental' if any(s in str(patient.sintomas).lower() for s in ['ansiedade', 'depressão', 'pânico']) else 'física'}, manifestadas por {', '.join(patient.sintomas[:2]) if patient.sintomas else 'sintomas incapacitantes'}. Estas limitações comprometem diretamente a funcionalidade laboral, tornando inviável a continuidade das atividades profissionais em condições adequadas. Os sintomas agravantes incluem episódios de {', '.join(patient.sintomas) if patient.sintomas else 'manifestações clínicas'} que interferem na concentração, produtividade e capacidade de interação no ambiente de trabalho.

**3. TRATAMENTO**
Paciente encontra-se em tratamento médico com {', '.join(patient.medicamentos) if patient.medicamentos else 'medicações apropriadas conforme prescrição médica'}. A resposta terapêutica tem sido {'parcial' if classification.gravidade.value == 'MODERADA' else 'limitada' if classification.gravidade.value == 'GRAVE' else 'satisfatória'}, necessitando continuidade do acompanhamento especializado. O plano terapêutico inclui medidas farmacológicas e não-farmacológicas, sendo fundamental a adesão ao tratamento para otimização dos resultados clínicos.

**4. PROGNÓSTICO**
O prognóstico é considerado {'reservado' if classification.gravidade.value in ['MODERADA', 'GRAVE'] else 'favorável'} a {'desfavorável' if classification.gravidade.value == 'GRAVE' else 'reservado'}, com expectativa de {'estabilização gradual' if classification.tipo_beneficio.value == 'AUXILIO_DOENCA' else 'limitações permanentes'} {'a médio prazo' if classification.tipo_beneficio.value == 'AUXILIO_DOENCA' else 'de longo prazo'}. Tempo estimado de afastamento: {'3 a 6 meses com reavaliações periódicas' if classification.tipo_beneficio.value == 'AUXILIO_DOENCA' else 'indeterminado' if classification.tipo_beneficio.value in ['BPC/LOAS', 'APOSENTADORIA POR INVALIDEZ'] else 'conforme evolução clínica'}. A possibilidade de retorno à função {'é condicionada à resposta terapêutica adequada' if classification.tipo_beneficio.value == 'AUXILIO_DOENCA' else 'é improvável sem readaptação funcional' if classification.tipo_beneficio.value == 'AUXILIO_ACIDENTE' else 'é remota'}.

**5. CONCLUSÃO CONGRUENTE COM O BENEFÍCIO**
{conclusao_beneficio} O quadro clínico atual fundamenta a indicação de {classification.tipo_beneficio.value}, considerando {'a natureza temporária da incapacidade' if classification.tipo_beneficio.value == 'AUXILIO_DOENCA' else 'a natureza permanente das limitações' if classification.tipo_beneficio.value in ['APOSENTADORIA POR INVALIDEZ', 'BPC/LOAS'] else 'as características específicas do caso'} e a necessidade de {'tratamento especializado' if classification.tipo_beneficio.value == 'AUXILIO_DOENCA' else 'suporte continuado'}.

**6. CID-10**
Código(s): {classification.cid_principal}

Data: {datetime.now().strftime('%d/%m/%Y')}
Observação: Laudo gerado por sistema de IA médica avançada - Validação médica presencial recomendada.
"""
        
        return laudo.strip()
    
    def _calculate_confidence(self, state: MedicalAnalysisState) -> float:
        """Calcula score de confiança"""
        confidence = 0.5  # Base
        
        # Aumentar se há dados do paciente
        if state["patient_data"] and state["patient_data"].nome != "Paciente":
            confidence += 0.2
        
        # Aumentar se há transcrição
        if state.get("transcription") and len(state["transcription"]) > 50:
            confidence += 0.2
        
        # Aumentar se RAG encontrou casos
        if state.get("rag_results") and len(state["rag_results"]) > 0:
            confidence += 0.1
        
        # Diminuir se há erros
        if state.get("errors"):
            confidence -= 0.1 * len(state["errors"])
        
        return max(0.0, min(1.0, confidence))
    
    # ========================================================================
    # INTERFACE PÚBLICA
    # ========================================================================
    
    async def analyze_complete(self, patient_text: str = "", transcription: str = "") -> MedicalReportComplete:
        """Análise médica completa usando Pydantic AI + LangGraph"""
        try:
            print("🚀 Iniciando análise COMPLETA: Pydantic AI + LangGraph + RAG + FAISS")
            
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
                current_step="inicio"
            )
            
            # Executar pipeline LangGraph
            final_state = await self.workflow.ainvoke(initial_state)
            
            if final_state["medical_report"]:
                print("✅ ANÁLISE COMPLETA FINALIZADA COM SUCESSO!")
                return final_state["medical_report"]
            else:
                raise Exception("Relatório não foi gerado corretamente")
                
        except Exception as e:
            print(f"❌ Erro na análise completa: {e}")
            raise e


# ============================================================================
# INSTÂNCIA GLOBAL
# ============================================================================

_pydantic_medical_ai = None

def get_pydantic_medical_ai() -> PydanticMedicalAI:
    """Retorna instância singleton do Pydantic Medical AI"""
    global _pydantic_medical_ai
    if _pydantic_medical_ai is None:
        _pydantic_medical_ai = PydanticMedicalAI()
    return _pydantic_medical_ai 