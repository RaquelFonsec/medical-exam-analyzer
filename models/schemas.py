# models/schemas.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class AudioInfo(BaseModel):
    """Informações sobre o áudio processado"""
    duration_seconds: float
    channels: int
    sample_rate: int
    size_bytes: int
    filename: str

class MedicalConversation(BaseModel):
    """Conversa médica separada por falantes"""
    doctor_text: str = ""
    patient_text: str = ""
    detailed_conversation: str = ""
    total_speakers: int = 0
    method_used: str = ""

class ProcessingDetails(BaseModel):
    """Detalhes do processamento de áudio"""
    mixing_success: Optional[bool] = None
    original_doctor_duration: Optional[float] = None
    original_patient_duration: Optional[float] = None
    final_mixed_duration: Optional[float] = None
    audio_quality: Optional[Dict[str, Any]] = None
    volume_adjustments: Optional[str] = None

class AudioProcessingResponse(BaseModel):
    """Resposta do processamento de áudio"""
    success: bool
    processing_method: str
    transcription: str
    medical_conversation: MedicalConversation
    audio_processing_details: Optional[ProcessingDetails] = None
    file_info: Dict[str, Any]
    processing_time_seconds: float
    timestamp: str
    warnings: List[str] = []
    error: Optional[str] = None

class LLMAnalysis(BaseModel):
    """Análise LLM de exames"""
    clinical_analysis: str
    exam_type: str
    key_findings: List[str]
    overall_status: str

class ExamAnalysisResponse(BaseModel):
    """Resposta da análise de exames"""
    success: bool
    llm_analysis: Optional[LLMAnalysis] = None
    extracted_text: Optional[str] = None
    filename: str
    model_used: Optional[str] = None
    interpretation_complete: Optional[bool] = None
    processing_timestamp: str
    error: Optional[str] = None

class AudioMixingResult(BaseModel):
    """Resultado da mixagem de áudio"""
    success: bool
    mixed_audio_path: Optional[str] = None
    stereo_separated_path: Optional[str] = None
    audio_info: Optional[Dict[str, Any]] = None
    processing_notes: Optional[Dict[str, str]] = None
    error: Optional[str] = None

class TranscriptionResult(BaseModel):
    """Resultado da transcrição"""
    sucesso: bool
    transcricao: str = ""
    medico: str = ""
    paciente: str = ""
    conversa_detalhada: str = ""
    metodo: str = ""
    total_falantes: int = 0
    tamanho: int = 0
    confianca: str = ""
    erro: Optional[str] = None
    warning: Optional[str] = None