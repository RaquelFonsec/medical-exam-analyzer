# ============================================================================
# MAIN.PY COMPLETA 
# ============================================================================

#
from dotenv import load_dotenv
import os


load_dotenv()

# Agora importar o resto
import logging
import asyncio
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional

# Core imports
import boto3
import openai
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn

# Novos imports para PDF
import fitz  # PyMuPDF
from PIL import Image

# ============================================================================
# CONFIGURAÇÃO LENDO .ENV
# ============================================================================

# Agora vai ler do .env que você configurou
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID') 
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Debug: Verificar se carregou as chaves
logger.info("VERIFICANDO CONFIGURAÇÕES DO .ENV:")
logger.info(f"OpenAI Key: {'CONFIGURADO' if OPENAI_API_KEY else 'MISSING'}")
logger.info(f"AWS Access Key: {'CONFIGURADO' if AWS_ACCESS_KEY_ID else 'MISSING'}")
logger.info(f"AWS Secret Key: {'CONFIGURADO' if AWS_SECRET_ACCESS_KEY else 'MISSING'}")
logger.info(f"AWS Region: {AWS_REGION}")

if OPENAI_API_KEY:
    logger.info(f"OpenAI Key Preview: {OPENAI_API_KEY[:15]}...{OPENAI_API_KEY[-8:]}")

# ============================================================================
# PDF CONVERTER PARA TEXTRACT
# ============================================================================

class PDFConverter:
    """Converte PDFs para imagens quando Textract falha"""
    
    @staticmethod
    async def convert_pdf_to_image(pdf_bytes: bytes, filename: str) -> tuple[bytes, str]:
        """
        Converte PDF para imagem PNG para usar com Textract
        
        Returns:
            tuple: (image_bytes, new_filename)
        """
        try:
            logger.info(f"Convertendo PDF para imagem: {filename}")
            
            # Abrir PDF com PyMuPDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Converter primeira página para imagem
            page = pdf_document[0]  # Primeira página
            
            # Renderizar em alta resolução
            matrix = fitz.Matrix(2.0, 2.0)  # 2x zoom para melhor qualidade
            pix = page.get_pixmap(matrix=matrix)
            
            # Converter para PNG
            img_data = pix.tobytes("png")
            
            # Limpar recursos
            pdf_document.close()
            
            # Novo nome do arquivo
            new_filename = filename.replace('.pdf', '_converted.png')
            
            logger.info(f"PDF convertido: {len(img_data)} bytes")
            
            return img_data, new_filename
            
        except Exception as e:
            logger.error(f"Erro na conversão PDF: {e}")
            raise Exception(f"Falha ao converter PDF: {e}")

# ============================================================================
# 1. TRANSCRIÇÃO COM WHISPER
# ============================================================================

class TranscricaoService:
    """Transcrição de áudio com Whisper"""
    
    def __init__(self):
        if OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
            logger.info("OpenAI Whisper configurado")
        else:
            self.client = None
            logger.error("OpenAI API Key não encontrada no .env")
    
    async def transcrever_audio(self, audio_bytes: bytes, filename: str) -> Dict:
        """Transcreve áudio para texto"""
        
        if not self.client:
            return {
                'sucesso': False,
                'erro': 'OpenAI API Key não configurada no arquivo .env',
                'transcricao': ''
            }
        
        try:
            logger.info(f"Transcrevendo áudio: {filename}")
            
            # Salvar temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_bytes)
                temp_path = tmp_file.name
            
            # Transcrever com Whisper
            with open(temp_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt",
                    response_format="text"
                )
            
            # Limpar arquivo temporário
            os.unlink(temp_path)
            
            transcricao = transcript if isinstance(transcript, str) else str(transcript)
            
            logger.info(f"Transcrição concluída: {len(transcricao)} caracteres")
            
            return {
                'sucesso': True,
                'transcricao': transcricao.strip(),
                'tamanho': len(transcricao)
            }
            
        except Exception as e:
            logger.error(f"Erro na transcrição: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'transcricao': ''
            }

# ============================================================================
# 2. EXTRAÇÃO COM TEXTRACT MELHORADA
# ============================================================================

