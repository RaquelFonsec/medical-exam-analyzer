"""
API FastAPI para o Sistema de Análise Médica
"""

import os
import sys
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import asyncio
import json
from datetime import datetime

# Adicionar path do sistema médico
sys.path.append('.')

# Importações do sistema médico
try:
    from medical_system.config.system_config import (
        MedicalSystemConfiguration,
        validate_system_setup
    )
    from medical_system.utils.validators import validate_medical_analysis_result
    MEDICAL_SYSTEM_AVAILABLE = True
    print("✅ Sistema médico carregado com sucesso")
except ImportError as e:
    print(f"⚠️ Sistema médico não disponível: {e}")
    MEDICAL_SYSTEM_AVAILABLE = False

# ============================================================================
# CONFIGURAÇÃO FASTAPI
# ============================================================================

app = FastAPI(
    title="Sistema de Análise Médica",
    description="API para análise automatizada de benefícios previdenciários",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELOS PYDANTIC FLEXÍVEIS
# ============================================================================

class MedicalTranscriptionRequest(BaseModel):
    """Request para análise médica - mais flexível"""
    transcription: str = Field(..., min_length=1, description="Texto da transcrição médica")
    patient_id: Optional[str] = Field(default=None, description="ID do paciente")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Configurações personalizadas")
    
    class Config:
        # Permitir campos extras sem erro
        extra = "ignore"

class MedicalAnalysisResponse(BaseModel):
    """Response da análise médica"""
    status: str
    analysis_id: Optional[str] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

# ============================================================================
# SERVIÇO RAG MOCK
# ============================================================================

class MockRAGService:
    def __init__(self):
        self.knowledge_base = [
            "Auxílio-doença é concedido ao segurado incapacitado temporariamente.",
            "BPC/LOAS é destinado a pessoas com deficiência ou idosos vulneráveis.",
            "Aposentadoria por invalidez é para incapacidade total e permanente."
        ]
    
    def search_similar_documents(self, query: str, k: int = 3):
        docs = []
        for i, doc in enumerate(self.knowledge_base[:k]):
            score = 0.9 - (i * 0.1)
            docs.append((doc, score))
        return docs

# ============================================================================
# ROTAS DA API
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "Sistema de Análise Médica API",
        "version": "1.0.0",
        "status": "running",
        "system_available": MEDICAL_SYSTEM_AVAILABLE
    }

@app.get("/health")
async def health_check():
    if not MEDICAL_SYSTEM_AVAILABLE:
        return {
            "status": "unhealthy",
            "system_ready": False,
            "timestamp": datetime.now().isoformat(),
            "error": "Sistema médico não disponível"
        }
    
    try:
        system_ready = validate_system_setup()
        requirements = MedicalSystemConfiguration.validate_system_requirements()
        
        return {
            "status": "healthy" if system_ready else "degraded",
            "system_ready": system_ready,
            "timestamp": requirements["timestamp"],
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
            "issues": requirements.get("critical_issues", [])
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "system_ready": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# ============================================================================
# ROTA PRINCIPAL - ANÁLISE MÉDICA
# ============================================================================

async def process_medical_analysis(transcription: str, patient_id: str = None, config: dict = None):
    """Função helper para processar análise médica"""
    
    if not MEDICAL_SYSTEM_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Sistema médico não disponível"
        )
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY não configurada"
        )
    
    if not transcription or len(transcription.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="Transcrição deve ter pelo menos 5 caracteres"
        )
    
    try:
        analysis_id = f"analysis_{int(datetime.now().timestamp())}"
        
        print(f"🔬 Iniciando análise {analysis_id}")
        print(f"📄 Transcrição: {len(transcription)} caracteres")
        
        # Criar sistema médico
        rag_service = MockRAGService()
        medical_system, sys_config = MedicalSystemConfiguration.create_complete_system(
            openai_api_key=openai_api_key,
            rag_service=rag_service,
            custom_config=config or {}
        )
        
        # Processar análise
        result = await medical_system.process_medical_transcription(transcription)
        
        # Validar resultado
        validation = validate_medical_analysis_result(result)
        result["validation"] = validation
        result["analysis_id"] = analysis_id
        
        beneficio = result.get('beneficio_classificado', 'N/A')
        print(f"✅ Análise {analysis_id} concluída: {beneficio}")
        
        return {
            "status": "success",
            "analysis_id": analysis_id,
            "result": result
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Erro na análise: {error_msg}")
        
        return {
            "status": "error",
            "analysis_id": f"error_{int(datetime.now().timestamp())}",
            "error": error_msg,
            "result": {}
        }

@app.post("/analyze")
async def analyze_medical_transcription(request: MedicalTranscriptionRequest):
    """Rota padrão para análise médica"""
    return await process_medical_analysis(
        transcription=request.transcription,
        patient_id=request.patient_id,
        config=request.config
    )

@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis(request: Request):
    """
    Rota específica para análise médica inteligente
    Aceita dados de qualquer formato JSON
    """
    
    try:
        # Log da requisição
        print(f"📋 Recebida requisição em /api/intelligent-medical-analysis")
        
        # Ler body da requisição
        body = await request.body()
        print(f"📄 Body recebido: {body[:200]}...")
        
        # Parse do JSON
        try:
            json_data = json.loads(body)
            print(f"📊 JSON data keys: {list(json_data.keys())}")
        except json.JSONDecodeError as e:
            print(f"❌ Erro no parse JSON: {e}")
            raise HTTPException(status_code=400, detail="JSON inválido")
        
        # Extrair dados necessários (flexível)
        transcription = (
            json_data.get('transcription') or 
            json_data.get('text') or 
            json_data.get('content') or
            json_data.get('transcript') or
            ""
        )
        
        patient_id = (
            json_data.get('patient_id') or 
            json_data.get('patientId') or 
            json_data.get('id') or
            None
        )
        
        config = json_data.get('config', {})
        
        print(f"📝 Transcrição extraída: {len(transcription)} caracteres")
        print(f"👤 Patient ID: {patient_id}")
        
        # Validar se tem transcrição
        if not transcription:
            available_fields = list(json_data.keys())
            raise HTTPException(
                status_code=400, 
                detail=f"Campo 'transcription' não encontrado. Campos disponíveis: {available_fields}"
            )
        
        # Processar análise
        return await process_medical_analysis(transcription, patient_id, config)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test")
async def test_analysis():
    """Teste rápido do sistema"""
    
    mock_transcription = """
    Paciente João Silva, 45 anos, carpinteiro há 20 anos.
    Refere dor lombar intensa há 6 meses, com irradiação para perna direita.
    Não consegue mais carregar peso ou trabalhar em pé.
    Radiografia mostra artrose L4-L5.
    Solicita auxílio-doença para afastamento.
    """
    
    return await process_medical_analysis(
        transcription=mock_transcription,
        patient_id="test_001",
        config={"pipeline_timeout_seconds": 180}
    )

# ============================================================================
# TRATAMENTO DE ERROS
# ============================================================================

@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    """Handler específico para erro 422"""
    print(f"❌ Erro 422 em {request.url.path}")
    print(f"📄 Body: {await request.body()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Dados de entrada inválidos",
            "detail": "Verifique se o campo 'transcription' está presente",
            "expected_format": {
                "transcription": "string (obrigatório)",
                "patient_id": "string (opcional)",
                "config": "object (opcional)"
            },
            "path": str(request.url.path)
        }
    )

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint não encontrado",
            "path": str(request.url.path),
            "available_endpoints": ["/", "/health", "/analyze", "/api/intelligent-medical-analysis", "/test"]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erro interno do servidor",
            "path": str(request.url.path)
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
