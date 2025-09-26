# textract_service.py
import boto3
import asyncio
import logging
from typing import Dict, Tuple
import io
from PIL import Image
import fitz  # PyMuPDF
import os

# Configurações
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

logger = logging.getLogger(__name__)

class PDFConverter:
    """Conversor de PDF para imagem quando Textract não suporta diretamente"""
    
    @staticmethod
    async def convert_pdf_to_image(pdf_bytes: bytes, filename: str) -> Tuple[bytes, str]:
        """Converte PDF para imagem PNG"""
        
        try:
            # Abrir PDF com PyMuPDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Converter primeira página para imagem
            page = pdf_document[0]
            
            # Renderizar em alta resolução
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom para melhor qualidade
            pix = page.get_pixmap(matrix=mat)
            
            # Converter para PIL Image
            img_data = pix.tobytes("png")
            
            pdf_document.close()
            
            # Novo nome do arquivo
            new_filename = filename.replace('.pdf', '_converted.png')
            
            logger.info(f"PDF convertido para imagem: {filename} -> {new_filename}")
            
            return img_data, new_filename
            
        except Exception as e:
            logger.error(f"Erro na conversão de PDF: {e}")
            raise Exception(f"Falha na conversão de PDF: {str(e)}")

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
