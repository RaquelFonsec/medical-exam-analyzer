# ============================================================================
# SISTEMA MÉDICO INTEGRADO - VERSÃO CORRIGIDA
# OpenAI Whisper + AWS Textract
# ============================================================================

import os
import sys
import tempfile
import logging
import io
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

# Core imports
import boto3
import openai
from PIL import Image
import cv2
import numpy as np

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# Web framework
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Environment
from dotenv import load_dotenv
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Settings:
    """Configurações do sistema"""
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

settings = Settings()

# ============================================================================
# TRANSCRIPTION SERVICE CORRIGIDO
# ============================================================================

class TranscriptionService:
    """Serviço de transcrição com OpenAI Whisper API"""
    
    def __init__(self):
        """Inicializar serviço de transcrição"""
        try:
            # Verificar se a chave API está disponível
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
            
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✅ TranscriptionService inicializado com OpenAI Whisper")
            logger.info(f"🔑 API Key configurada: {settings.OPENAI_API_KEY[:10]}...{settings.OPENAI_API_KEY[-4:]}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar TranscriptionService: {e}")
            self.client = None
    
    async def transcribe_audio_bytes(self, audio_bytes: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """
        Transcrição de áudio a partir de bytes usando OpenAI Whisper API
        
        Args:
            audio_bytes: Dados binários do áudio
            filename: Nome do arquivo (para contexto)
        
        Returns:
            Dict com resultado da transcrição
        """
        if not self.client:
            logger.error("❌ Cliente OpenAI não disponível para transcrição")
            return {
                "transcription": "Erro: Cliente OpenAI não configurado. Verifique OPENAI_API_KEY.",
                "success": False,
                "error": "Cliente não inicializado"
            }
        
        temp_file_path = None
        
        try:
            logger.info(f"🎤 Processando áudio: {len(audio_bytes)} bytes")
            
            # Validações básicas
            if len(audio_bytes) < 100:
                logger.warning("⚠️ Arquivo de áudio muito pequeno")
                return {
                    "transcription": "Erro: Arquivo de áudio muito pequeno ou vazio",
                    "success": False,
                    "error": "Arquivo muito pequeno"
                }
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_bytes)
                temp_file_path = tmp_file.name
            
            logger.info(f"📁 Áudio salvo temporariamente: {temp_file_path}")
            
            # Verificar tamanho do arquivo
            file_size = os.path.getsize(temp_file_path)
            logger.info(f"📊 Tamanho do arquivo: {file_size} bytes")
            
            if file_size == 0:
                logger.error("❌ Arquivo de áudio vazio")
                return {
                    "transcription": "Erro: Arquivo de áudio vazio",
                    "success": False,
                    "error": "Arquivo vazio"
                }
            
            # Realizar transcrição com Whisper API
            logger.info("🤖 Iniciando transcrição com Whisper API...")
            
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt",  # Português
                    response_format="text",
                    temperature=0.1,  # Mais conservador para melhor precisão
                    prompt="Esta é uma consulta médica em português. O paciente está relatando sintomas e histórico médico."
                )
            
            # Extrair texto da resposta
            transcription_text = transcript if isinstance(transcript, str) else str(transcript)
            transcription_text = transcription_text.strip()
            
            if transcription_text:
                logger.info(f"✅ Transcrição concluída: {len(transcription_text)} caracteres")
                logger.info(f"📝 Preview: {transcription_text[:100]}...")
                
                return {
                    "transcription": transcription_text,
                    "language": "pt",
                    "model": "whisper-1",
                    "success": True,
                    "character_count": len(transcription_text),
                    "filename": filename
                }
            else:
                logger.warning("⚠️ Transcrição retornou vazio")
                return {
                    "transcription": "Nenhum texto foi detectado no áudio. Verifique a qualidade da gravação.",
                    "success": False,
                    "error": "Transcrição vazia"
                }
            
        except openai.BadRequestError as e:
            error_msg = str(e)
            logger.error(f"❌ Erro de requisição OpenAI: {error_msg}")
            
            if "audio_too_short" in error_msg:
                suggestion = "Grave pelo menos 0.1 segundos (idealmente 2-3 segundos) de fala clara"
            elif "invalid_file" in error_msg:
                suggestion = "Use formatos suportados (mp3, mp4, wav, webm, m4a)"
            else:
                suggestion = "Verifique o formato do arquivo e qualidade da gravação"
            
            return {
                "transcription": f"Erro na transcrição: {error_msg}",
                "success": False,
                "error": error_msg,
                "suggestion": suggestion
            }
            
        except openai.AuthenticationError as e:
            logger.error(f"❌ Erro de autenticação OpenAI: {e}")
            return {
                "transcription": "Erro de autenticação. Verifique se a OPENAI_API_KEY está correta.",
                "success": False,
                "error": str(e)
            }
            
        except openai.RateLimitError as e:
            logger.error(f"❌ Limite de rate da OpenAI excedido: {e}")
            return {
                "transcription": "Limite de requisições excedido. Aguarde alguns segundos e tente novamente.",
                "success": False,
                "error": str(e)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro inesperado na transcrição: {type(e).__name__}: {e}")
            return {
                "transcription": f"Erro inesperado: {str(e)}",
                "success": False,
                "error": str(e)
            }
            
        finally:
            # Limpar arquivo temporário
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info("🗑️ Arquivo temporário removido")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao remover arquivo temporário: {e}")
    
    async def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Transcrição de áudio a partir de caminho do arquivo
        
        Args:
            audio_file_path: Caminho para o arquivo de áudio
        
        Returns:
            Dict com resultado da transcrição
        """
        try:
            if not os.path.exists(audio_file_path):
                logger.error(f"❌ Arquivo não encontrado: {audio_file_path}")
                return {
                    "transcription": f"Arquivo não encontrado: {audio_file_path}",
                    "success": False,
                    "error": "Arquivo não encontrado"
                }
            
            # Ler arquivo e usar o método de bytes
            with open(audio_file_path, "rb") as f:
                audio_bytes = f.read()
            
            filename = os.path.basename(audio_file_path)
            return await self.transcribe_audio_bytes(audio_bytes, filename)
            
        except Exception as e:
            logger.error(f"❌ Erro ao ler arquivo: {e}")
            return {
                "transcription": f"Erro ao ler arquivo: {str(e)}",
                "success": False,
                "error": str(e)
            }

# ============================================================================
# AWS TEXTRACT SERVICE (MANTIDO ORIGINAL)
# ============================================================================

class TextractExamService:
    """Serviço especializado em extração de texto de exames médicos"""
    
    def __init__(self):
        self.client = None
        self.supported_formats = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
        self._init_client()
    
    def _init_client(self):
        """Inicializa cliente AWS Textract"""
        try:
            session = boto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            self.client = session.client('textract')
            logger.info("✅ AWS Textract client initialized")
            
        except Exception as e:
            logger.error(f"❌ AWS Textract initialization failed: {e}")
            self.client = None
    
    def _convert_pdf_to_images(self, pdf_bytes: bytes) -> List[bytes]:
        """Converte PDF em imagens"""
        if not PDF2IMAGE_AVAILABLE:
            logger.error("❌ pdf2image não disponível")
            return []
            
        try:
            images = convert_from_bytes(pdf_bytes, dpi=300)
            image_bytes_list = []
            
            for img in images:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                image_bytes_list.append(img_byte_arr.getvalue())
            
            logger.info(f"📄 PDF converted to {len(image_bytes_list)} images")
            return image_bytes_list
            
        except Exception as e:
            logger.error(f"❌ PDF conversion failed: {e}")
            return []
    
    def _preprocess_image_for_ocr(self, image_bytes: bytes) -> bytes:
        """Pré-processa imagem para melhor OCR"""
        try:
            # Carregar imagem
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return image_bytes
            
            # Converter para escala de cinza
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Aplicar denoising
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Aplicar threshold adaptativo para melhor contraste
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Converter de volta para bytes
            _, buffer = cv2.imencode('.png', thresh)
            return buffer.tobytes()
            
        except Exception as e:
            logger.warning(f"⚠️ Image preprocessing failed, using original: {e}")
            return image_bytes
    
    def _detect_medical_content(self, text: str) -> Dict[str, Any]:
        """Detecta se o texto contém conteúdo médico"""
        
        medical_keywords = [
            'hemograma', 'glicemia', 'colesterol', 'triglicerídeos', 'creatinina',
            'ureia', 'tsh', 't3', 't4', 'hemoglobina', 'hematócrito', 'leucócitos',
            'plaquetas', 'exame', 'laboratorial', 'resultado', 'análise', 'valores',
            'referência', 'normal', 'alterado', 'mg/dl', 'g/dl', 'mmol/l'
        ]
        
        text_lower = text.lower()
        detected_keywords = [kw for kw in medical_keywords if kw in text_lower]
        
        is_medical = len(detected_keywords) > 0
        confidence = min(1.0, len(detected_keywords) * 0.2)
        
        return {
            'is_medical_exam': is_medical,
            'confidence': confidence,
            'detected_keywords': detected_keywords,
            'keyword_count': len(detected_keywords)
        }
    
    async def extract_exam_text(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Extrai texto de exame médico"""
        try:
            if not self.client:
                return {
                    'success': False,
                    'extracted_text': '',
                    'error': 'AWS Textract não configurado - verifique credenciais AWS'
                }
            
            logger.info(f"📄 Processando exame: {filename} ({len(file_bytes)} bytes)")
            
            is_pdf = filename.lower().endswith('.pdf')
            all_text = ""
            all_confidences = []
            pages_processed = 0
            
            if is_pdf:
                # Processar PDF página por página
                image_bytes_list = self._convert_pdf_to_images(file_bytes)
                
                if not image_bytes_list:
                    return {
                        'success': False,
                        'extracted_text': '',
                        'error': 'Falha na conversão do PDF - instale pdf2image: pip install pdf2image'
                    }
                
                for i, img_bytes in enumerate(image_bytes_list):
                    logger.info(f"🔄 Processando página {i+1}/{len(image_bytes_list)}")
                    
                    # Pré-processar imagem
                    processed_img = self._preprocess_image_for_ocr(img_bytes)
                    
                    # Chamar Textract
                    response = self.client.detect_document_text(Document={'Bytes': processed_img})
                    
                    # Extrair texto da página
                    page_text = ""
                    page_confidences = []
                    
                    for block in response.get('Blocks', []):
                        if block['BlockType'] == 'LINE':
                            line_text = block.get('Text', '')
                            confidence = block.get('Confidence', 0)
                            
                            page_text += line_text + "\n"
                            page_confidences.append(confidence)
                    
                    all_text += f"\n--- PÁGINA {i+1} ---\n{page_text}"
                    all_confidences.extend(page_confidences)
                    pages_processed += 1
            
            else:
                # Processar imagem única
                processed_img = self._preprocess_image_for_ocr(file_bytes)
                
                response = self.client.detect_document_text(Document={'Bytes': processed_img})
                
                for block in response.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        line_text = block.get('Text', '')
                        confidence = block.get('Confidence', 0)
                        
                        all_text += line_text + "\n"
                        all_confidences.append(confidence)
                
                pages_processed = 1
            
            # Calcular métricas
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
            
            # Detectar conteúdo médico
            medical_analysis = self._detect_medical_content(all_text)
            
            result = {
                'success': True,
                'filename': filename,
                'extracted_text': all_text.strip(),
                'text_length': len(all_text.strip()),
                'avg_confidence': round(avg_confidence, 2),
                'pages_processed': pages_processed,
                'document_type': 'PDF' if is_pdf else 'Image',
                'medical_analysis': medical_analysis,
                'service_used': 'AWS Textract',
                'processing_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Exame processado com sucesso")
            logger.info(f"📊 Páginas: {pages_processed}, Texto: {len(all_text)} chars, Confiança: {avg_confidence:.1f}%")
            logger.info(f"🏥 Conteúdo médico detectado: {medical_analysis['is_medical_exam']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento do exame: {e}")
            return {
                'success': False,
                'extracted_text': '',
                'error': str(e),
                'filename': filename,
                'service_used': 'AWS Textract',
                'processing_timestamp': datetime.now().isoformat()
            }

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="Medical System - Transcrição + Exames",
    version="1.1",
    description="Sistema integrado com OpenAI Whisper e AWS Textract (CORRIGIDO)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar serviços
transcription_service = TranscriptionService()
textract_service = TextractExamService()

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis(
    patient_info: str = Form(default=""),
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None)
):
    """🏥 ENDPOINT PRINCIPAL - ANÁLISE MÉDICA COMPLETA (CORRIGIDO)"""
    
    start_time = datetime.now()
    
    try:
        logger.info("🚀 Nova análise médica iniciada")
        logger.info(f"📋 Patient info: {patient_info[:50]}...")
        logger.info(f"🎤 Audio: {audio.filename if audio else 'None'}")
        logger.info(f"📄 Image: {image.filename if image else 'None'}")
        
        # Resultado base
        result = {
            'success': True,
            'timestamp': start_time.isoformat(),
            'patient_info': patient_info,
            'transcription': '',
            'laudo_medico': '',
            'processing_details': {
                'transcription_service': 'OpenAI Whisper API',
                'extraction_service': 'AWS Textract',
                'audio_processed': False,
                'exam_processed': False,
                'transcription_details': {},
                'extraction_details': {}
            }
        }
        
        # PROCESSAR ÁUDIO (TRANSCRIÇÃO) - CORRIGIDO
        if audio and audio.filename:
            try:
                logger.info(f"🎤 Processando áudio: {audio.filename}")
                audio_data = await audio.read()
                
                # Usar o método corrigido do TranscriptionService
                transcription_result = await transcription_service.transcribe_audio_bytes(
                    audio_data, audio.filename
                )
                
                if transcription_result.get('success', False):
                    result['transcription'] = transcription_result.get('transcription', '')
                    result['processing_details']['audio_processed'] = True
                    result['processing_details']['transcription_details'] = {
                        'model': transcription_result.get('model', 'whisper-1'),
                        'language': transcription_result.get('language', 'pt'),
                        'character_count': transcription_result.get('character_count', 0)
                    }
                    logger.info(f"✅ Transcrição concluída com sucesso")
                else:
                    result['transcription'] = transcription_result.get('transcription', 'Erro na transcrição')
                    result['processing_details']['transcription_details'] = {
                        'error': transcription_result.get('error', 'Erro desconhecido'),
                        'suggestion': transcription_result.get('suggestion', '')
                    }
                    logger.warning("⚠️ Transcrição falhou")
                    
            except Exception as e:
                logger.error(f"❌ Erro na transcrição: {e}")
                result['transcription'] = f"Erro na transcrição: {str(e)}"
                result['processing_details']['transcription_details'] = {'error': str(e)}
        
        # PROCESSAR DOCUMENTO/EXAME (TEXTRACT) - MANTIDO
        if image and image.filename:
            try:
                logger.info(f"📄 Processando exame: {image.filename}")
                image_data = await image.read()
                
                # Usar AWS Textract
                extraction_result = await textract_service.extract_exam_text(image_data, image.filename)
                
                if extraction_result.get('success'):
                    extracted_text = extraction_result.get('extracted_text', '')
                    medical_analysis = extraction_result.get('medical_analysis', {})
                    
                    if extracted_text:
                        result['laudo_medico'] = extracted_text
                        result['processing_details']['exam_processed'] = True
                        result['processing_details']['extraction_details'] = {
                            'medical_content_detected': medical_analysis.get('is_medical_exam', False),
                            'textract_confidence': extraction_result.get('avg_confidence', 0),
                            'pages_processed': extraction_result.get('pages_processed', 0),
                            'document_type': extraction_result.get('document_type', 'Unknown')
                        }
                        
                        logger.info(f"✅ Extração concluída: {len(extracted_text)} chars")
                    else:
                        result['laudo_medico'] = "Nenhum texto foi extraído do documento."
                        result['processing_details']['extraction_details'] = {'error': 'Texto vazio'}
                else:
                    error_msg = extraction_result.get('error', 'Erro desconhecido')
                    result['laudo_medico'] = f"Erro na extração: {error_msg}"
                    result['processing_details']['extraction_details'] = {'error': error_msg}
                    logger.error(f"❌ Falha na extração: {error_msg}")
                    
            except Exception as e:
                logger.error(f"❌ Erro no processamento do exame: {e}")
                result['laudo_medico'] = f"Erro no processamento: {str(e)}"
                result['processing_details']['extraction_details'] = {'error': str(e)}
        
        # FINALIZAR
        processing_time = (datetime.now() - start_time).total_seconds()
        result['processing_time_seconds'] = round(processing_time, 2)
        
        # Verificar se pelo menos um processamento foi bem-sucedido
        if not result['processing_details']['audio_processed'] and not result['processing_details']['exam_processed']:
            if not audio and not image:
                result['transcription'] = "Nenhum arquivo de áudio fornecido"
                result['laudo_medico'] = "Nenhum documento de exame fornecido"
            
        logger.info(f"✅ Análise concluída em {processing_time:.2f}s")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro geral na análise: {e}")
        
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'processing_time_seconds': (datetime.now() - start_time).total_seconds()
            }
        )

