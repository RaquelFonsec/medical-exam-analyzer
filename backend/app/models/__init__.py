"""
Modelos Pydantic da aplicação médica
"""

from .patient import (
    PatientData,
    MedicalHistory,
    Diagnosis,
    FunctionalAssessment,
    BenefitAnalysis,
    CompleteMedicalAnalysis,
    BenefitType,
    Specialty,
    FunctionalLimitation,
    Severity,
    # Modelos LangGraph
    PatientIdentification,
    ChiefComplaint,
    CurrentIllnessHistory,
    PastHistory,
    MedicalDocumentation,
    TelemedicineExam,
    MedicalAssessment,
    CompleteMedicalRecord,
    # Modelos Multimodal
    DocumentType,
    AnalysisConfidence,
    ClassificationMethod,
    DocumentAnalysis,
    MultimodalAnalysisResult
)

# Alias para compatibilidade com código existente
BenefitClassification = BenefitAnalysis

__all__ = [
    'PatientData',
    'MedicalHistory', 
    'Diagnosis',
    'FunctionalAssessment',
    'BenefitAnalysis',
    'CompleteMedicalAnalysis',
    'BenefitType',
    'Specialty',
    'FunctionalLimitation',
    'Severity',
    # LangGraph models
    'PatientIdentification',
    'ChiefComplaint',
    'CurrentIllnessHistory',
    'PastHistory',
    'MedicalDocumentation',
    'TelemedicineExam',
    'MedicalAssessment',
    'CompleteMedicalRecord',
    # Multimodal models
    'DocumentType',
    'AnalysisConfidence',
    'ClassificationMethod',
    'DocumentAnalysis',
    'MultimodalAnalysisResult',
    # Compatibility
    'BenefitClassification'
]