class TextractService:
    """Extração de texto com AWS Textract - versão melhorada com suporte a PDF"""
    
    def __init__(self):
        try:
            self.client = boto3.client(
                'textract',
                region_name=AWS_REGION
            )
            logger.info("AWS Textract configurado")
        except Exception as e:
            logger.error(f"Erro ao configurar Textract: {e}")
            self.client = None
    
    async def extrair_texto(self, file_bytes: bytes, filename: str) -> Dict:
        """Extrai texto com fallback para conversão de PDF"""
        
        if not self.client:
            return {
                'success': False,
                'error': 'AWS Textract não configurado - verifique credenciais no .env',
                'extracted_text': ''
            }
        
        try:
            logger.info(f"Extraindo texto: {filename}")
            
            # PRIMEIRO: Tentar diretamente com Textract
            try:
                response = await asyncio.to_thread(
                    self.client.detect_document_text,
                    Document={'Bytes': file_bytes}
                )
                
                # Se chegou aqui, funcionou!
                return await self._processar_resposta_textract(response, filename)
                
            except Exception as textract_error:
                error_msg = str(textract_error)
                
                # Se é erro de formato não suportado E é PDF, tentar conversão
                if "UnsupportedDocumentException" in error_msg and filename.lower().endswith('.pdf'):
                    logger.warning(f"PDF não suportado diretamente, convertendo para imagem...")
                    
                    # Converter PDF para imagem
                    image_bytes, new_filename = await PDFConverter.convert_pdf_to_image(
                        file_bytes, filename
                    )
                    
                    # Tentar novamente com a imagem
                    response = await asyncio.to_thread(
                        self.client.detect_document_text,
                        Document={'Bytes': image_bytes}
                    )
                    
                    return await self._processar_resposta_textract(response, new_filename, converted=True)
                
                else:
                    # Outros erros, repassar
                    raise textract_error
            
        except Exception as e:
            logger.error(f"Erro na extração: {e}")
            return {
                'success': False,
                'error': str(e),
                'extracted_text': ''
            }
    
    async def _processar_resposta_textract(self, response: dict, filename: str, converted: bool = False) -> Dict:
        """Processa resposta do Textract"""
        
        texto_extraido = ""
        confidence_scores = []
        
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                texto = block.get('Text', '')
                confidence = block.get('Confidence', 0)
                
                texto_extraido += texto + "\n"
                confidence_scores.append(confidence)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        conversion_note = " (convertido de PDF)" if converted else ""
        logger.info(f"Texto extraído: {len(texto_extraido)} caracteres, confiança: {avg_confidence:.1f}%{conversion_note}")
        
        return {
            'success': True,
            'extracted_text': texto_extraido.strip(),
            'tamanho': len(texto_extraido),
            'confidence': avg_confidence,
            'converted_from_pdf': converted,
            'filename_processed': filename
        }

# ============================================================================
# 3. INTERPRETAÇÃO COM LLM - USANDO .ENV
# ============================================================================

