"""
Modelos Pydantic para dados do paciente e análise médica
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class BenefitType(str, Enum):
    """Tipos de benefícios previdenciários"""
    AUXILIO_DOENCA = "AUXÍLIO-DOENÇA"
    APOSENTADORIA_INVALIDEZ = "APOSENTADORIA POR INVALIDEZ"
    BPC_LOAS = "BPC/LOAS"
    AUXILIO_ACIDENTE = "AUXÍLIO-ACIDENTE"
    ISENCAO_IR = "ISENÇÃO IMPOSTO DE RENDA"


class Specialty(str, Enum):
    """Especialidades médicas"""
    CARDIOLOGIA = "CARDIOLOGIA"
    NEUROLOGIA = "NEUROLOGIA"
    ORTOPEDIA = "ORTOPEDIA"
    PSIQUIATRIA = "PSIQUIATRIA"
    CLINICA_GERAL = "CLÍNICA GERAL"
    ENDOCRINOLOGIA = "ENDOCRINOLOGIA"


class FunctionalLimitation(str, Enum):
    """Limitações funcionais"""
    LEVE = "LEVE"
    MODERADA = "MODERADA"
    GRAVE = "GRAVE"
    TOTAL = "TOTAL"


class Severity(str, Enum):
    """Severidade da condição"""
    LEVE = "LEVE"
    MODERADA = "MODERADA"
    GRAVE = "GRAVE"


class DocumentType(str, Enum):
    """Tipos de documentos"""
    EXAME = "EXAME"
    RELATORIO = "RELATÓRIO"
    LAUDO = "LAUDO"
    PRONTUARIO = "PRONTUÁRIO"


class AnalysisConfidence(str, Enum):
    """Nível de confiança da análise"""
    ALTA = "ALTA"
    MEDIA = "MÉDIA"
    BAIXA = "BAIXA"


class ClassificationMethod(str, Enum):
    """Método de classificação usado"""
    LLM = "LLM"
    RAG = "RAG"
    HIBRIDO = "HÍBRIDO"


class PatientData(BaseModel):
    """Dados básicos do paciente"""
    nome: str = Field(description="Nome completo do paciente")
    idade: Optional[int] = Field(None, description="Idade do paciente")
    sexo: Optional[str] = Field(None, description="Sexo do paciente")
    profissao: Optional[str] = Field(None, description="Profissão do paciente")
    documento: Optional[str] = Field(None, description="Documento de identificação")


class MedicalHistory(BaseModel):
    """Histórico médico do paciente"""
    condicoes_cronicas: List[str] = Field(default_factory=list, description="Condições crônicas")
    medicamentos: List[str] = Field(default_factory=list, description="Medicamentos em uso")
    cirurgias_previas: List[str] = Field(default_factory=list, description="Cirurgias prévias")
    hospitalizacoes: List[str] = Field(default_factory=list, description="Hospitalizações")


class Diagnosis(BaseModel):
    """Diagnóstico médico"""
    cid_principal: str = Field(description="CID principal")
    cid_secundarios: List[str] = Field(default_factory=list, description="CIDs secundários")
    descricao: str = Field(description="Descrição do diagnóstico")
    especialidade: Specialty = Field(description="Especialidade responsável")


class FunctionalAssessment(BaseModel):
    """Avaliação funcional do paciente"""
    limitacoes: List[FunctionalLimitation] = Field(default_factory=list, description="Limitações funcionais")
    capacidade_trabalho: Optional[str] = Field(None, description="Capacidade para o trabalho")
    atividades_vida_diaria: Optional[str] = Field(None, description="Limitações nas AVDs")
    mobilidade: Optional[str] = Field(None, description="Avaliação da mobilidade")


class BenefitAnalysis(BaseModel):
    """Análise de benefício previdenciário"""
    tipo_beneficio: BenefitType = Field(description="Tipo de benefício recomendado")
    elegibilidade: bool = Field(description="Se é elegível para o benefício")
    justificativa: str = Field(description="Justificativa da recomendação")
    cid_relacionado: str = Field(description="CID relacionado ao benefício")


# Novos modelos para LangGraph
class PatientIdentification(BaseModel):
    """Identificação do paciente"""
    nome: str = Field(description="Nome completo")
    idade: Optional[int] = Field(None, description="Idade")
    sexo: Optional[str] = Field(None, description="Sexo")
    profissao: Optional[str] = Field(None, description="Profissão")
    documento: Optional[str] = Field(None, description="RG/CPF")
    processo: Optional[str] = Field(None, description="Número do processo")


class ChiefComplaint(BaseModel):
    """Queixa principal"""
    motivo_consulta: str = Field(description="Motivo da consulta")
    solicitacao_advogado: Optional[str] = Field(None, description="Solicitação específica")


class CurrentIllnessHistory(BaseModel):
    """História da doença atual"""
    inicio_sintomas: Optional[str] = Field(None, description="Data de início")
    fatores_desencadeantes: List[str] = Field(default_factory=list)
    tratamentos_realizados: List[str] = Field(default_factory=list)
    situacao_atual: str = Field(description="Situação atual")


class PastHistory(BaseModel):
    """Antecedentes"""
    doencas_previas: List[str] = Field(default_factory=list)
    historico_ocupacional: Optional[str] = Field(None)


class MedicalDocumentation(BaseModel):
    """Documentação médica"""
    exames_complementares: List[str] = Field(default_factory=list)
    relatorios: List[str] = Field(default_factory=list)
    observacoes: Optional[str] = Field(None)


class TelemedicineExam(BaseModel):
    """Exame clínico por telemedicina"""
    autoavaliacao: Optional[str] = Field(None)
    observacao_visual: Optional[str] = Field(None)
    limitacoes_funcionais: List[str] = Field(default_factory=list)


class MedicalAssessment(BaseModel):
    """Avaliação médica"""
    hipotese_diagnostica: str = Field(description="Hipótese diagnóstica")
    cid_10: str = Field(description="CID-10")
    prognostico: str = Field(description="Prognóstico")


class CompleteMedicalRecord(BaseModel):
    """Registro médico completo"""
    identificacao: PatientIdentification
    queixa_principal: ChiefComplaint
    historia_atual: CurrentIllnessHistory
    antecedentes: PastHistory
    documentacao: MedicalDocumentation
    exame_clinico: TelemedicineExam
    avaliacao: MedicalAssessment
    data_registro: datetime = Field(default_factory=datetime.now)


class DocumentAnalysis(BaseModel):
    """Análise de documento"""
    tipo: DocumentType
    conteudo_extraido: str
    confianca: AnalysisConfidence
    metodo: ClassificationMethod


class MultimodalAnalysisResult(BaseModel):
    """Resultado da análise multimodal"""
    transcricao: Optional[str] = Field(None)
    analise_imagem: Optional[str] = Field(None)
    analise_documento: Optional[DocumentAnalysis] = Field(None)
    dados_paciente: PatientData
    diagnostico: Diagnosis
    avaliacao_funcional: FunctionalAssessment
    analise_beneficio: BenefitAnalysis
    confianca_geral: AnalysisConfidence


class CompleteMedicalAnalysis(BaseModel):
    """Análise médica completa"""
    dados_paciente: PatientData
    historico_medico: MedicalHistory
    diagnostico: Diagnosis
    avaliacao_funcional: FunctionalAssessment
    analise_beneficio: BenefitAnalysis
    resultado_multimodal: Optional[MultimodalAnalysisResult] = Field(None)
    registro_completo: Optional[CompleteMedicalRecord] = Field(None)
    timestamp: datetime = Field(default_factory=datetime.now) 