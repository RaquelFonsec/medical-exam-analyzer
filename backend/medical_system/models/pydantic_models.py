# ============================================================================
# MODELOS PYDANTIC PARA SISTEMA RAG MÉDICO
# models.py
# ============================================================================

from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field, validator
import re

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

class PatientDataEnhanced(BaseModel):
    """Dados do paciente com validação estrita e correção automática"""
    nome: str = Field(min_length=1, description="Nome completo do paciente")
    idade: Optional[int] = Field(None, ge=0, le=120, description="Idade do paciente")
    sexo: Optional[str] = Field(None, pattern="^[MF]$", description="Sexo M ou F")
    profissao: Optional[str] = Field(None, description="Profissão do paciente")
    sintomas: List[str] = Field(default_factory=list, description="Lista de sintomas")
    medicamentos: List[str] = Field(default_factory=list, description="Lista de medicamentos")
    condicoes: List[str] = Field(default_factory=list, description="Lista de condições médicas")
    
    # Campos enriquecidos pelo RAG
    rag_similarity_score: Optional[float] = Field(None, description="Score de similaridade RAG")
    similar_cases_found: Optional[int] = Field(None, description="Número de casos similares encontrados")

    @validator('medicamentos', pre=True)
    def normalize_medications(cls, v):
        """Normaliza medicamentos corrigindo erros comuns de transcrição"""
        if not v:
            return []
        
        corrections = {
            'metamorfina': 'metformina',
            'captou o piu': 'captopril',
            'captou miúdo': 'captopril', 
            'captomai': 'captopril',
            'pium': '',  # Remove
            'zartan': 'losartana',
            'artões': 'atorvastatina',
            'lodosartana': 'losartana',
            'captou o rio': 'captopril',
            'captou pil': 'captopril',
            'metaformina': 'metformina',
            'diabinese': 'glibenclamida',
            'diabex': 'metformina'
        }
        
        corrected = []
        for med in v:
            if isinstance(med, str):
                med_lower = med.lower().strip()
                corrected_med = med_lower
                
                # Aplicar correções
                for wrong, right in corrections.items():
                    if wrong in med_lower:
                        if right:  # Se não é para remover
                            corrected_med = right
                        else:
                            corrected_med = None
                        break
                
                if corrected_med:
                    corrected.append(corrected_med)
        
        return list(set(filter(None, corrected)))  # Remove duplicatas e vazios

class BenefitClassificationEnhanced(BaseModel):
    """Classificação enriquecida com dados do RAG"""
    tipo_beneficio: BenefitTypeEnum = Field(description="Tipo de benefício recomendado")
    cid_principal: str = Field(pattern="^[A-Z]\d{2}(\.\d)?$", description="CID-10 no formato A00.0")
    cids_secundarios: Optional[List[str]] = Field(default_factory=list, description="CIDs secundários")
    gravidade: SeverityEnum = Field(description="Gravidade da condição")
    prognostico: str = Field(min_length=20, description="Prognóstico detalhado")
    elegibilidade: bool = Field(description="Se é elegível para o benefício")
    justificativa: str = Field(min_length=50, description="Justificativa médica detalhada")
    especificidade_cid: str = Field(description="Explicação da escolha do CID específico")
    
    # Campos enriquecidos pelo RAG
    rag_confidence: Optional[float] = Field(None, description="Confiança baseada no RAG")
    similar_cases_cids: Optional[List[str]] = Field(default_factory=list, description="CIDs de casos similares")
    rag_source_method: Optional[str] = Field(None, description="Método de busca RAG usado")
    severity_score: Optional[int] = Field(None, ge=0, le=10, description="Score numérico de severidade")
    estimated_leave_days: Optional[int] = Field(None, description="Dias estimados de afastamento")
    
    # Controles de qualidade
    telemedicina_limitacao: Optional[str] = Field(None, description="Limitações da telemedicina")
    fonte_cids: str = Field(default="RAG + Análise Clínica", description="Fonte dos CIDs")

    @validator('cid_principal')
    def validate_cid(cls, v):
        if not v or v.lower() in ['não informado', 'nao informado', '']:
            return 'I10'  # Hipertensão como fallback seguro
        return v.upper()

class HybridMedicalReport(BaseModel):
    """Relatório médico híbrido com dados RAG + Pydantic"""
    patient_data: PatientDataEnhanced
    classification: BenefitClassificationEnhanced
    anamnese: str = Field(min_length=100, description="Anamnese estruturada")
    laudo_medico: str = Field(min_length=200, description="Laudo médico detalhado")
    
    # Dados específicos do RAG
    rag_cases_analyzed: List[Dict[str, Any]] = Field(default_factory=list, description="Casos RAG analisados")
    rag_search_queries: List[str] = Field(default_factory=list, description="Queries RAG utilizadas")
    universal_analysis: Optional[Dict[str, Any]] = Field(None, description="Análise universal completa")
    
    # Métricas de qualidade
    overall_confidence: float = Field(ge=0.0, le=1.0, description="Confiança geral do sistema")
    processing_time_seconds: Optional[float] = Field(None, description="Tempo de processamento")
    system_version: str = Field(default="RAG-Hybrid-v1.0", description="Versão do sistema")