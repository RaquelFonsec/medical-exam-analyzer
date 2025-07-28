"""
Modelos de Estado para o LangGraph
"""

from typing import Dict, List, Optional, Any, TypedDict
from .pydantic_models import CompleteMedicalRecord

class MedicalAnalysisState(TypedDict):
    """Estado compartilhado do pipeline de análise"""
    original_text: str
    extracted_data: Optional[Dict[str, Any]]
    medical_record: Optional[CompleteMedicalRecord]
    benefit_classification: Optional[Dict[str, Any]]
    specialist_analysis: Optional[Dict[str, Any]]
    final_report: Optional[str]
    errors: List[str]
    current_step: str
