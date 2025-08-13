

import os
import boto3
import cv2
import numpy as np
import io
import logging
from typing import Dict, Any, List
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from config.settings import settings

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

logger = logging.getLogger(__name__)

class TextractService:
    """Serviço AWS Textract para extração de texto"""
    
    def __init__(self):
        self.client = None
        self.supported_formats = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
        self._init_client()
    
    def _init_client(self):
        """Inicializa cliente AWS"""
        try:
            logger.info("Verificando credenciais AWS...")
            
            aws_access_key = settings.AWS_ACCESS_KEY_ID
            aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
            aws_region = settings.AWS_REGION
            
            logger.info(f"AWS_ACCESS_KEY_ID: {'Presente' if aws_access_key else 'Ausente'}")
            logger.info(f"AWS_SECRET_ACCESS_KEY: {'Presente' if aws_secret_key else 'Ausente'}")
            logger.info(f"AWS_REGION: {aws_region if aws_region else 'Ausente'}")
            
            if aws_access_key and aws_secret_key and aws_region:
                try:
                    logger.info("Tentando configuração AWS...")
                    session = boto3.Session(
                        aws_access_key_id=aws_access_key,
                        aws_secret_access_key=aws_secret_key,
                        region_name=aws_region
                    )
                    
                    self.client = session.client('textract')
                    
                    # Teste básico
                    caller_identity = session.client('sts').get_caller_identity()
                    logger.info("AWS Textract configurado com sucesso!")
                    logger.info(f"Account: {caller_identity.get('Account', 'N/A')}")
                    return
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    logger.error(f"Erro AWS: {error_code}")
                    
                except Exception as e:
                    logger.error(f"Erro inesperado: {e}")
            
            # Tentar configuração padrão
            try:
                logger.info("Tentando configuração padrão AWS...")
                session = boto3.Session()
                session.get_credentials()
                
                self.client = session.client('textract', region_name=aws_region or 'us-east-1')
                
                caller_identity = session.client('sts').get_caller_identity()
                logger.info("AWS configurado via perfil padrão!")
                return
                
            except (NoCredentialsError, PartialCredentialsError):
                logger.warning("Credenciais padrão não encontradas")
            except Exception as e:
                logger.error(f"Erro na configuração padrão: {e}")
            
            logger.error("Falha em todas as tentativas de configuração AWS")
            self.client = None
            
        except Exception as e:
            logger.error(f"Erro crítico na inicialização AWS: {e}")
            self.client = None
    
    async def extract_text(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Extrai texto de arquivo usando Textract"""
        
        if not self.client:
            return {
                'success': False,
                'extracted_text': '',
                'error': 'AWS Textract não configurado - verifique credenciais AWS'
            }
        
        try:
            logger.info(f"Processando arquivo: {filename} ({len(file_bytes)} bytes)")
            
            is_pdf = filename.lower().endswith('.pdf')
            all_text = ""
            all_confidences = []
            pages_processed = 0
            
            if is_pdf:
                # Processar PDF
                image_bytes_list = self._convert_pdf_to_images(file_bytes)
                
                if not image_bytes_list:
                    return {
                        'success': False,
                        'extracted_text': '',
                        'error': 'Falha na conversão do PDF'
                    }
                
                for i, img_bytes in enumerate(image_bytes_list):
                    logger.info(f"Processando página {i+1}/{len(image_bytes_list)}")
                    
                    processed_img = self._preprocess_image(img_bytes)
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
                # Processar imagem
                processed_img = self._preprocess_image(file_bytes)
                response = self.client.detect_document_text(Document={'Bytes': processed_img})
                
                for block in response.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        line_text = block.get('Text', '')
                        confidence = block.get('Confidence', 0)
                        
                        all_text += line_text + "\n"
                        all_confidences.append(confidence)
                
                pages_processed = 1
            
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
            
            result = {
                'success': True,
                'filename': filename,
                'extracted_text': all_text.strip(),
                'text_length': len(all_text.strip()),
                'avg_confidence': round(avg_confidence, 2),
                'pages_processed': pages_processed,
                'document_type': 'PDF' if is_pdf else 'Image',
                'service_used': 'AWS Textract'
            }
            
            logger.info(f"Extração concluída: {len(all_text)} chars, {pages_processed} páginas")
            return result
            
        except Exception as e:
            logger.error(f"Erro na extração: {e}")
            return {
                'success': False,
                'extracted_text': '',
                'error': str(e),
                'filename': filename,
                'service_used': 'AWS Textract'
            }
    
    def _convert_pdf_to_images(self, pdf_bytes: bytes) -> List[bytes]:
        """Converte PDF em imagens"""
        if not PDF2IMAGE_AVAILABLE:
            logger.error("pdf2image não disponível")
            return []
            
        try:
            images = convert_from_bytes(pdf_bytes, dpi=300)
            image_bytes_list = []
            
            for img in images:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                image_bytes_list.append(img_byte_arr.getvalue())
            
            logger.info(f"PDF convertido para {len(image_bytes_list)} imagens")
            return image_bytes_list
            
        except Exception as e:
            logger.error(f"Erro na conversão PDF: {e}")
            return []
    
    def _preprocess_image(self, image_bytes: bytes) -> bytes:
        """Pré-processa imagem para melhor OCR"""
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return image_bytes
            
            # Processamento básico
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray)
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            _, buffer = cv2.imencode('.png', thresh)
            return buffer.tobytes()
            
        except Exception as e:
            logger.warning(f"Pré-processamento falhou, usando original: {e}")
            return image_bytes
    
    def test_textract_connection(self) -> dict:
        """Testa conexão com Textract"""
        if not self.client:
            return {
                'success': False,
                'error': 'Cliente não inicializado'
            }
        
        try:
            # Criar um teste mínimo
            test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
            
            response = self.client.detect_document_text(
                Document={'Bytes': test_image}
            )
            
            return {
                'success': True,
                'response_id': response.get('DocumentMetadata', {}).get('Pages', 0)
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            return {
                'success': False,
                'error_code': error_code,
                'error_message': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_health_status(self) -> Dict:
        """Status de saúde do serviço"""
        return {
            'service': 'AWS Textract',
            'status': 'Ready' if self.client else 'Not configured',
            'supported_formats': list(self.supported_formats),
            'features': ['PDF multi-page', 'Image preprocessing', 'High accuracy OCR']
        }
    
    def get_status(self) -> str:
        """Status simples"""
        return "Ready" if self.client else "Not configured"
