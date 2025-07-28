"""
Modelos Pydantic para o Sistema de Análise Médica
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class BenefitType(Enum):
    AUXILIO_DOENCA = "AUXÍLIO-DOENÇA"
    APOSENTADORIA_INVALIDEZ = "APOSENTADORIA POR INVALIDEZ"
    AUXILIO_ACIDENTE = "AUXÍLIO-ACIDENTE"
    BPC_LOAS = "BPC/LOAS"
    ISENCAO_IR = "ISENÇÃO IMPOSTO DE RENDA"
    MAJORACAO_25 = "MAJORAÇÃO 25%"

class Specialty(Enum):
    PSIQUIATRIA = "psiquiatria"
    CARDIOLOGIA = "cardiologia"
    NEUROLOGIA = "neurologia"
    OFTALMOLOGIA = "oftalmologia" 
    ORTOPEDIA = "ortopedia"
    CLINICA_GERAL = "clinica_geral"
    MEDICINA_TRABALHO = "medicina_trabalho"

class FunctionalLimitation(Enum):
    MOTORA = "motora"
    SENSORIAL = "sensorial"
    COGNITIVA = "cognitiva"
    INTELECTUAL = "intelectual"
    PSIQUICA = "psiquica"

class PatientIdentification(BaseModel):
    """Identificação do paciente"""
    nome: str = "não informado"
    idade: Optional[int] = None
    sexo: str = "não informado"
    profissao: str = "não informada"
    documento_rg: Optional[str] = None
    documento_cpf: Optional[str] = None
    numero_processo: Optional[str] = None

class ChiefComplaint(BaseModel):
    """Queixa principal estruturada"""
    motivo_consulta: str = "não informado"
    solicitacao_beneficio: Optional[BenefitType] = None
    solicitacao_advogado: str = "não informada"

class CurrentIllnessHistory(BaseModel):
    """História da doença atual"""
    data_inicio_sintomas: Optional[str] = None
    data_diagnostico: Optional[str] = None
    fatores_desencadeantes: List[str] = Field(default_factory=list)
    tratamentos_realizados: List[str] = Field(default_factory=list)
    medicacoes_atuais: List[str] = Field(default_factory=list)
    limitacoes_atuais: List[str] = Field(default_factory=list)
    sintomas_persistentes: List[str] = Field(default_factory=list)

class PastHistory(BaseModel):
    """Antecedentes pessoais e familiares"""
    doencas_previas: List[str] = Field(default_factory=list)
    historico_ocupacional: str = "não informado"
    anos_contribuicao: Optional[int] = None
    acidentes_trabalho: List[str] = Field(default_factory=list)
    historico_familiar: List[str] = Field(default_factory=list)

class MedicalDocumentation(BaseModel):
    """Documentação médica"""
    exames_complementares: List[str] = Field(default_factory=list)
    relatorios_medicos: List[str] = Field(default_factory=list)
    cids_mencionados: List[str] = Field(default_factory=list)
    documentos_suficientes: bool = False
    observacoes_documentacao: str = ""

class TelemedicineExam(BaseModel):
    """Exame clínico adaptado para telemedicina"""
    autoavaliacao_forca: str = "não avaliada"
    autoavaliacao_mobilidade: str = "não avaliada"
    nivel_dor: str = "não informado"
    observacoes_video: str = "não realizada"
    limitacoes_funcionais: List[FunctionalLimitation] = Field(default_factory=list)

class MedicalAssessment(BaseModel):
    """Avaliação médica"""
    cid_principal: str = ""
    cid_descricao: str = ""
    cids_secundarios: List[str] = Field(default_factory=list)
    especialidade_principal: Specialty = Specialty.CLINICA_GERAL
    especialidades_complementares: List[Specialty] = Field(default_factory=list)
    gravidade_quadro: str = "moderada"
    prognostico: str = "reservado"

class CompleteMedicalRecord(BaseModel):
    """Prontuário médico completo"""
    identificacao: PatientIdentification
    queixa_principal: ChiefComplaint
    historia_doenca_atual: CurrentIllnessHistory
    antecedentes: PastHistory
    documentacao: MedicalDocumentation
    exame_telemedico: TelemedicineExam
    avaliacao_medica: MedicalAssessment
    
    # Campos de análise automática
    nexo_ocupacional: bool = False
    capacidade_laborativa: str = "prejudicada"
    necessita_auxilio_terceiros: bool = False
