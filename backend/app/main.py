# ============================================================================
# MAIN.PY - SISTEMA MÉDICO COM PIPELINE E RAG
# ============================================================================

import os
import sys
import traceback
import tempfile
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

# Configurar path para imports
sys.path.append('.')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# Verificar variáveis essenciais
required_env_vars = ['OPENAI_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Variáveis de ambiente faltando: {missing_vars}")
    sys.exit(1)

app = FastAPI(
    title="Medical AI System", 
    version="3.1",
    description="Sistema de análise médica com pipeline e RAG"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serviço médico principal
pydantic_ai_service = None

try:
    # SISTEMA PRINCIPAL: PYDANTIC AI (LangGraph + RAG + FAISS + Pydantic)
    from app.services.pydantic_ai_medical_service import get_pydantic_medical_ai
    pydantic_ai_service = get_pydantic_medical_ai()
    
    if pydantic_ai_service is None:
        print("❌ ERRO CRÍTICO: PydanticMedicalAI retornou None")
        pydantic_ai_service = None
    else:
        print("✅ PydanticMedicalAI carregado (LangGraph + RAG + FAISS + Pydantic)")
        
except Exception as e:
    print(f"❌ ERRO CRÍTICO: PydanticMedicalAI não disponível: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    pydantic_ai_service = None


def is_audio_file(content_type: str, filename: str) -> bool:
    """Verifica se o arquivo é de áudio"""
    if not filename:
        return False
        
    audio_types = ['audio/', 'video/', 'application/octet-stream']
    audio_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.webm', '.mp4', '.mpeg', '.aac']
    
    if content_type:
        for audio_type in audio_types:
            if content_type.startswith(audio_type):
                return True
    
    if filename:
        for ext in audio_extensions:
            if filename.lower().endswith(ext):
                return True
    
    return False


def is_image_file(content_type: str, filename: str) -> bool:
    """Verifica se o arquivo é uma imagem"""
    if not filename:
        return False
        
    image_types = ['image/']
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    if content_type:
        for image_type in image_types:
            if content_type.startswith(image_type):
                return True
    
    if filename:
        for ext in image_extensions:
            if filename.lower().endswith(ext):
                return True
    
    return False


# Funções antigas removidas - agora usamos PydanticAI que gera anamnese e laudo automaticamente


# ============================================================================
# ROTAS DA API
# ============================================================================

@app.get("/")
async def root():
    """Página inicial"""
    return {"message": "Sistema Médico AI - Backend ativo", "version": "3.1"}


@app.get("/health")
async def health_check():
    """Health check da API"""
    return {
        "status": "healthy" if pydantic_ai_service else "error",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "pydantic_ai": pydantic_ai_service is not None
        },
        "active_system": "PydanticAI (LangGraph + RAG + FAISS + Pydantic)" if pydantic_ai_service else "Sistema indisponível"
    }


@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis(
    patient_info: str = Form(""),
    audio: UploadFile = File(None),
    image: UploadFile = File(None)
):
    """Análise médica inteligente com PydanticAI + LangGraph + RAG + FAISS"""
    try:
        if not pydantic_ai_service:
            raise HTTPException(status_code=500, detail="Sistema PydanticAI não disponível")

        print(f"🧠 Análise médica: {patient_info[:50]}...")
        print("🚀 Sistema: PydanticAI + LangGraph + RAG + FAISS + Pydantic")
        
        # Processar áudio se enviado
        transcription = ""
        if audio and audio.filename:
            print(f"🎤 Processando áudio: {audio.filename}")
            try:
                from app.services.transcription_service import TranscriptionService
                transcription_service = TranscriptionService()
                audio_bytes = await audio.read()
                transcription = await transcription_service.transcribe_audio(audio_bytes)
                print(f"✅ Transcrição: {transcription[:100]}...")
            except Exception as e:
                print(f"⚠️ Erro na transcrição (continuando sem áudio): {e}")
                transcription = ""
        
        # Executar análise COMPLETA com PydanticAI
        pydantic_result = await pydantic_ai_service.analyze_complete(
            patient_text=patient_info,
            transcription=transcription
        )
        
        print("✅ ANÁLISE COMPLETA FINALIZADA!")
        
        # Preparar resposta estruturada
        response_data = {
            "success": True,
            "transcription": transcription,
            "anamnese": pydantic_result.anamnese,
            "laudo_medico": pydantic_result.laudo_medico,
            "classification": {
                "tipo_beneficio": pydantic_result.classification.tipo_beneficio.value,
                "cid_principal": pydantic_result.classification.cid_principal,
                "cids_secundarios": pydantic_result.classification.cids_secundarios,
                "gravidade": pydantic_result.classification.gravidade.value,
                "prognostico": pydantic_result.classification.prognostico,
                "elegibilidade": pydantic_result.classification.elegibilidade,
                "justificativa": pydantic_result.classification.justificativa,
                "especificidade_cid": pydantic_result.classification.especificidade_cid
            },
            "patient_data": {
                "nome": pydantic_result.patient_data.nome,
                "idade": pydantic_result.patient_data.idade,
                "sexo": pydantic_result.patient_data.sexo,
                "profissao": pydantic_result.patient_data.profissao,
                "sintomas": pydantic_result.patient_data.sintomas,
                "medicamentos": pydantic_result.patient_data.medicamentos,
                "condicoes": pydantic_result.patient_data.condicoes
            },
            "rag_results": pydantic_result.rag_context,
            "confidence_score": pydantic_result.confidence_score,
            "analysis_method": "PydanticAI + LangGraph + RAG + FAISS + Pydantic",
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"❌ Erro na análise: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "transcription": "Erro na análise",
                "anamnese": "Erro ao gerar anamnese",
                "laudo_medico": "Erro ao gerar laudo",
                "timestamp": datetime.now().isoformat()
            }
        )


@app.post("/api/analyze-document")
async def analyze_document_with_pydantic_ai(
    document: UploadFile = File(...),
    patient_info: str = Form("")
):
    """Analisa documento médico usando PydanticAI + OCR"""
    try:
        if not pydantic_ai_service:
            raise HTTPException(status_code=500, detail="Sistema PydanticAI não disponível")

        print(f"📄 Analisando documento: {document.filename}")
        
        # Salvar arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(document.filename)[1]) as tmp:
            tmp.write(await document.read())
            temp_path = tmp.name
        
        try:
            # Extrair texto do documento usando OCR simples
            document_text = ""
            try:
                from app.services.ocr_service import OCRService
                ocr_service = OCRService()
                document_text = ocr_service.extract_text_from_file(temp_path)
                print(f"✅ Texto extraído do documento: {len(document_text)} caracteres")
            except Exception as e:
                print(f"⚠️ Erro na extração de texto: {e}")
                document_text = "Documento anexado - texto não extraído"
            
            # Combinar texto do documento com informações do paciente
            combined_text = f"{patient_info}\n\nDocumento anexado:\n{document_text}"
            
            # Executar análise completa com PydanticAI
            pydantic_result = await pydantic_ai_service.analyze_complete(
                patient_text=combined_text,
                transcription=""
            )
            
            response_data = {
                "success": True,
                "document_text": document_text,
                "anamnese": pydantic_result.anamnese,
                "laudo_medico": pydantic_result.laudo_medico,
                "classification": {
                    "tipo_beneficio": pydantic_result.classification.tipo_beneficio.value,
                    "cid_principal": pydantic_result.classification.cid_principal,
                    "gravidade": pydantic_result.classification.gravidade.value,
                    "prognostico": pydantic_result.classification.prognostico,
                    "elegibilidade": pydantic_result.classification.elegibilidade,
                    "justificativa": pydantic_result.classification.justificativa
                },
                "patient_data": {
                    "nome": pydantic_result.patient_data.nome,
                    "idade": pydantic_result.patient_data.idade,
                    "sexo": pydantic_result.patient_data.sexo,
                    "profissao": pydantic_result.patient_data.profissao,
                    "sintomas": pydantic_result.patient_data.sintomas,
                    "medicamentos": pydantic_result.patient_data.medicamentos,
                    "condicoes": pydantic_result.patient_data.condicoes
                },
                "rag_results": pydantic_result.rag_context,
                "confidence_score": pydantic_result.confidence_score,
                "analysis_method": "PydanticAI + OCR + LangGraph + RAG + FAISS",
                "timestamp": datetime.now().isoformat()
            }
            
            return JSONResponse(content=response_data)
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except Exception as e:
        print(f"❌ Erro na análise de documento: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