@app.get("/api/health")
async def health_check():
    """🔍 Verificação de saúde do sistema"""
    
    health = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.1 - Fixed Transcription',
        'services': {}
    }
    
    # Verificar OpenAI Whisper
    health['services']['transcription'] = {
        'service': 'OpenAI Whisper API',
        'available': transcription_service.client is not None,
        'api_key_configured': bool(settings.OPENAI_API_KEY),
        'api_key_preview': f"{settings.OPENAI_API_KEY[:10]}...{settings.OPENAI_API_KEY[-4:]}" if settings.OPENAI_API_KEY else "Not configured"
    }
    
    # Verificar AWS Textract
    health['services']['textract'] = {
        'service': 'AWS Textract',
        'available': textract_service.client is not None,
        'region': settings.AWS_REGION,
        'credentials_configured': bool(settings.AWS_ACCESS_KEY_ID)
    }
    
    # Verificar dependências
    health['dependencies'] = {
        'pdf2image': PDF2IMAGE_AVAILABLE,
        'opencv': True,
        'boto3': True,
        'openai': True
    }
    
    return health

@app.get("/api/system-status")
async def system_status():
    """📊 Status detalhado do sistema"""
    
    return {
        'system': 'Medical Analysis System - Fixed',
        'version': '1.1',
        'components': {
            'transcription': {
                'service': 'OpenAI Whisper API',
                'status': '✅ Ready' if transcription_service.client else '❌ Not configured',
                'supported_formats': ['mp3', 'mp4', 'wav', 'webm', 'm4a'],
                'features': ['Portuguese language', 'Medical context prompts', 'High accuracy', 'Bytes processing'],
                'methods': ['transcribe_audio_bytes', 'transcribe_audio']
            },
            'text_extraction': {
                'service': 'AWS Textract',
                'status': '✅ Ready' if textract_service.client else '❌ Not configured',
                'supported_formats': list(textract_service.supported_formats),
                'features': ['PDF multi-page', 'Image preprocessing', 'Medical content detection']
            }
        },
        'configuration': {
            'openai_api_key': '✅ Configured' if settings.OPENAI_API_KEY else '❌ Missing',
            'aws_credentials': '✅ Configured' if settings.AWS_ACCESS_KEY_ID else '❌ Missing',
            'aws_region': settings.AWS_REGION
        },
        'fixes_applied': [
            '✅ Corrigida chamada do método de transcrição',
            '✅ Melhor tratamento de erros na transcrição',
            '✅ Logs mais detalhados',
            '✅ Validação de arquivos de áudio',
            '✅ Retorno estruturado com detalhes'
        ]
    }

