# ============================================================================
# SISTEMA MÉDICO INTEGRADO -  + LLM
# OpenAI Whisper + AWS Textract + LLM Medical Analysis
# ============================================================================

import os
import sys
import tempfile
import logging
import io
import re
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Union, Tuple
from dataclasses import dataclass, asdict

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
from fastapi.responses import JSONResponse, HTMLResponse
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
# MODELOS DE DADOS PARA LLM
# ============================================================================

@dataclass
class ExamFinding:
    """Representa um achado em exame"""
    parameter: str
    value: str
    reference_range: str
    status: str  # normal, alto, baixo, alterado
    severity: str  # leve, moderado, grave
    clinical_significance: str
    recommendation: str

@dataclass
class ExamSummary:
    """Resumo completo do exame"""
    exam_type: str
    patient_info: Dict
    exam_date: str
    findings: List[ExamFinding]
    overall_status: str
    key_alterations: List[str]
    clinical_summary: str
    recommendations: List[str]
    follow_up_needed: bool
    llm_analysis: str  # Análise gerada por LLM
    risk_assessment: str  # Avaliação de risco por LLM

# ============================================================================
# TRANSCRIPTION SERVICE (MANTIDO IGUAL)
# ============================================================================

class TranscriptionService:
    """Serviço de transcrição com OpenAI Whisper API"""
    
    def __init__(self):
        """Inicializar serviço de transcrição"""
        try:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
            
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✅ TranscriptionService inicializado com OpenAI Whisper")
            logger.info(f"🔑 API Key configurada: {settings.OPENAI_API_KEY[:10]}...{settings.OPENAI_API_KEY[-4:]}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar TranscriptionService: {e}")
            self.client = None
    
    async def transcribe_audio_bytes(self, audio_bytes: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """Transcrição de áudio a partir de bytes usando OpenAI Whisper API"""
        if not self.client:
            logger.error("❌ Cliente OpenAI não disponível para transcrição")
            return {
                "transcription": "Erro: Cliente OpenAI não configurado. Verifique OPENAI_API_KEY.",
                "success": False,
                "error": "Cliente não inicializado"
            }
        
        temp_file_path = None
        
        try:
            logger.info(f" Processando áudio: {len(audio_bytes)} bytes")
            
            if len(audio_bytes) < 100:
                logger.warning("⚠️ Arquivo de áudio muito pequeno")
                return {
                    "transcription": "Erro: Arquivo de áudio muito pequeno ou vazio",
                    "success": False,
                    "error": "Arquivo muito pequeno"
                }
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_bytes)
                temp_file_path = tmp_file.name
            
            logger.info(f"📁 Áudio salvo temporariamente: {temp_file_path}")
            
            file_size = os.path.getsize(temp_file_path)
            logger.info(f" Tamanho do arquivo: {file_size} bytes")
            
            if file_size == 0:
                logger.error("❌ Arquivo de áudio vazio")
                return {
                    "transcription": "Erro: Arquivo de áudio vazio",
                    "success": False,
                    "error": "Arquivo vazio"
                }
            
            logger.info("🤖 Iniciando transcrição com Whisper API...")
            
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt",
                    response_format="text",
                    temperature=0.1,
                    prompt="Esta é uma consulta médica em português. O paciente está relatando sintomas e histórico médico."
                )
            
            transcription_text = transcript if isinstance(transcript, str) else str(transcript)
            transcription_text = transcription_text.strip()
            
            if transcription_text:
                logger.info(f" Transcrição concluída: {len(transcription_text)} caracteres")
                logger.info(f" Preview: {transcription_text[:100]}...")
                
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
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info("🗑️ Arquivo temporário removido")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao remover arquivo temporário: {e}")
    
    async def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcrição de áudio a partir de caminho do arquivo"""
        try:
            if not os.path.exists(audio_file_path):
                logger.error(f"❌ Arquivo não encontrado: {audio_file_path}")
                return {
                    "transcription": f"Arquivo não encontrado: {audio_file_path}",
                    "success": False,
                    "error": "Arquivo não encontrado"
                }
            
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
# AWS TEXTRACT SERVICE (MANTIDO IGUAL)
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
            logger.info(" AWS Textract client initialized")
            
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
            
            logger.info(f" PDF converted to {len(image_bytes_list)} images")
            return image_bytes_list
            
        except Exception as e:
            logger.error(f"❌ PDF conversion failed: {e}")
            return []
    
    def _preprocess_image_for_ocr(self, image_bytes: bytes) -> bytes:
        """Pré-processa imagem para melhor OCR"""
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return image_bytes
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray)
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
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
            
            logger.info(f" Processando exame: {filename} ({len(file_bytes)} bytes)")
            
            is_pdf = filename.lower().endswith('.pdf')
            all_text = ""
            all_confidences = []
            pages_processed = 0
            
            if is_pdf:
                image_bytes_list = self._convert_pdf_to_images(file_bytes)
                
                if not image_bytes_list:
                    return {
                        'success': False,
                        'extracted_text': '',
                        'error': 'Falha na conversão do PDF - instale pdf2image: pip install pdf2image'
                    }
                
                for i, img_bytes in enumerate(image_bytes_list):
                    logger.info(f" Processando página {i+1}/{len(image_bytes_list)}")
                    
                    processed_img = self._preprocess_image_for_ocr(img_bytes)
                    response = self.client.detect_document_text(Document={'Bytes': processed_img})
                    
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
                processed_img = self._preprocess_image_for_ocr(file_bytes)
                response = self.client.detect_document_text(Document={'Bytes': processed_img})
                
                for block in response.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        line_text = block.get('Text', '')
                        confidence = block.get('Confidence', 0)
                        
                        all_text += line_text + "\n"
                        all_confidences.append(confidence)
                
                pages_processed = 1
            
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
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
            
            logger.info(f" Exame processado com sucesso")
            logger.info(f" Páginas: {pages_processed}, Texto: {len(all_text)} chars, Confiança: {avg_confidence:.1f}%")
            logger.info(f" Conteúdo médico detectado: {medical_analysis['is_medical_exam']}")
            
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
# AGENTE LLM FOCADO APENAS EM ANÁLISE CLÍNICA + PRINCIPAIS ACHADOS
# ============================================================================

class LLMExamAnalyzer:
    """Agente LLM FOCADO APENAS em análise clínica e principais achados"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        
    async def analyze_exam_with_llm(self, extracted_text: str, patient_info: Dict = None) -> Dict[str, Any]:
        """Análise FOCADA do exame usando LLM - APENAS análise clínica + principais achados"""
        
        if not self.openai_client:
            return {
                'success': False,
                'error': 'OpenAI API não configurada',
                'fallback_analysis': self._basic_analysis(extracted_text)
            }
        
        try:
            logger.info("🤖 Iniciando análise LLM FOCADA do exame...")
            
            # 1. Preparar contexto
            context = self._prepare_context(extracted_text, patient_info)
            
            # 2. Análise clínica principal (FOCO PRINCIPAL)
            clinical_analysis = await self._generate_clinical_analysis(context)
            
            # 3. Principais achados (extração + LLM)
            key_findings = self._extract_key_findings(extracted_text)
            
            # 4. Tipo de exame (simples)
            exam_type = self._identify_exam_type(extracted_text)
            
            result = {
                'success': True,
                'llm_analysis': {
                    'clinical_analysis': clinical_analysis,
                    'key_findings': key_findings,
                    'exam_type': exam_type,
                    'overall_status': 'Análise clínica realizada - Consultar médico para interpretação completa'
                },
                'processing_timestamp': datetime.now().isoformat(),
                'model_used': 'gpt-3.5-turbo'
            }
            
            logger.info("✅ Análise LLM FOCADA concluída com sucesso")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na análise LLM: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_analysis': self._basic_analysis(extracted_text)
            }
    
    def _prepare_context(self, text: str, patient_info: Dict = None) -> str:
        """Prepara contexto estruturado para LLM"""
        context = f"""
TEXTO DO EXAME MÉDICO:
{text[:2000]}

INFORMAÇÕES DO PACIENTE:
"""
        if patient_info:
            context += f"- Idade: {patient_info.get('age', 'Não informado')}\n"
            context += f"- Sexo: {patient_info.get('gender', 'Não informado')}\n"
            context += f"- Informações adicionais: {patient_info.get('additional_info', 'Nenhuma')}\n"
        else:
            context += "- Não informadas\n"
        
        return context
    
    async def _generate_clinical_analysis(self, context: str) -> str:
        """Gera análise clínica detalhada - FOCO PRINCIPAL"""
        try:
            prompt = f"""
Como médico especialista, analise este exame e forneça uma interpretação clínica:

{context}

Forneça:
1. Principais achados clínicos
2. Correlação entre resultados alterados
3. Possíveis diagnósticos a considerar
4. Significado clínico das alterações

Resposta em até 200 palavras, linguagem técnica mas acessível.
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um médico especialista em medicina laboratorial."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ Erro na análise clínica: {e}")
            return "Análise clínica automática não disponível."
    
    def _extract_key_findings(self, text: str) -> List[str]:
        """Extrai achados principais usando regex básico"""
        findings = []
        
        # Padrões para detectar valores alterados
        patterns = [
            r'([A-ZÀ-Ÿ][a-zà-ÿ\s\-\/]+)[:\s]+([0-9,\.]+)\s*([a-zA-Z\/³%μ]*)',
            r'(alto|baixo|elevado|diminuído|aumentado)[:\s]*([A-ZÀ-Ÿ][a-zà-ÿ\s\-\/]+)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                finding = match.group(0).strip()
                if len(finding) > 5 and finding not in findings:
                    findings.append(finding)
        
        return findings[:5]
    
    def _identify_exam_type(self, text: str) -> str:
        """Identifica tipo de exame"""
        text_lower = text.lower()
        
        exam_types = {
            'hemograma': ['hemograma', 'hemácias', 'leucócitos', 'plaquetas'],
            'bioquimica': ['glicose', 'colesterol', 'creatinina', 'ureia'],
            'hormonal': ['tsh', 't4', 't3', 'cortisol'],
            'urina': ['urina', 'eas', 'sedimento']
        }
        
        for exam_type, keywords in exam_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return exam_type
        
        return 'geral'
    
    def _basic_analysis(self, text: str) -> Dict[str, Any]:
        """Análise básica sem LLM (fallback)"""
        return {
            'exam_type': self._identify_exam_type(text),
            'key_findings': self._extract_key_findings(text),
            'basic_summary': 'Análise básica realizada. Consulte um médico para interpretação completa.',
            'status': 'REQUER INTERPRETAÇÃO MÉDICA'
        }

# ============================================================================
# SERVIÇO INTEGRADO: TEXTRACT + LLM (MANTIDO IGUAL)
# ============================================================================

class EnhancedTextractService(TextractExamService):
    """Serviço Textract com análise LLM integrada"""
    
    def __init__(self):
        super().__init__()
        self.llm_analyzer = LLMExamAnalyzer()
    
    async def extract_and_analyze_exam(self, file_bytes: bytes, filename: str, patient_info: Dict = None) -> Dict[str, Any]:
        """Extrai texto do exame E faz análise LLM completa"""
        try:
            logger.info(f" Processando exame com análise LLM: {filename}")
            
            # 1. Extrair texto com Textract (método original mantido)
            extraction_result = await self.extract_exam_text(file_bytes, filename)
            
            if not extraction_result.get('success'):
                return extraction_result
            
            extracted_text = extraction_result.get('extracted_text', '')
            
            if not extracted_text.strip():
                return {
                    'success': False,
                    'error': 'Nenhum texto foi extraído do documento',
                    'filename': filename
                }
            
            # 2. Análise com LLM
            logger.info("🤖 Iniciando análise LLM...")
            llm_analysis = await self.llm_analyzer.analyze_exam_with_llm(extracted_text, patient_info)
            
            # 3. Resultado completo combinado
            result = {
                'success': True,
                'filename': filename,
                'extracted_text': extracted_text,
                'textract_details': {
                    'text_length': extraction_result.get('text_length', 0),
                    'avg_confidence': extraction_result.get('avg_confidence', 0),
                    'pages_processed': extraction_result.get('pages_processed', 0),
                    'medical_content_detected': extraction_result.get('medical_analysis', {}).get('is_medical_exam', False)
                },
                'llm_analysis': llm_analysis.get('llm_analysis', {}) if llm_analysis.get('success') else llm_analysis.get('fallback_analysis', {}),
                'llm_success': llm_analysis.get('success', False),
                'processing_time': datetime.now().isoformat(),
                'summary': {
                    'exam_type': llm_analysis.get('llm_analysis', {}).get('exam_type', 'Não identificado'),
                    'overall_status': llm_analysis.get('llm_analysis', {}).get('overall_status', 'Requer avaliação'),
                    'key_findings_count': len(llm_analysis.get('llm_analysis', {}).get('key_findings', [])),
                    'clinical_analysis_available': bool(llm_analysis.get('llm_analysis', {}).get('clinical_analysis'))
                }
            }
            
            logger.info(f" Análise completa concluída - Tipo: {result['summary']['exam_type']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento com LLM: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename,
                'processing_time': datetime.now().isoformat()
            }

# ============================================================================
# FASTAPI APPLICATION (MANTENDO ESTRUTURA ORIGINAL)
# ============================================================================

app = FastAPI(
    title="Medical System - Transcrição + Exames + LLM",
    version="2.0",
    description="Sistema integrado com OpenAI Whisper, AWS Textract e Análise LLM"
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
enhanced_textract_service = EnhancedTextractService()

# ============================================================================
# ENDPOINTS ORIGINAIS (MANTIDOS IGUAIS)
# ============================================================================

@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis(
    patient_info: str = Form(default=""),
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None)
):
    """ ENDPOINT PRINCIPAL - ANÁLISE MÉDICA COMPLETA (MANTIDO ORIGINAL)"""
    
    start_time = datetime.now()
    
    try:
        logger.info("🚀 Nova análise médica iniciada")
        logger.info(f" Patient info: {patient_info[:50]}...")
        logger.info(f" Audio: {audio.filename if audio else 'None'}")
        logger.info(f" Image: {image.filename if image else 'None'}")
        
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
        
        # PROCESSAR ÁUDIO (MANTIDO IGUAL)
        if audio and audio.filename:
            try:
                logger.info(f"🎤 Processando áudio: {audio.filename}")
                audio_data = await audio.read()
                
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
        
        # PROCESSAR DOCUMENTO/EXAME (MANTIDO IGUAL)
        if image and image.filename:
            try:
                logger.info(f" Processando exame: {image.filename}")
                image_data = await image.read()
                
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
                        
                        logger.info(f"Extração concluída: {len(extracted_text)} chars")
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
        
        processing_time = (datetime.now() - start_time).total_seconds()
        result['processing_time_seconds'] = round(processing_time, 2)
        
        if not result['processing_details']['audio_processed'] and not result['processing_details']['exam_processed']:
            if not audio and not image:
                result['transcription'] = "Nenhum arquivo de áudio fornecido"
                result['laudo_medico'] = "Nenhum documento de exame fornecido"
            
        logger.info(f"Análise concluída em {processing_time:.2f}s")
        
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

# ============================================================================
# NOVOS ENDPOINTS COM LLM
# ============================================================================

@app.post("/api/analyze-exam-with-llm")
async def analyze_exam_with_llm(
    file: UploadFile = File(...),
    patient_age: Optional[int] = Form(None),
    patient_gender: Optional[str] = Form(None),
    additional_info: Optional[str] = Form("")
):
    """ NOVO: Análise de exame com LLM integrado"""
    
    try:
        # Verificar formato do arquivo
        supported_formats = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']
        if not any(file.filename.lower().endswith(ext) for ext in supported_formats):
            return {
                'success': False,
                'error': f'Formato não suportado. Use: {", ".join(supported_formats)}'
            }
        
        # Verificar se OpenAI está configurado
        if not settings.OPENAI_API_KEY:
            return {
                'success': False,
                'error': 'OpenAI API não configurada. Análise LLM não disponível.',
                'suggestion': 'Configure OPENAI_API_KEY no arquivo .env'
            }
        
        # Ler arquivo
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            return {
                'success': False,
                'error': 'Arquivo vazio'
            }
        
        # Preparar informações do paciente
        patient_info = {}
        if patient_age:
            patient_info['age'] = patient_age
        if patient_gender:
            patient_info['gender'] = patient_gender
        if additional_info:
            patient_info['additional_info'] = additional_info
        
        logger.info(f"📁 Processando {file.filename} com LLM ({len(file_bytes)} bytes)")
        
        # Processar com serviço aprimorado
        result = await enhanced_textract_service.extract_and_analyze_exam(
            file_bytes, file.filename, patient_info
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro na análise com LLM: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.get("/api/exam-report-html/{exam_id}")
async def generate_exam_report_html(exam_id: str):
    """ NOVO: Gera relatório HTML detalhado do exame"""
    
    # Para demonstração - em produção, buscar do banco de dados
    sample_data = {
        'exam_id': exam_id,
        'patient_name': 'Paciente Exemplo',
        'exam_date': datetime.now().strftime('%d/%m/%Y'),
        'exam_type': 'Hemograma Completo',
        'overall_status': 'MODERADO - Acompanhamento necessário',
        'clinical_analysis': 'Hemograma revela anemia leve com possível deficiência de ferro. Leucocitose discreta pode indicar processo inflamatório em resolução.',
        'risk_assessment': 'MODERADO: Alterações requerem acompanhamento médico em 30 dias.',
        'key_alterations': [
            'Hemoglobina baixa (11.8 g/dL)',
            'Leucócitos elevados (12.200/mm³)',
            'Ferritina reduzida'
        ],
        'recommendations': [
            'Consulta médica em 15 dias',
            'Dieta rica em ferro',
            'Suplementação conforme orientação',
            'Repetir exame em 30 dias'
        ]
    }
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Relatório do Exame - {sample_data['exam_id']}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f7fa;
                color: #333;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 30px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            .ai-badge {{
                background: rgba(255,255,255,0.2);
                padding: 5px 15px;
                border-radius: 20px;
                font-size: 12px;
                margin-top: 10px;
                display: inline-block;
            }}
            .section {{
                background: white;
                padding: 25px;
                margin-bottom: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            .status-moderate {{
                background: #fff3cd;
                color: #856404;
                padding: 10px 15px;
                border-radius: 8px;
                border-left: 4px solid #ffc107;
                margin: 15px 0;
                font-weight: bold;
            }}
            .llm-analysis {{
                background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
                border-left: 4px solid #2196F3;
                padding: 20px;
                border-radius: 8px;
                position: relative;
            }}
            .llm-analysis::before {{
                content: "🤖";
                position: absolute;
                top: 10px;
                right: 15px;
                font-size: 24px;
            }}
            .alterations li {{
                background: #ffebee;
                margin: 8px 0;
                padding: 12px;
                border-left: 4px solid #f44336;
                border-radius: 5px;
                list-style: none;
            }}
            .recommendations li {{
                background: #e8f5e8;
                margin: 8px 0;
                padding: 12px;
                border-left: 4px solid #4caf50;
                border-radius: 5px;
                list-style: none;
            }}
            ul {{ padding: 0; }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding: 20px;
                background: #37474f;
                color: white;
                border-radius: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1> Relatório de Exame Médico</h1>
            <div class="ai-badge"> Análise Inteligente com LLM</div>
            <p>Sistema de Análise Médica com IA</p>
        </div>
        
        <div class="section">
            <h3> Informações do Exame</h3>
            <p><strong>ID:</strong> {sample_data['exam_id']}</p>
            <p><strong>Paciente:</strong> {sample_data['patient_name']}</p>
            <p><strong>Data:</strong> {sample_data['exam_date']}</p>
            <p><strong>Tipo:</strong> {sample_data['exam_type']}</p>
            <div class="status-moderate">{sample_data['overall_status']}</div>
        </div>
        
        <div class="section">
            <h3> Análise Clínica Inteligente</h3>
            <div class="llm-analysis">
                <p>{sample_data['clinical_analysis']}</p>
            </div>
        </div>
        
        <div class="section">
            <h3>⚠️ Avaliação de Risco</h3>
            <div style="background: #fff8e1; padding: 15px; border-radius: 8px; border-left: 4px solid #ff9800;">
                <strong>{sample_data['risk_assessment']}</strong>
            </div>
        </div>
        
        <div class="section">
            <h3> Principais Alterações</h3>
            <ul class="alterations">
    """
    
    for alteration in sample_data['key_alterations']:
        html_content += f"<li>{alteration}</li>"
    
    html_content += """
            </ul>
        </div>
        
        <div class="section">
            <h3> Recomendações</h3>
            <ul class="recommendations">
    """
    
    for recommendation in sample_data['recommendations']:
        html_content += f"<li>{recommendation}</li>"
    
    html_content += f"""
            </ul>
        </div>
        
        <div class="footer">
            <p><strong>⚠️ IMPORTANTE:</strong> Este relatório é gerado com auxílio de Inteligência Artificial.</p>
            <p>Sempre consulte um médico para interpretação completa.</p>
            <p>Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

# ============================================================================
# ENDPOINTS ORIGINAIS MANTIDOS
# ============================================================================

@app.get("/api/health")
async def health_check():
    """🔍 Verificação de saúde do sistema"""
    
    health = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0 - With LLM Analysis',
        'services': {}
    }
    
    # Verificar OpenAI Whisper
    health['services']['transcription'] = {
        'service': 'OpenAI Whisper API',
        'available': transcription_service.client is not None,
        'api_key_configured': bool(settings.OPENAI_API_KEY)
    }
    
    # Verificar AWS Textract
    health['services']['textract'] = {
        'service': 'AWS Textract',
        'available': textract_service.client is not None,
        'region': settings.AWS_REGION,
        'credentials_configured': bool(settings.AWS_ACCESS_KEY_ID)
    }
    
    # Verificar LLM
    health['services']['llm_analysis'] = {
        'service': 'OpenAI GPT for Medical Analysis',
        'available': bool(settings.OPENAI_API_KEY),
        'features': ['Clinical analysis', 'Risk assessment', 'Personalized recommendations']
    }
    
    health['dependencies'] = {
        'pdf2image': PDF2IMAGE_AVAILABLE,
        'opencv': True,
        'boto3': True,
        'openai': True
    }
    
    return health

@app.get("/api/system-status")
async def system_status():
    """ Status detalhado do sistema"""
    
    return {
        'system': 'Enhanced Medical Analysis System with LLM',
        'version': '2.0',
        'components': {
            'transcription': {
                'service': 'OpenAI Whisper API',
                'status': ' Ready' if transcription_service.client else '❌ Not configured',
                'supported_formats': ['mp3', 'mp4', 'wav', 'webm', 'm4a'],
                'features': ['Portuguese language', 'Medical context prompts', 'High accuracy']
            },
            'text_extraction': {
                'service': 'AWS Textract',
                'status': 'Ready' if textract_service.client else '❌ Not configured',
                'supported_formats': list(textract_service.supported_formats),
                'features': ['PDF multi-page', 'Image preprocessing', 'Medical content detection']
            },
            'llm_analysis': {
                'service': 'OpenAI GPT for Medical Analysis',
                'status': 'Ready' if settings.OPENAI_API_KEY else '❌ Not configured',
                'features': [
                    ' Clinical interpretation',
                    '⚠️ Risk assessment',
                    ' Personalized recommendations',
                    ' Clear patient summaries',
                    'HTML reports'
                ]
            }
        },
        'endpoints': {
            'original': {
                'main_analysis': 'POST /api/intelligent-medical-analysis',
                'health': 'GET /api/health',
                'status': 'GET /api/system-status'
            },
            'new_llm': {
                'llm_analysis': 'POST /api/analyze-exam-with-llm',
                'html_report': 'GET /api/exam-report-html/{exam_id}'
            }
        },
        'configuration': {
            'openai_api_key': '✅ Configured' if settings.OPENAI_API_KEY else '❌ Missing',
            'aws_credentials': '✅ Configured' if settings.AWS_ACCESS_KEY_ID else '❌ Missing',
            'aws_region': settings.AWS_REGION
        },
        'new_features': [
            '✅ Análise clínica com LLM',
            '✅ Avaliação de risco personalizada',
            '✅ Recomendações adaptadas',
            '✅ Relatórios HTML profissionais',
            '✅ Resumos em linguagem clara',
            '✅ Fallback para análise básica'
        ]
    }

@app.get("/")
async def root():
    """ Página inicial"""
    
    return {
        'message': 'Enhanced Medical Analysis System with LLM',
        'version': '2.0',
        'description': 'Sistema integrado com transcrição, extração e análise LLM',
        'features': [
            'OpenAI Whisper API para transcrição',
            'AWS Textract para extração de exames',
            ' Análise inteligente com LLM',
            'Avaliação de risco automática',
            ' Recomendações personalizadas',
            'Relatórios HTML profissionais'
        ],
        'endpoints': {
            'original_main': 'POST /api/intelligent-medical-analysis',
            'new_llm_analysis': 'POST /api/analyze-exam-with-llm',
            'html_report': 'GET /api/exam-report-html/{exam_id}',
            'health': 'GET /api/health',
            'status': 'GET /api/system-status'
        },
        'ready': {
            'transcription': transcription_service.client is not None,
            'textract': textract_service.client is not None,
            'llm_analysis': bool(settings.OPENAI_API_KEY)
        }
    }

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting Enhanced Medical System with LLM")
    print("=" * 60)
    
    print(" CONFIGURAÇÕES:")
    print(f" OpenAI Whisper: {' Ready' if transcription_service.client else '❌ Check OPENAI_API_KEY'}")
    print(f" AWS Textract: {' Ready' if textract_service.client else '❌ Check AWS credentials'}")
    print(f" LLM Analysis: {' Ready' if settings.OPENAI_API_KEY else '❌ Check OPENAI_API_KEY'}")
    
    if settings.OPENAI_API_KEY:
        print(f"   API Key: {settings.OPENAI_API_KEY[:10]}...{settings.OPENAI_API_KEY[-4:]}")
    
    print()
    print(" NOVOS RECURSOS:")
    print("   Análise clínica inteligente com LLM")
    print("   Avaliação de risco personalizada")
    print("    Recomendações adaptadas ao paciente")
    print("    Relatórios HTML profissionais")
    print("    Resumos em linguagem clara")
    
    print()
    print("🌐 ENDPOINTS DISPONÍVEIS:")
    print("    Original: POST http://localhost:8000/api/intelligent-medical-analysis")
    print("    Novo LLM: POST http://localhost:8000/api/analyze-exam-with-llm")
    print("    Relatório: GET http://localhost:8000/api/exam-report-html/123")
    print("    Health: GET http://localhost:8000/api/health")
    print("    Status: GET http://localhost:8000/api/system-status")
    
    print()
    print(" COMO USAR:")
    print("   1. Use endpoint original para compatibilidade")
    print("   2. Use /analyze-exam-with-llm para análise inteligente")
    print("   3. Inclua idade/sexo do paciente para melhor análise")
    print("   4. Gere relatórios HTML para apresentação")
    
    if not settings.OPENAI_API_KEY:
        print()
        print("⚠️  Configure OPENAI_API_KEY para usar análise LLM")
    
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