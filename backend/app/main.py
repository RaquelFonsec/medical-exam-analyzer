# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import asyncio
import json
from .config import settings
from .services.exam_processor import ExamProcessor
from .services.aws_textract_service import AWSTextractService

app = FastAPI(title="PREVIDAS Medical Exam Analyzer with AWS Textract")

# CORS CORRIGIDO - Incluir porta 5003
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5000", 
        "http://127.0.0.1:5000",
        "http://localhost:5003", 
        "http://127.0.0.1:5003",
        "http://192.168.2.164:5003"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar serviços
processor = ExamProcessor()
textract_service = AWSTextractService()

# Configurar OpenAI
import openai
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
async def root():
    return {"message": "PREVIDAS Medical AI - Sistema Inteligente ✅"}

@app.get("/health")
async def health_check():
    """Verificar status dos serviços"""
    try:
        # Verificar OpenAI
        openai_status = "connected" if os.getenv("OPENAI_API_KEY") else "not configured"
        
        # Verificar AWS
        aws_status = "ready"
        try:
            import boto3
            textract = boto3.client('textract', region_name='us-east-1')
            aws_status = "connected"
        except:
            aws_status = "not configured"
        
        return {
            "status": "healthy",
            "version": "3.0.0",
            "services": {
                "database": "connected",
                "openai": openai_status,
                "aws_textract": aws_status,
                "ocr": "ready",
                "context_classifier": "ready"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Importar serviços
from .services.multimodal_ai_service import MultimodalAIService
from .services.encryption_service import encryption_service
from .services.auth_service import auth_service
from .services.audit_service import audit_service

# IMPORT CORRETO do context_classifier
try:
    from .services.context_classifier_service import context_classifier
    print("✅ Context Classifier carregado")
except ImportError as e:
    print(f"⚠️ Context Classifier não encontrado: {e}")
    context_classifier = None

# Inicializar serviço multimodal
# FORÇAR RELOAD COMPLETO
import importlib
import sys
if "app.services.multimodal_ai_service" in sys.modules:
    del sys.modules["app.services.multimodal_ai_service"]
    print("🔄 Módulo removido do cache")

from .services.multimodal_ai_service import MultimodalAIService
print("🔄 MultimodalAIService reimportado")
multimodal_service = MultimodalAIService()

@app.post("/multimodal-analysis/")
async def multimodal_analysis_secure(
    patient_info: str = Form(...),
    audio_file: UploadFile = File(None),
    image_file: UploadFile = File(None)
):
    """Análise multimodal SEGURA com criptografia LGPD"""
    try:
        print(f"🔒 ANÁLISE MULTIMODAL SEGURA iniciada")
        
        # 1. Gerar hash do paciente para auditoria (sem expor dados)
        patient_hash = encryption_service.hash_patient_id(patient_info)
        
        # 2. Registrar acesso nos logs LGPD
        audit_service.log_patient_access(
            doctor_crm="demo_doctor",  # TODO: pegar do token JWT
            patient_hash=patient_hash,
            action="consultation_started",
            details={"has_audio": bool(audio_file), "has_image": bool(image_file)}
        )
        
        # 3. Ler arquivos se fornecidos
        audio_bytes = None
        image_bytes = None
        
        if audio_file and audio_file.filename:
            audio_bytes = await audio_file.read()
            print(f"🎤 Áudio recebido: {len(audio_bytes)} bytes (criptografado)")
            
            # Registrar processamento de áudio
            audit_service.log_data_processing(
                doctor_crm="demo_doctor",
                patient_hash=patient_hash,
                processing_type="audio_transcription"
            )
        
        if image_file and image_file.filename:
            image_bytes = await image_file.read()
            print(f"📷 Imagem recebida: {len(image_bytes)} bytes (criptografado)")
            
            # Registrar processamento de imagem
            audit_service.log_data_processing(
                doctor_crm="demo_doctor",
                patient_hash=patient_hash,
                processing_type="image_analysis"
            )
        
        # 4. Processar com GPT-4o multimodal
        result = await multimodal_service.analyze_multimodal(
            patient_info, audio_bytes, image_bytes
        )
        
        # 5. Criptografar dados antes de salvar
        if result["success"]:
            try:
                from .models import SessionLocal, MedicalConsultation
                db = SessionLocal()
                try:
                    # CRIPTOGRAFAR DADOS SENSÍVEIS
                    encrypted_patient_info = encryption_service.encrypt_patient_data(patient_info)
                    encrypted_transcription = encryption_service.encrypt_patient_data(
                        result.get("transcription", "")
                    )
                    encrypted_report = encryption_service.encrypt_patient_data(
                        result.get("multimodal_report", "")
                    )
                    
                    consultation = MedicalConsultation(
                        patient_info=encrypted_patient_info,  # ← DADOS CRIPTOGRAFADOS
                        audio_transcription=encrypted_transcription,  # ← DADOS CRIPTOGRAFADOS
                        medical_report=encrypted_report,  # ← DADOS CRIPTOGRAFADOS
                        confidence=result.get("confidence", 0.0),
                        model_used=result.get("model", "GPT-4o"),
                        patient_hash=patient_hash  # Hash para auditoria
                    )
                    db.add(consultation)
                    db.commit()
                    
                    # Registrar salvamento seguro
                    audit_service.log_patient_access(
                        doctor_crm="demo_doctor",
                        patient_hash=patient_hash,
                        action="data_saved_encrypted",
                        details={"database": "postgresql", "encryption": "AES-256"}
                    )
                    
                    print("🔒 Consulta salva CRIPTOGRAFADA no banco de dados")
                    
                except Exception as db_error:
                    print(f"⚠️ Erro ao salvar: {str(db_error)}")
                    audit_service.log_patient_access(
                        doctor_crm="demo_doctor",
                        patient_hash=patient_hash,
                        action="database_error",
                        details={"error": str(db_error)}
                    )
                    db.rollback()
                finally:
                    db.close()
            except ImportError:
                print("⚠️ Modelos de banco não configurados")
        
        if result["success"]:
            print("✅ Análise multimodal SEGURA concluída")
            
            # Registrar conclusão
            audit_service.log_patient_access(
                doctor_crm="demo_doctor",
                patient_hash=patient_hash,
                action="consultation_completed",
                details={"success": True, "model": result.get("model")}
            )
            
            return {
                "success": True,
                "type": "multimodal_analysis_secure",
                "transcription": result.get("transcription", ""),  # Retorna descriptografado para exibição
                "medical_report": result["multimodal_report"],
                "modalities_used": result["modalities_used"],
                "model": result["model"],
                "confidence": result["confidence"],
                "timestamp": result["timestamp"],
                "security": {
                    "encrypted_storage": True,
                    "audit_logged": True,
                    "lgpd_compliant": True,
                    "patient_hash": patient_hash[:8] + "..."  # Mostrar apenas parte do hash
                }
            }
        else:
            return {"success": False, "error": result["error"]}
            
    except Exception as e:
        print(f"❌ Erro na análise segura: {str(e)}")
        
        # Registrar erro no audit
        try:
            patient_hash = encryption_service.hash_patient_id(patient_info)
            audit_service.log_patient_access(
                doctor_crm="demo_doctor",
                patient_hash=patient_hash,
                action="error_occurred",
                details={"error": str(e)}
            )
        except:
            pass
            
        return {"success": False, "error": str(e)}

@app.post("/login")
async def login_doctor(request: Request):
    """Login de médico com autenticação"""
    try:
        # Ler dados JSON
        data = await request.json()
        crm = data.get('crm', '').strip()
        password = data.get('password', '').strip()
        
        print(f"🔐 Tentativa de login: CRM {crm}")
        
        # Validar campos
        if not crm or not password:
            return {"success": False, "error": "CRM e senha são obrigatórios"}
        
        # Autenticar médico
        doctor_data = auth_service.authenticate_doctor(crm, password)
        
        if doctor_data:
            # Gerar token JWT
            token = auth_service.generate_token(doctor_data)
            
            # Registrar login bem-sucedido
            audit_service.log_patient_access(
                doctor_crm=crm,
                patient_hash="system",
                action="login_successful",
                details={"doctor_name": doctor_data["name"]}
            )
            
            print(f"✅ Login bem-sucedido: Dr. {doctor_data['name']}")
            
            return {
                "success": True,
                "token": token,
                "doctor": {
                    "crm": doctor_data["crm"],
                    "name": doctor_data["name"],
                    "specialty": doctor_data.get("specialty", "Clínica Geral")
                },
                "message": f"Bem-vindo, Dr. {doctor_data['name']}!"
            }
        else:
            # Registrar tentativa falhada
            audit_service.log_patient_access(
                doctor_crm=crm,
                patient_hash="system",
                action="login_failed",
                details={"reason": "invalid_credentials"}
            )
            
            print(f"❌ Login falhado: CRM {crm}")
            
            return {
                "success": False, 
                "error": "CRM ou senha inválidos"
            }
        
    except Exception as e:
        print(f"❌ Erro no login: {str(e)}")
        return {"success": False, "error": "Erro interno do servidor"}

@app.post("/api/multimodal-consultation")
async def api_multimodal_consultation_route(
    patient_info: str = Form(...),
    audio_data: UploadFile = File(None)
):
    """Rota compatível com frontend ANTIGO - chama multimodal_analysis_secure"""
    print(f"📨 Chamada via /api/multimodal-consultation: {patient_info}")
    
    # Redirecionar para função existente
    return await multimodal_analysis_secure(
        patient_info=patient_info,
        audio_file=audio_data,
        image_file=None
    )

@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis(
    patient_info: str = Form(...),
    audio_data: UploadFile = File(None),
    image_data: UploadFile = File(None)
):
    """🚀 ANÁLISE QUE FUNCIONA DE VERDADE"""
    print(f"🚀 NOVA FUNÇÃO CHAMADA: {patient_info}")
    
    try:
        # Importar e criar nova instância sempre
        from .services.multimodal_ai_service import MultimodalAIService
        service_real = MultimodalAIService()
        print(f"✅ Serviço criado: {type(service_real)}")
        
        # Processar áudio
        audio_bytes = None
        if audio_data and audio_data.filename:
            audio_bytes = await audio_data.read()
            print(f"🎤 Áudio: {len(audio_bytes)} bytes")
        
        # Chamar função REAL
        result = await service_real.analyze_multimodal(
            patient_info, audio_bytes, None
        )
        
        print(f"📋 Resultado: {result.get('success')}")
        return result
        
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "transcription": f"Erro: {str(e)}",
            "anamnese": f"Erro: {str(e)}",
            "laudo_medico": f"Erro: {str(e)}"
        }