@app.get("/")
async def root():
    """🏠 Página inicial"""
    
    return {
        'message': 'Medical Analysis System - Fixed Transcription',
        'version': '1.1',
        'description': 'Sistema integrado com transcrição corrigida',
        'features': [
            '🎤 OpenAI Whisper API para transcrição (CORRIGIDO)',
            '📄 AWS Textract para extração de exames',
            '🏥 Detecção de conteúdo médico',
            '📊 Métricas de qualidade',
            '⚡ Processamento otimizado',
            '🔧 Tratamento de erros melhorado'
        ],
        'endpoints': {
            'main': 'POST /api/intelligent-medical-analysis',
            'health': 'GET /api/health',
            'status': 'GET /api/system-status'
        },
        'ready': {
            'transcription': transcription_service.client is not None,
            'textract': textract_service.client is not None
        },
        'changelog': [
            'Fix: Método transcribe_audio_bytes implementado corretamente',
            'Fix: Melhor validação de arquivos de áudio',
            'Fix: Tratamento de erros específicos do OpenAI',
            'Improvement: Logs mais detalhados',
            'Improvement: Retorno estruturado com detalhes de processamento'
        ]
    }

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting Fixed Medical System")
    print("=" * 60)
    
    # Verificar configurações
    print("📋 CONFIGURAÇÕES:")
    print(f"🎤 OpenAI Whisper: {'✅ Ready' if transcription_service.client else '❌ Check OPENAI_API_KEY'}")
    if settings.OPENAI_API_KEY:
        print(f"   API Key: {settings.OPENAI_API_KEY[:10]}...{settings.OPENAI_API_KEY[-4:]}")
    else:
        print("   ❌ OPENAI_API_KEY não configurada")
    
    print(f"📄 AWS Textract: {'✅ Ready' if textract_service.client else '❌ Check AWS credentials'}")
    if settings.AWS_ACCESS_KEY_ID:
        print(f"   Region: {settings.AWS_REGION}")
        print(f"   Access Key: {settings.AWS_ACCESS_KEY_ID[:10]}...{settings.AWS_ACCESS_KEY_ID[-4:]}")
    else:
        print("   ❌ AWS credentials não configuradas")
    
    print()
    print("🔧 CORREÇÕES APLICADAS:")
    print("   ✅ Método transcribe_audio_bytes implementado")
    print("   ✅ Melhor tratamento de erros OpenAI")
    print("   ✅ Validação robusta de arquivos de áudio")
    print("   ✅ Logs detalhados para debugging")
    print("   ✅ Retorno estruturado com detalhes")
    
    print()
    print("🌐 ENDPOINTS DISPONÍVEIS:")
    print("   📍 Main API: POST http://localhost:8000/api/intelligent-medical-analysis")
    print("   📊 Health: GET http://localhost:8000/api/health")
    print("   📋 Status: GET http://localhost:8000/api/system-status")
    print("   🏠 Root: GET http://localhost:8000/")
    
    print()
    print("💡 TESTE DA TRANSCRIÇÃO:")
    print("   1. Envie um arquivo de áudio (mp3, wav, m4a, etc.)")
    print("   2. Verifique os logs para detalhes do processamento")
    print("   3. A resposta incluirá detalhes sobre sucesso/falha")
    
    if not settings.OPENAI_API_KEY:
        print()
        print("⚠️  ATENÇÃO: Configure OPENAI_API_KEY no arquivo .env")
        print("   export OPENAI_API_KEY='sua_chave_aqui'")
    
    if not settings.AWS_ACCESS_KEY_ID:
        print()
        print("⚠️  ATENÇÃO: Configure AWS credentials no arquivo .env")
        print("   export AWS_ACCESS_KEY_ID='sua_chave_aqui'")
        print("   export AWS_SECRET_ACCESS_KEY='sua_chave_secreta_aqui'")
    
    print()
    print("🚀 Iniciando servidor...")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )