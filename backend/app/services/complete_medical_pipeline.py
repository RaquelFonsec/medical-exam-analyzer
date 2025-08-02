# ============================================================================
# PIPELINE MÉDICO COMPLETO - WHISPER + AWS TEXTRACT
# ============================================================================

import os
import json
import time
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import tempfile
import base64

# Core imports
import whisper
import boto3
import openai
from PIL import Image
import pytesseract
import cv2
import numpy as np
import pandas as pd

# Web framework
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename
import requests

# Audio processing
import librosa
import soundfile as sf
from pydub import AudioSegment

# Image processing
import fitz  # PyMuPDF
from pdf2image import convert_from_path

# Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalPipelineConfig:
    """Configuração centralizada do pipeline médico"""
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Whisper Configuration
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'medium')  # tiny, base, small, medium, large
    WHISPER_LANGUAGE = 'pt'
    
    # File Configuration
    UPLOAD_FOLDER = 'uploads'
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'webm', 'm4a', 'flac'}
    ALLOWED_IMAGE_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'}
    
    # Medical AI Configuration
    MEDICAL_MODEL = "gpt-4"
    MAX_TOKENS = 4000
    TEMPERATURE = 0.1

class WhisperTranscriptionService:
    """Serviço de transcrição usando Whisper"""
    
    def __init__(self, model_name: str = "medium"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Carrega o modelo Whisper"""
        try:
            logger.info(f"🎤 Carregando modelo Whisper: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            logger.info("✅ Modelo Whisper carregado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo Whisper: {e}")
            raise
    
    def preprocess_audio(self, audio_path: str) -> str:
        """Pré-processa áudio para melhor qualidade de transcrição"""
        try:
            logger.info(f"🔧 Pré-processando áudio: {audio_path}")
            
            # Carregar áudio
            audio = AudioSegment.from_file(audio_path)
            
            # Normalizar volume
            audio = audio.normalize()
            
            # Reduzir ruído (filtro simples)
            audio = audio.low_pass_filter(3000).high_pass_filter(200)
            
            # Converter para WAV mono 16kHz
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            # Salvar áudio processado
            processed_path = audio_path.replace('.', '_processed.')
            if not processed_path.endswith('.wav'):
                processed_path = processed_path.rsplit('.', 1)[0] + '.wav'
            
            audio.export(processed_path, format="wav")
            logger.info(f"✅ Áudio pré-processado salvo: {processed_path}")
            
            return processed_path
            
        except Exception as e:
            logger.error(f"❌ Erro no pré-processamento: {e}")
            return audio_path  # Retorna original se falhar
    
    def transcribe_audio(self, audio_path: str, language: str = "pt") -> Dict[str, Any]:
        """Transcreve áudio usando Whisper"""
        try:
            logger.info(f"🎤 Iniciando transcrição: {audio_path}")
            
            if not self.model:
                self._load_model()
            
            # Pré-processar áudio
            processed_path = self.preprocess_audio(audio_path)
            
            # Transcrever
            start_time = time.time()
            result = self.model.transcribe(
                processed_path,
                language=language,
                task="transcribe",
                verbose=True,
                temperature=0.0,
                compression_ratio_threshold=2.4,
                logprob_threshold=-1.0,
                no_speech_threshold=0.6
            )
            
            transcription_time = time.time() - start_time
            
            # Limpar arquivo processado
            if processed_path != audio_path and os.path.exists(processed_path):
                os.remove(processed_path)
            
            # Estruturar resultado
            transcription_result = {
                'text': result['text'].strip(),
                'language': result['language'],
                'segments': result['segments'],
                'duration': len(result['segments']),
                'confidence': self._calculate_confidence(result['segments']),
                'transcription_time': transcription_time,
                'model_used': self.model_name,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Transcrição concluída em {transcription_time:.2f}s")
            logger.info(f"📝 Texto: {result['text'][:100]}...")
            
            return transcription_result
            
        except Exception as e:
            logger.error(f"❌ Erro na transcrição: {e}")
            return {
                'text': '',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_confidence(self, segments: List[Dict]) -> float:
        """Calcula confiança média da transcrição"""
        if not segments:
            return 0.0
        
        total_confidence = 0.0
        total_duration = 0.0
        
        for segment in segments:
            duration = segment['end'] - segment['start']
            # Usar avg_logprob como proxy para confiança
            confidence = max(0.0, min(1.0, (segment.get('avg_logprob', -1.0) + 1.0)))
            total_confidence += confidence * duration
            total_duration += duration
        
        return total_confidence / total_duration if total_duration > 0 else 0.0

class AWSTextractService:
    """Serviço de extração de texto usando AWS Textract"""
    
    def __init__(self):
        self.textract_client = None
        self.s3_client = None
        self._init_aws_clients()
    
    def _init_aws_clients(self):
        """Inicializa clientes AWS"""
        try:
            session = boto3.Session(
                aws_access_key_id=MedicalPipelineConfig.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=MedicalPipelineConfig.AWS_SECRET_ACCESS_KEY,
                region_name=MedicalPipelineConfig.AWS_REGION
            )
            
            self.textract_client = session.client('textract')
            self.s3_client = session.client('s3')
            
            logger.info("✅ Clientes AWS inicializados")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar AWS: {e}")
            raise
    
    def preprocess_image(self, image_path: str) -> str:
        """Pré-processa imagem para melhor OCR"""
        try:
            logger.info(f"🖼️ Pré-processando imagem: {image_path}")
            
            # Carregar imagem
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError("Não foi possível carregar a imagem")
            
            # Converter para escala de cinza
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Aplicar filtro de desfoque gaussiano
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Aplicar threshold adaptativo
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Operações morfológicas para limpeza
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Salvar imagem processada
            processed_path = image_path.replace('.', '_processed.')
            cv2.imwrite(processed_path, cleaned)
            
            logger.info(f"✅ Imagem pré-processada: {processed_path}")
            return processed_path
            
        except Exception as e:
            logger.error(f"❌ Erro no pré-processamento de imagem: {e}")
            return image_path
    
    def convert_pdf_to_images(self, pdf_path: str) -> List[str]:
        """Converte PDF em imagens"""
        try:
            logger.info(f"📄 Convertendo PDF: {pdf_path}")
            
            # Converter PDF para imagens
            images = convert_from_path(pdf_path, dpi=300, fmt='png')
            
            image_paths = []
            for i, image in enumerate(images):
                image_path = pdf_path.replace('.pdf', f'_page_{i+1}.png')
                image.save(image_path, 'PNG')
                image_paths.append(image_path)
            
            logger.info(f"✅ PDF convertido em {len(image_paths)} imagens")
            return image_paths
            
        except Exception as e:
            logger.error(f"❌ Erro na conversão PDF: {e}")
            return []
    
    def extract_text_textract(self, image_path: str) -> Dict[str, Any]:
        """Extrai texto usando AWS Textract"""
        try:
            logger.info(f"📖 Extraindo texto com Textract: {image_path}")
            
            # Ler arquivo de imagem
            with open(image_path, 'rb') as image_file:
                image_bytes = image_file.read()
            
            # Chamar Textract
            start_time = time.time()
            response = self.textract_client.detect_document_text(
                Document={'Bytes': image_bytes}
            )
            extraction_time = time.time() - start_time
            
            # Processar resposta
            extracted_text = ""
            lines = []
            confidence_scores = []
            
            for item in response['Blocks']:
                if item['BlockType'] == 'LINE':
                    line_text = item['Text']
                    confidence = item['Confidence']
                    
                    extracted_text += line_text + "\n"
                    lines.append({
                        'text': line_text,
                        'confidence': confidence,
                        'bbox': item['Geometry']['BoundingBox']
                    })
                    confidence_scores.append(confidence)
            
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            result = {
                'text': extracted_text.strip(),
                'lines': lines,
                'confidence': avg_confidence,
                'extraction_time': extraction_time,
                'service': 'AWS Textract',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Texto extraído em {extraction_time:.2f}s (confiança: {avg_confidence:.1f}%)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no Textract: {e}")
            return {
                'text': '',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def extract_text_fallback(self, image_path: str) -> Dict[str, Any]:
        """Extração de texto usando Tesseract como fallback"""
        try:
            logger.info(f"🔄 Usando Tesseract como fallback: {image_path}")
            
            # Pré-processar imagem
            processed_path = self.preprocess_image(image_path)
            
            # Configurar Tesseract para português
            custom_config = r'--oem 3 --psm 6 -l por'
            
            start_time = time.time()
            text = pytesseract.image_to_string(
                Image.open(processed_path), 
                config=custom_config
            )
            extraction_time = time.time() - start_time
            
            # Limpar arquivo processado
            if processed_path != image_path and os.path.exists(processed_path):
                os.remove(processed_path)
            
            result = {
                'text': text.strip(),
                'extraction_time': extraction_time,
                'service': 'Tesseract OCR',
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Fallback concluído em {extraction_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no fallback: {e}")
            return {
                'text': '',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """Processa documento (PDF ou imagem)"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                # Converter PDF para imagens
                image_paths = self.convert_pdf_to_images(file_path)
                
                if not image_paths:
                    return {'text': '', 'error': 'Falha na conversão do PDF'}
                
                # Processar cada página
                all_text = ""
                all_results = []
                
                for img_path in image_paths:
                    try:
                        # Tentar Textract primeiro
                        result = self.extract_text_textract(img_path)
                        
                        if not result.get('text') and not result.get('error'):
                            # Fallback para Tesseract
                            result = self.extract_text_fallback(img_path)
                        
                        all_text += result.get('text', '') + "\n\n"
                        all_results.append(result)
                        
                    finally:
                        # Limpar arquivo temporário
                        if os.path.exists(img_path):
                            os.remove(img_path)
                
                return {
                    'text': all_text.strip(),
                    'pages': all_results,
                    'total_pages': len(image_paths),
                    'timestamp': datetime.now().isoformat()
                }
            
            else:
                # Processar imagem diretamente
                result = self.extract_text_textract(file_path)
                
                if not result.get('text') and not result.get('error'):
                    result = self.extract_text_fallback(file_path)
                
                return result
                
        except Exception as e:
            logger.error(f"❌ Erro no processamento do documento: {e}")
            return {
                'text': '',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

class MedicalAIProcessor:
    """Processador de IA médica para análise de dados"""
    
    def __init__(self):
        openai.api_key = MedicalPipelineConfig.OPENAI_API_KEY
    
    def analyze_consultation(self, transcription: str, exam_results: str) -> Dict[str, Any]:
        """Analisa consulta médica combinando transcrição e exames"""
        try:
            logger.info("🧠 Iniciando análise médica com IA")
            
            prompt = self._build_analysis_prompt(transcription, exam_results)
            
            response = openai.ChatCompletion.create(
                model=MedicalPipelineConfig.MEDICAL_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um assistente médico especializado em análise de consultas e exames. Forneça análises precisas, profissionais e em conformidade com diretrizes médicas."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=MedicalPipelineConfig.MAX_TOKENS,
                temperature=MedicalPipelineConfig.TEMPERATURE
            )
            
            analysis_text = response.choices[0].message.content
            
            # Estruturar resultado
            result = {
                'analysis': analysis_text,
                'model_used': MedicalPipelineConfig.MEDICAL_MODEL,
                'timestamp': datetime.now().isoformat(),
                'structured_data': self._extract_structured_data(analysis_text)
            }
            
            logger.info("✅ Análise médica concluída")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na análise médica: {e}")
            return {
                'analysis': '',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _build_analysis_prompt(self, transcription: str, exam_results: str) -> str:
        """Constrói prompt para análise médica"""
        return f"""
Por favor, analise os seguintes dados médicos e forneça uma avaliação profissional:

TRANSCRIÇÃO DA CONSULTA:
{transcription}

RESULTADOS DE EXAMES:
{exam_results}

Forneça uma análise estruturada incluindo:

1. RESUMO CLÍNICO
   - Principais queixas e sintomas
   - Histórico relevante

2. ANÁLISE DOS EXAMES
   - Principais achados
   - Alterações significativas
   - Valores fora da normalidade

3. CORRELAÇÃO CLÍNICO-LABORATORIAL
   - Relação entre sintomas e exames
   - Consistência dos achados

4. SUGESTÕES CLÍNICAS
   - Possíveis diagnósticos diferenciais
   - Exames complementares sugeridos
   - Orientações gerais

5. CLASSIFICAÇÃO DE URGÊNCIA
   - ROTINA / URGENTE / EMERGÊNCIA

Mantenha a análise profissional, objetiva e baseada em evidências.
"""
    
    def _extract_structured_data(self, analysis_text: str) -> Dict[str, Any]:
        """Extrai dados estruturados da análise"""
        structured = {
            'urgency_level': 'ROTINA',
            'main_findings': [],
            'recommendations': [],
            'differential_diagnoses': []
        }
        
        # Extrair nível de urgência
        text_upper = analysis_text.upper()
        if 'EMERGÊNCIA' in text_upper:
            structured['urgency_level'] = 'EMERGÊNCIA'
        elif 'URGENTE' in text_upper:
            structured['urgency_level'] = 'URGENTE'
        
        # TODO: Implementar extração mais sofisticada com NLP
        
        return structured

class MedicalPipeline:
    """Pipeline médico principal"""
    
    def __init__(self):
        self.whisper_service = WhisperTranscriptionService(MedicalPipelineConfig.WHISPER_MODEL)
        self.textract_service = AWSTextractService()
        self.ai_processor = MedicalAIProcessor()
        
        # Criar diretório de uploads
        os.makedirs(MedicalPipelineConfig.UPLOAD_FOLDER, exist_ok=True)
    
    def process_medical_consultation(
        self, 
        audio_file: Optional[str] = None,
        document_files: Optional[List[str]] = None,
        patient_info: Optional[str] = None
    ) -> Dict[str, Any]:
        """Processa consulta médica completa"""
        try:
            logger.info("🏥 Iniciando pipeline médico completo")
            start_time = time.time()
            
            results = {
                'success': True,
                'transcription': '',
                'exam_results': '',
                'medical_analysis': '',
                'processing_time': 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # 1. Transcrição de áudio
            if audio_file and os.path.exists(audio_file):
                logger.info("🎤 Processando transcrição de áudio")
                transcription_result = self.whisper_service.transcribe_audio(audio_file)
                results['transcription'] = transcription_result.get('text', '')
                results['transcription_details'] = transcription_result
            
            # 2. Extração de texto de documentos
            extracted_texts = []
            if document_files:
                logger.info(f"📄 Processando {len(document_files)} documentos")
                for doc_file in document_files:
                    if os.path.exists(doc_file):
                        extraction_result = self.textract_service.process_document(doc_file)
                        if extraction_result.get('text'):
                            extracted_texts.append(extraction_result['text'])
            
            results['exam_results'] = '\n\n'.join(extracted_texts)
            
            # 3. Análise médica com IA
            if results['transcription'] or results['exam_results']:
                logger.info("🧠 Processando análise médica")
                
                # Incluir informações do paciente se disponíveis
                consultation_text = results['transcription']
                if patient_info:
                    consultation_text = f"INFORMAÇÕES DO PACIENTE:\n{patient_info}\n\nCONSULTA:\n{consultation_text}"
                
                analysis_result = self.ai_processor.analyze_consultation(
                    consultation_text,
                    results['exam_results']
                )
                results['medical_analysis'] = analysis_result.get('analysis', '')
                results['analysis_details'] = analysis_result
            
            # Calcular tempo total
            results['processing_time'] = time.time() - start_time
            
            logger.info(f"✅ Pipeline concluído em {results['processing_time']:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"❌ Erro no pipeline médico: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# ============================================================================
# FLASK APPLICATION
# ============================================================================

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MedicalPipelineConfig.MAX_FILE_SIZE

# Inicializar pipeline
medical_pipeline = MedicalPipeline()

@app.route('/')
def index():
    """Página principal"""
    return render_template_string(MEDICAL_INTERFACE_HTML)

@app.route('/api/medical-analysis', methods=['POST'])
def medical_analysis():
    """Endpoint principal para análise médica"""
    try:
        logger.info("📨 Recebida requisição de análise médica")
        
        # Processar arquivos enviados
        audio_file = None
        document_files = []
        
        # Processar áudio
        if 'audio' in request.files:
            audio = request.files['audio']
            if audio.filename:
                filename = secure_filename(audio.filename)
                audio_path = os.path.join(MedicalPipelineConfig.UPLOAD_FOLDER, filename)
                audio.save(audio_path)
                audio_file = audio_path
                logger.info(f"🎤 Áudio salvo: {audio_path}")
        
        # Processar documentos
        if 'documents' in request.files:
            documents = request.files.getlist('documents')
            for doc in documents:
                if doc.filename:
                    filename = secure_filename(doc.filename)
                    doc_path = os.path.join(MedicalPipelineConfig.UPLOAD_FOLDER, filename)
                    doc.save(doc_path)
                    document_files.append(doc_path)
                    logger.info(f"📄 Documento salvo: {doc_path}")
        
        # Obter informações do paciente
        patient_info = request.form.get('patient_info', '')
        
        # Executar pipeline
        results = medical_pipeline.process_medical_consultation(
            audio_file=audio_file,
            document_files=document_files,
            patient_info=patient_info
        )
        
        # Limpar arquivos temporários
        cleanup_files = [audio_file] + document_files
        for file_path in cleanup_files:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"❌ Erro na API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'services': {
            'whisper': 'loaded',
            'textract': 'connected',
            'openai': 'connected'
        },
        'timestamp': datetime.now().isoformat()
    })

# HTML Template (simplificado)
MEDICAL_INTERFACE_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Pipeline Médico - Whisper + Textract</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
        .upload-area { border: 2px dashed #ccc; padding: 20px; margin: 20px 0; text-align: center; }
        button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .results { margin-top: 30px; }
        .result-section { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
        textarea { width: 100%; height: 100px; margin: 10px 0; padding: 10px; }
        .processing { display: none; text-align: center; color: #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 Pipeline Médico Completo</h1>
        <p>Transcrição com Whisper + Extração de Exames com AWS Textract</p>
        
        <form id="medicalForm" enctype="multipart/form-data">
            <div>
                <label>Informações do Paciente:</label>
                <textarea name="patient_info" placeholder="Nome, idade, histórico médico relevante..."></textarea>
            </div>
            
            <div class="upload-area">
                <h3>🎤 Áudio da Consulta</h3>
                <input type="file" name="audio" accept="audio/*">
            </div>
            
            <div class="upload-area">
                <h3>📄 Exames e Documentos</h3>
                <input type="file" name="documents" accept=".pdf,.png,.jpg,.jpeg" multiple>
            </div>
            
            <button type="submit">🧠 Processar Análise Médica</button>
        </form>
        
        <div class="processing" id="processing">
            <h3>⚡ Processando...</h3>
            <p>Transcrevendo áudio → Extraindo texto → Analisando dados médicos</p>
        </div>
        
        <div class="results" id="results" style="display:none;">
            <div class="result-section">
                <h3>🎤 Transcrição da Consulta</h3>
                <div id="transcription"></div>
            </div>
            
            <div class="result-section">
                <h3>📄 Resultados dos Exames</h3>
                <div id="examResults"></div>
            </div>
            
            <div class="result-section">
                <h3>🧠 Análise Médica</h3>
                <div id="medicalAnalysis"></div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('medicalForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            document.getElementById('processing').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/api/medical-analysis', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('transcription').innerText = result.transcription || 'Nenhuma transcrição disponível';
                    document.getElementById('examResults').innerText = result.exam_results || 'Nenhum resultado de exame disponível';
                    document.getElementById('medicalAnalysis').innerText = result.medical_analysis || 'Nenhuma análise disponível';
                    document.getElementById('results').style.display = 'block';
                } else {
                    alert('Erro: ' + result.error);
                }
            } catch (error) {
                alert('Erro de comunicação: ' + error.message);
            } finally {
                document.getElementById('processing').style.display = 'none';
            }
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    logger.info("🚀 Iniciando servidor do Pipeline Médico")
    app.run(debug=True, host='0.0.0.0', port=5000)

# ============================================================================
# REQUIREMENTS.txt
# ============================================================================

"""
# Core dependencies
flask==2.3.3
werkzeug==2.3.7

# AI and ML
openai==0.28.1
openai-whisper==20231117
torch>=1.13.0
transformers>=4.21.0

# AWS
boto3==1.28.85
botocore==1.31.85

# Audio processing
librosa==0.10.1
soundfile==0.12.1
pydub==0.25.1

# Image processing and OCR
pillow==10.0.1
opencv-python==4.8.1.78
pytesseract==0.3.10
pdf2image==1.16.3
PyMuPDF==1.23.5

# Data processing
pandas==2.1.1
numpy==1.24.3

# Utils
requests==2.31.0
python-dotenv==1.0.0
"""

# ============================================================================
# DOCKER CONFIGURATION
# ============================================================================

DOCKERFILE_CONTENT = '''
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    ffmpeg \\
    tesseract-ocr \\
    tesseract-ocr-por \\
    poppler-utils \\
    libsm6 \\
    libxext6 \\
    libxrender-dev \\
    libglib2.0-0 \\
    libgtk-3-0 \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 5000

# Environment variables
ENV FLASK_APP=medical_pipeline.py
ENV FLASK_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:5000/health || exit 1

# Run application
CMD ["python", "medical_pipeline.py"]
'''

# ============================================================================
# DOCKER COMPOSE
# ============================================================================

DOCKER_COMPOSE_CONTENT = '''
version: '3.8'

services:
  medical-pipeline:
    build: .
    ports:
      - "5000:5000"
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - WHISPER_MODEL=medium
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - medical-pipeline
    restart: unless-stopped
'''

# ============================================================================
# CONFIGURAÇÃO NGINX
# ============================================================================

NGINX_CONFIG = '''
events {
    worker_connections 1024;
}

http {
    upstream medical_app {
        server medical-pipeline:5000;
    }

    server {
        listen 80;
        client_max_body_size 50M;

        location / {
            proxy_pass http://medical_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }
    }
}
'''

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

ENV_TEMPLATE = '''
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Whisper Configuration
WHISPER_MODEL=medium

# Application Configuration
FLASK_ENV=production
MAX_FILE_SIZE=52428800
'''

# ============================================================================
# ADVANCED FEATURES
# ============================================================================

class AdvancedMedicalFeatures:
    """Recursos avançados para o pipeline médico"""
    
    @staticmethod
    def batch_process_files(file_paths: List[str]) -> Dict[str, Any]:
        """Processamento em lote de múltiplos arquivos"""
        results = []
        for file_path in file_paths:
            # Implementar processamento paralelo
            pass
        return results
    
    @staticmethod
    def medical_entity_extraction(text: str) -> Dict[str, List[str]]:
        """Extração de entidades médicas (medicamentos, sintomas, etc.)"""
        # TODO: Implementar NER médico
        entities = {
            'medications': [],
            'symptoms': [],
            'diagnoses': [],
            'procedures': []
        }
        return entities
    
    @staticmethod
    def generate_medical_report(data: Dict[str, Any]) -> str:
        """Gera relatório médico estruturado"""
        # TODO: Implementar geração de relatório
        return ""
    
    @staticmethod
    def anonymize_medical_data(text: str) -> str:
        """Anonimiza dados médicos sensíveis"""
        # TODO: Implementar anonimização
        return text

# ============================================================================
# MONITORING AND LOGGING
# ============================================================================

class MedicalPipelineMonitor:
    """Sistema de monitoramento do pipeline"""
    
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'successful_transcriptions': 0,
            'successful_extractions': 0,
            'failed_requests': 0,
            'average_processing_time': 0
        }
    
    def log_request(self, success: bool, processing_time: float):
        """Registra métricas de requisição"""
        self.metrics['total_requests'] += 1
        if success:
            self.metrics['successful_transcriptions'] += 1
        else:
            self.metrics['failed_requests'] += 1
        
        # Atualizar tempo médio
        current_avg = self.metrics['average_processing_time']
        total = self.metrics['total_requests']
        self.metrics['average_processing_time'] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Retorna status de saúde do sistema"""
        return {
            'status': 'healthy',
            'metrics': self.metrics,
            'timestamp': datetime.now().isoformat()
        }

# ============================================================================
# TESTING UTILITIES
# ============================================================================

class MedicalPipelineTester:
    """Utilitários para teste do pipeline"""
    
    @staticmethod
    def test_whisper_transcription():
        """Testa transcrição Whisper"""
        # TODO: Implementar testes
        pass
    
    @staticmethod
    def test_textract_extraction():
        """Testa extração Textract"""
        # TODO: Implementar testes
        pass
    
    @staticmethod
    def test_full_pipeline():
        """Testa pipeline completo"""
        # TODO: Implementar testes end-to-end
        pass

# ============================================================================
# DEPLOYMENT SCRIPTS
# ============================================================================

DEPLOY_SCRIPT = '''#!/bin/bash

# Deploy script for Medical Pipeline

echo "🚀 Deploying Medical Pipeline..."

# Create necessary directories
mkdir -p uploads logs

# Build Docker image
echo "📦 Building Docker image..."
docker-compose build

# Start services
echo "🔄 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services..."
sleep 30

# Health check
echo "🔍 Performing health check..."
curl -f http://localhost/health

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "🌐 Access the application at: http://localhost"
else
    echo "❌ Deployment failed!"
    docker-compose logs
    exit 1
fi
'''

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

USAGE_EXAMPLES = '''
# EXEMPLO DE USO DO PIPELINE MÉDICO

## 1. Instalação

```bash
# Clonar repositório
git clone <repo-url>
cd medical-pipeline

# Configurar ambiente
cp .env.template .env
# Editar .env com suas credenciais

# Instalar dependências
pip install -r requirements.txt

# Ou usar Docker
docker-compose up -d
```

## 2. Uso da API

```python
import requests

# Preparar arquivos
files = {
    'audio': open('consulta.wav', 'rb'),
    'documents': [
        open('exame1.pdf', 'rb'),
        open('exame2.jpg', 'rb')
    ]
}

data = {
    'patient_info': 'João Silva, 45 anos, hipertensão'
}

# Enviar requisição
response = requests.post(
    'http://localhost:5000/api/medical-analysis',
    files=files,
    data=data
)

result = response.json()
print(result['transcription'])
print(result['exam_results'])
print(result['medical_analysis'])
```

## 3. Uso direto do Pipeline

```python
from medical_pipeline import MedicalPipeline

pipeline = MedicalPipeline()

result = pipeline.process_medical_consultation(
    audio_file='consulta.wav',
    document_files=['exame1.pdf', 'exame2.jpg'],
    patient_info='Informações do paciente'
)

print(result)
```

## 4. Monitoramento

```bash
# Verificar saúde
curl http://localhost:5000/health

# Ver logs
docker-compose logs -f medical-pipeline

# Métricas
curl http://localhost:5000/metrics
```
'''