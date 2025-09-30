# textract_service.py
import boto3
import asyncio
import logging
from typing import Dict, Tuple, List
import io
from PIL import Image
import fitz  # PyMuPDF
import os
import re

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

class ParagraphSeparator:
    """Classe para separar texto em parágrafos baseado em regras médicas"""
    
    @staticmethod
    def separar_paragrafos(texto: str) -> List[str]:
        """Separa texto em parágrafos usando regras específicas para documentos médicos"""
        
        if not texto or not texto.strip():
            return []
        
        # 1. Dividir por quebras de linha duplas (parágrafos tradicionais)
        paragrafos_br = re.split(r'\n\s*\n', texto)
        
        # 2. Dividir por palavras-chave médicas específicas
        palavras_chave_medicas = [
            r'\b(?:RESULTADO|Resultado|resultado)\s*:',
            r'\b(?:CONCLUSÃO|Conclusão|conclusão)\s*:',
            r'\b(?:DIAGNÓSTICO|Diagnóstico|diagnóstico)\s*:',
            r'\b(?:EXAME|Exame|exame)\s*:',
            r'\b(?:LAUDO|Laudo|laudo)\s*:',
            r'\b(?:OBSERVAÇÃO|Observação|observação)\s*:',
            r'\b(?:RECOMENDAÇÃO|Recomendação|recomendação)\s*:',
            r'\b(?:SINTOMAS|Sintomas|sintomas)\s*:',
            r'\b(?:HISTÓRICO|Histórico|histórico)\s*:',
            r'\b(?:TRATAMENTO|Tratamento|tratamento)\s*:',
            r'\b(?:MEDICAÇÃO|Medicação|medicação)\s*:',
            r'\b(?:PROGNÓSTICO|Prognóstico|prognóstico)\s*:'
        ]
        
        # Combinar todas as palavras-chave
        pattern_medico = '|'.join(palavras_chave_medicas)
        
        # 3. Dividir por pontos finais seguidos de maiúscula (novas frases importantes)
        pattern_pontuacao = r'\.\s+[A-Z]'
        
        # 4. Aplicar todas as regras de separação
        paragrafos_finais = []
        
        # Primeiro: separar por quebras duplas
        for paragrafo in paragrafos_br:
            if not paragrafo.strip():
                continue
                
            # Segundo: verificar se contém palavras-chave médicas
            if re.search(pattern_medico, paragrafo):
                # Dividir por palavras-chave médicas
                sub_paragrafos = re.split(pattern_medico, paragrafo)
                for i, sub_p in enumerate(sub_paragrafos):
                    if sub_p.strip():
                        if i > 0:  # Adicionar a palavra-chave de volta
                            # Encontrar a palavra-chave que causou a divisão
                            match = re.search(pattern_medico, paragrafo)
                            if match:
                                sub_p = match.group() + sub_p
                        paragrafos_finais.append(sub_p.strip())
            else:
                # Dividir por pontuação forte
                sub_paragrafos = re.split(pattern_pontuacao, paragrafo)
                for sub_p in sub_paragrafos:
                    if sub_p.strip():
                        paragrafos_finais.append(sub_p.strip())
        
        # 5. Limpar e filtrar parágrafos
        paragrafos_limpos = []
        for p in paragrafos_finais:
            p_limpo = p.strip()
            if len(p_limpo) > 10:  # Filtrar parágrafos muito pequenos
                paragrafos_limpos.append(p_limpo)
        
        # 6. Se não conseguiu separar bem, usar quebras simples como fallback
        if len(paragrafos_limpos) <= 1:
            linhas = texto.split('\n')
            paragrafos_limpos = []
            paragrafo_atual = []
            
            for linha in linhas:
                linha = linha.strip()
                if linha:
                    paragrafo_atual.append(linha)
                else:
                    if paragrafo_atual:
                        paragrafos_limpos.append(' '.join(paragrafo_atual))
                        paragrafo_atual = []
            
            # Adicionar último parágrafo
            if paragrafo_atual:
                paragrafos_limpos.append(' '.join(paragrafo_atual))
        
        logger.info(f"Texto separado em {len(paragrafos_limpos)} parágrafos")
        return paragrafos_limpos

class TextractService:
    """Extração de texto com AWS Textract - versão melhorada com suporte a PDF e separação por parágrafos"""
    
    def __init__(self):
        try:
            self.client = boto3.client(
                'textract',
                region_name=AWS_REGION
            )
            self.paragraph_separator = ParagraphSeparator()
            logger.info("AWS Textract configurado com separação por parágrafos")
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
        """Processa resposta do Textract com separação por parágrafos"""
        
        texto_extraido = ""
        confidence_scores = []
        
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                texto = block.get('Text', '')
                confidence = block.get('Confidence', 0)
                
                texto_extraido += texto + "\n"
                confidence_scores.append(confidence)
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # Separar texto em parágrafos
        paragrafos = self.paragraph_separator.separar_paragrafos(texto_extraido.strip())
        
        conversion_note = " (convertido de PDF)" if converted else ""
        logger.info(f"Texto extraído: {len(texto_extraido)} caracteres, confiança: {avg_confidence:.1f}%{conversion_note}")
        logger.info(f"Texto separado em {len(paragrafos)} parágrafos")
        
        return {
            'success': True,
            'extracted_text': texto_extraido.strip(),
            'paragrafos': paragrafos,
            'tamanho': len(texto_extraido),
            'confidence': avg_confidence,
            'converted_from_pdf': converted,
            'filename_processed': filename
        }
