"""
AWS Textract Service - Serviço básico para extrair texto de documentos
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AWSTextractService:
    """Serviço AWS Textract para extração de texto"""
    
    def __init__(self):
        self.available = False
        self.client = None
        
        try:
            import boto3
            
        
            aws_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
            aws_region = os.getenv('AWS_REGION', 'us-east-1')
            
            if aws_key and aws_secret:
                self.client = boto3.client(
                    'textract',
                    aws_access_key_id=aws_key,
                    aws_secret_access_key=aws_secret,
                    region_name=aws_region
                )
                self.available = True
                logger.info("✅ AWS Textract Service inicializado")
            else:
                logger.warning("⚠️ Credenciais AWS não configuradas")
                
        except ImportError:
            logger.warning("⚠️ boto3 não instalado - pip install boto3")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Textract: {e}")
    
    async def extract_text_from_document(self, file_path: str) -> Dict[str, Any]:
        """Extrair texto de documento usando AWS Textract"""
        
        if not self.available:
            return await self._fallback_extraction(file_path)
        
        try:
            # Ler arquivo
            with open(file_path, 'rb') as document:
                document_bytes = document.read()
            
            # Chamar Textract
            response = self.client.detect_document_text(
                Document={'Bytes': document_bytes}
            )
            
            # Extrair texto
            extracted_text = ""
            confidence_scores = []
            
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    extracted_text += block['Text'] + '\n'
                    confidence_scores.append(block['Confidence'])
            
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            return {
                'success': True,
                'service': 'AWS Textract',
                'extracted_text': extracted_text.strip(),
                'confidence': avg_confidence / 100,
                'blocks_processed': len(response['Blocks']),
                'lines_found': len([b for b in response['Blocks'] if b['BlockType'] == 'LINE'])
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no Textract: {e}")
            return await self._fallback_extraction(file_path)
    
    async def _fallback_extraction(self, file_path: str) -> Dict[str, Any]:
        """Extração alternativa quando Textract não está disponível"""
        
        try:
            # Tentar OCR com Tesseract se disponível
            try:
                import pytesseract
                from PIL import Image
                
                # Para imagens
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
                    image = Image.open(file_path)
                    text = pytesseract.image_to_string(image, lang='por')
                    
                    return {
                        'success': True,
                        'service': 'Tesseract OCR',
                        'extracted_text': text,
                        'confidence': 0.7
                    }
                    
            except ImportError:
                pass
            
            # Para PDFs, tentar PyPDF2
            if file_path.lower().endswith('.pdf'):
                try:
                    import PyPDF2
                    
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text()
                    
                    return {
                        'success': True,
                        'service': 'PyPDF2',
                        'extracted_text': text,
                        'confidence': 0.8
                    }
                    
                except ImportError:
                    pass
            
            # Fallback final
            return {
                'success': False,
                'service': 'No OCR Available',
                'extracted_text': f"[Arquivo não processado: {os.path.basename(file_path)}]",
                'confidence': 0.1,
                'message': 'Instale boto3 para AWS Textract ou pytesseract para OCR local'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'extracted_text': f"[Erro: {str(e)}]"
            }

class MedicalDocumentAnalyzer:
    """Analisador de documentos médicos"""
    
    def __init__(self):
        self.textract = AWSTextractService()
    
    async def analyze_medical_document(self, file_path: str) -> Dict[str, Any]:
        """Analisar documento médico completo"""
        
        # Extrair texto
        extraction_result = await self.textract.extract_text_from_document(file_path)
        
        if extraction_result['success']:
            # Análise médica básica
            text = extraction_result['extracted_text'].lower()
            
            medical_terms = ['paciente', 'exame', 'resultado', 'diagnóstico', 'medicamento', 'receita']
            medical_score = sum(1 for term in medical_terms if term in text) / len(medical_terms)
            
            extraction_result.update({
                'medical_analysis': {
                    'is_medical_document': medical_score > 0.3,
                    'medical_relevance_score': medical_score,
                    'document_type': self._detect_document_type(text),
                    'contains_patient_info': any(term in text for term in ['paciente', 'nome', 'idade']),
                    'contains_medications': any(term in text for term in ['medicamento', 'receita', 'prescrição']),
                    'contains_lab_results': any(term in text for term in ['resultado', 'exame', 'análise'])
                },
                'tables': [],  # Placeholder para tabelas
                'key_value_pairs': {}  # Placeholder para formulários
            })
        
        return extraction_result
    
    def _detect_document_type(self, text: str) -> str:
        """Detectar tipo de documento médico"""
        
        if any(term in text for term in ['receita', 'prescrição']):
            return 'receita_medica'
        elif any(term in text for term in ['hemograma', 'leucócitos', 'hemácias']):
            return 'hemograma'
        elif any(term in text for term in ['glicose', 'glicemia']):
            return 'exame_glicemia'
        elif any(term in text for term in ['raio-x', 'tomografia', 'ressonância']):
            return 'exame_imagem'
        else:
            return 'documento_medico_generico'