class InterpretadorLLM:
    """Interpretação de exames com LLM"""
    
    def __init__(self):
        if OPENAI_API_KEY:
            self.client = openai.OpenAI(
                api_key=OPENAI_API_KEY,
                timeout=480.0,  # 8 minutos
                max_retries=3
            )
            logger.info("OpenAI LLM configurado")
        else:
            self.client = None
            logger.error("OpenAI API Key não encontrada para LLM")
    
    async def interpretar_exame_para_frontend(self, texto_extraido: str, nome_arquivo: str, patient_info: Dict = None) -> Dict:
        """Interpreta exame para ser compatível com o frontend"""
        
        if not self.client:
            return {
                'success': False,
                'error': 'OpenAI API Key não configurada no arquivo .env',
                'llm_analysis': {}
            }
        
        try:
            logger.info(f"Interpretando exame para frontend: {nome_arquivo}")
            
            # PROMPT OTIMIZADO PARA EXAMES
            prompt = f"""
INTERPRETAÇÃO DE EXAME CLÍNICO

ARQUIVO: {nome_arquivo}
TEXTO EXTRAÍDO DO EXAME:
{texto_extraido}

INFORMAÇÕES DO PACIENTE:
{patient_info.get('additional_info', 'Não informado') if patient_info else 'Não informado'}

INSTRUÇÕES PARA INTERPRETAÇÃO:
INTERPRETE os achados clínicos encontrados no exame
EXPLIQUE o significado clínico dos valores alterados
CORRELACIONE os resultados entre si
IDENTIFIQUE padrões e tendências
NÃO dê diagnósticos definitivos
NÃO prescreva medicamentos ou tratamentos
TERMINE OBRIGATORIAMENTE com "INTERPRETAÇÃO FINALIZADA"

ESTRUTURA OBRIGATÓRIA:

## 1. IDENTIFICAÇÃO DO EXAME
* Tipo de exame identificado
* Finalidade

## 2. PRINCIPAIS ACHADOS CLÍNICOS
* Valores alterados (aumentados/diminuídos)
* Achados qualitativos relevantes

## 3. INTERPRETAÇÃO TÉCNICA 
* Significado clínico dos valores alterados
* Contexto fisiopatológico

## 4. CORRELAÇÃO DOS RESULTADOS
* Como os diferentes achados se relacionam
* Padrões identificados nos resultados
* Consistência entre parâmetros

## 5. OBSERVAÇÕES IMPORTANTES
- Pontos técnicos relevantes
- Limitações da interpretação

## 6. CONSIDERAÇÕES FINAIS
- Síntese dos principais achados
- Relevância médico-legal

INTERPRETAÇÃO FINALIZADA
"""

            logger.info("Chamando OpenAI GPT-4o para interpretação...")
            
            # Chamar OpenAI com configuração robusta
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": """Você é um especialista em interpretação de exames clínicos e laboratoriais.
                            INTERPRETE tecnicamente os achados encontrados.
                            NÃO forneça diagnósticos definitivos.
                            NÃO prescreva tratamentos.
                            SEMPRE termine com 'INTERPRETAÇÃO FINALIZADA'.
                            Complete TODAS as seções solicitadas."""
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=16000,
                    temperature=0.2
                ),
                timeout=480  # 8 minutos
            )
            
            interpretacao = response.choices[0].message.content.strip()
            
            logger.info(f"Interpretação LLM concluída: {len(interpretacao)} caracteres")
            
            # Verificar se a interpretação está completa
            esta_completa = "INTERPRETAÇÃO FINALIZADA" in interpretacao
            
            if not esta_completa:
                logger.warning("Interpretação pode estar incompleta")
            
            # FORMATO COMPATÍVEL COM FRONTEND
            return {
                'success': True,
                'llm_analysis': {
                    'clinical_analysis': interpretacao,
                    'exam_type': self._identificar_tipo_exame(texto_extraido),
                    'key_findings': self._extrair_achados_principais(texto_extraido),
                    'overall_status': 'Interpretação técnica realizada - Consultar médico para avaliação completa'
                },
                'extracted_text': texto_extraido,
                'filename': nome_arquivo,
                'model_used': 'gpt-4o',
                'interpretation_complete': esta_completa,
                'processing_timestamp': datetime.now().isoformat()
            }
            
        except asyncio.TimeoutError:
            logger.error("Timeout na interpretação LLM (8 minutos)")
            return {
                'success': False,
                'error': 'Timeout na interpretação - documento muito complexo',
                'llm_analysis': {}
            }
        except Exception as e:
            logger.error(f"Erro na interpretação LLM: {e}")
            return {
                'success': False,
                'error': str(e),
                'llm_analysis': {}
            }
    
    def _identificar_tipo_exame(self, texto: str) -> str:
        """Identifica o tipo de exame baseado no conteúdo"""
        texto_lower = texto.lower()
        
        if any(palavra in texto_lower for palavra in ['hemograma', 'hemácias', 'leucócitos', 'plaquetas']):
            return 'Hemograma'
        elif any(palavra in texto_lower for palavra in ['glicose', 'colesterol', 'triglicérides', 'hdl', 'ldl']):
            return 'Bioquímica'
        elif any(palavra in texto_lower for palavra in ['urina', 'eas', 'sedimento']):
            return 'Urina'
        elif any(palavra in texto_lower for palavra in ['tsh', 't3', 't4', 'hormônio']):
            return 'Hormonal'
        else:
            return 'Exame Clínico'
    
    def _extrair_achados_principais(self, texto: str) -> list:
        """Extrai achados principais do texto"""
        import re
        
        achados = []
        linhas = texto.split('\n')
        
        # Padrões para identificar resultados de exames
        padroes = [
            r'([A-ZÀ-Ÿ][a-zà-ÿ\s]{3,})[:\s]+([0-9,\.]+)\s*([a-zA-Z\/³%μ]*)',
            r'(.*?):\s*([0-9,\.]+)',
            r'([A-ZÀ-Ÿ][a-zà-ÿ\s]+)\s+([0-9,\.]+)'
        ]
        
        for linha in linhas:
            linha = linha.strip()
            if len(linha) > 5 and ':' in linha:
                for padrao in padroes:
                    match = re.search(padrao, linha)
                    if match and len(achados) < 8:
                        achados.append(linha)
                        break
        
        return achados

# ============================================================================
# 4. SISTEMA INTEGRADO
# ============================================================================

class SistemaMedicoCompleto:
    """Sistema médico completo com .env configurado"""
    
    def __init__(self):
        self.transcricao = TranscricaoService()
        self.textract = TextractService()
        self.interpretador = InterpretadorLLM()
        
        # Log do status dos serviços
        logger.info("STATUS DOS SERVIÇOS APÓS INICIALIZAÇÃO:")
        logger.info(f"   Transcrição: {'OK' if self.transcricao.client else 'Erro'}")
        logger.info(f"   Textract: {'OK' if self.textract.client else 'Erro'}")
        logger.info(f"   LLM: {'OK' if self.interpretador.client else 'Erro'}")

# ============================================================================
# 5. API FASTAPI
# ============================================================================

app = FastAPI(
    title="Sistema Médico - Configurado via .env",
    description="Backend lendo todas as configurações do arquivo .env",
    version="1.0-env-complete-pdf"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Sistema global
sistema = SistemaMedicoCompleto()

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.post("/api/analyze-exam-with-llm")
async def analyze_exam_with_llm(
    file: UploadFile = File(...),
    patient_age: Optional[int] = Form(None),
    patient_gender: Optional[str] = Form(None),
    additional_info: Optional[str] = Form("")
):
    """
    ENDPOINT PRINCIPAL - Análise com Textract + LLM
    Lendo configurações do .env
    """
    
    try:
        logger.info(f"Análise LLM solicitada: {file.filename}")
        
        # Verificar se os serviços estão configurados
        if not sistema.textract.client:
            return {
                'success': False,
                'error': 'AWS Textract não configurado. Verifique as variáveis no .env: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY'
            }
        
        if not sistema.interpretador.client:
            return {
                'success': False,
                'error': 'OpenAI não configurado. Verifique a variável no .env: OPENAI_API_KEY'
            }
        
        # Verificar formato
        formatos_suportados = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']
        if not any(file.filename.lower().endswith(ext) for ext in formatos_suportados):
            return {
                'success': False,
                'error': f"Formato não suportado. Use: {', '.join(formatos_suportados)}"
            }
        
        # Ler arquivo
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            return {
                'success': False,
                'error': 'Arquivo vazio'
            }
        
        logger.info(f"Arquivo recebido: {len(file_bytes)} bytes")
        
        # Preparar informações do paciente
        patient_info = {}
        if patient_age:
            patient_info['age'] = patient_age
        if patient_gender:
            patient_info['gender'] = patient_gender
        if additional_info:
            patient_info['additional_info'] = additional_info
        
        # ETAPA 1: Extrair texto com Textract
        logger.info("Iniciando extração com Textract...")
        extracao_result = await sistema.textract.extrair_texto(file_bytes, file.filename)
        
        if not extracao_result['success']:
            return {
                'success': False,
                'error': f"Erro na extração Textract: {extracao_result['error']}"
            }
        
        texto_extraido = extracao_result['extracted_text']
        
        if not texto_extraido.strip():
            return {
                'success': False,
                'error': 'Nenhum texto foi extraído do documento'
            }
        
        logger.info(f"Textract concluído: {len(texto_extraido)} caracteres")
        
        # ETAPA 2: Interpretar com LLM
        logger.info("Iniciando interpretação com LLM...")
        interpretacao_result = await sistema.interpretador.interpretar_exame_para_frontend(
            texto_extraido, file.filename, patient_info
        )
        
        if interpretacao_result['success']:
            logger.info("Análise LLM concluída com SUCESSO!")
            return interpretacao_result
        else:
            logger.error(f"Erro na interpretação LLM: {interpretacao_result['error']}")
            return interpretacao_result
        
    except Exception as e:
        logger.error(f"Erro crítico na análise: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis(
    patient_info: str = Form(default=""),
    audio: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None)
):
    """Endpoint original - compatibilidade com frontend"""
    
    start_time = datetime.now()
    
    try:
        logger.info("Análise médica completa iniciada")
        
        result = {
            'success': True,
            'timestamp': start_time.isoformat(),
            'patient_info': patient_info,
            'transcription': '',
            'laudo_medico': '',
            'processing_details': {
                'audio_processed': False,
                'exam_processed': False
            }
        }
        
        # Processar áudio se fornecido
        if audio and audio.filename:
            logger.info(f"Processando áudio: {audio.filename}")
            audio_data = await audio.read()
            
            transcricao_result = await sistema.transcricao.transcrever_audio(audio_data, audio.filename)
            
            if transcricao_result['sucesso']:
                result['transcription'] = transcricao_result['transcricao']
                result['processing_details']['audio_processed'] = True
            else:
                result['transcription'] = f"Erro: {transcricao_result['erro']}"
        
        # Processar documento se fornecido
        if image and image.filename:
            logger.info(f"Processando documento: {image.filename}")
            image_data = await image.read()
            
            extracao_result = await sistema.textract.extrair_texto(image_data, image.filename)
            
            if extracao_result['success']:
                result['laudo_medico'] = extracao_result['extracted_text']
                result['processing_details']['exam_processed'] = True
            else:
                result['laudo_medico'] = f"Erro: {extracao_result['error']}"
        
        processing_time = (datetime.now() - start_time).total_seconds()
        result['processing_time_seconds'] = round(processing_time, 2)
        
        logger.info(f"Análise completa em {processing_time:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"Erro na análise completa: {e}")
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        )

@app.get("/api/health")
async def health_check():
    """Status do sistema lendo .env"""
    
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'configuration_source': '.env file',
        'environment_variables': {
            'openai_api_key': 'LOADED' if OPENAI_API_KEY else 'MISSING',
            'aws_access_key_id': 'LOADED' if AWS_ACCESS_KEY_ID else 'MISSING',
            'aws_secret_access_key': 'LOADED' if AWS_SECRET_ACCESS_KEY else 'MISSING',
            'aws_region': AWS_REGION
        },
        'services_status': {
            'transcricao': 'READY' if sistema.transcricao.client else 'NOT READY',
            'textract': 'READY' if sistema.textract.client else 'NOT READY', 
            'interpretacao_llm': 'READY' if sistema.interpretador.client else 'NOT READY'
        },
        'endpoints': {
            'principal_llm': 'POST /api/analyze-exam-with-llm',
            'completo': 'POST /api/intelligent-medical-analysis',
            'status': 'GET /api/health'
        },
        'new_features': {
            'pdf_conversion': 'AUTO - PDFs são convertidos para imagem se necessário',
            'supported_formats': ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']
        }
    }

@app.get("/")
async def root():
    """Página inicial com status das configurações do .env"""
    
    all_configured = bool(OPENAI_API_KEY and AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
    
    return {
        'sistema': 'Sistema Médico - Configurado via arquivo .env',
        'status': 'TOTALMENTE OPERACIONAL' if all_configured else 'CONFIGURAÇÃO PARCIAL',
        'dotenv_loaded': True,
        'configuracoes_env': {
            'openai_api_key': 'Configurado' if OPENAI_API_KEY else 'Missing',
            'aws_access_key_id': 'Configurado' if AWS_ACCESS_KEY_ID else 'Missing',
            'aws_secret_access_key': 'Configurado' if AWS_SECRET_ACCESS_KEY else 'Missing',
            'aws_region': AWS_REGION
        },
        'servicos_funcionais': {
            'whisper_transcription': bool(sistema.transcricao.client),
            'aws_textract': bool(sistema.textract.client),
            'openai_llm_interpretation': bool(sistema.interpretador.client)
        },
        'proximos_passos': [
            'Teste o upload do sangue.jpg',
            'Teste também PDFs - agora convertidos automaticamente!',
            'Textract extrai texto + LLM interpreta'
        ] if all_configured else [
            'Configure as chaves que estão faltando no arquivo .env',
            'Reinicie o sistema após configurar'
        ]
    }

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")