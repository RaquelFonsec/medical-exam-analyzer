import boto3
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
import asyncio
from datetime import datetime

class AWSTextractService:
    """
    Serviço AWS Textract para OCR avançado
    Muito superior ao Tesseract - extrai tabelas, formulários e texto estruturado
    """
    
    def __init__(self):
        """Inicializar AWS Textract com configurações"""
        print("🚀 Inicializando AWS Textract Service...")
        
        try:
            # Configurar credenciais AWS
            self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
            self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            
            # Inicializar cliente Textract
            if self.aws_access_key and self.aws_secret_key:
                self.textract = boto3.client(
                    'textract',
                    region_name=self.aws_region,
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key
                )
                print("✅ AWS Textract configurado com credenciais personalizadas")
            else:
                # Usar credenciais padrão (IAM role, ~/.aws/credentials, etc.)
                self.textract = boto3.client('textract', region_name=self.aws_region)
                print("✅ AWS Textract configurado com credenciais padrão")
            
            # Testar conectividade
            self._test_connection()
            
        except NoCredentialsError:
            print("❌ Erro: Credenciais AWS não encontradas")
            self.textract = None
        except Exception as e:
            print(f"❌ Erro inicializando AWS Textract: {str(e)}")
            self.textract = None
    
    def _test_connection(self):
        """Testar conexão com AWS Textract"""
        try:
            # Fazer uma chamada simples para testar
            response = self.textract.get_document_text_detection(JobId='test')
        except ClientError as e:
            # Esperado - JobId inválido, mas confirma que a conexão funciona
            if e.response['Error']['Code'] == 'InvalidJobIdException':
                print("✅ Conexão AWS Textract testada com sucesso")
            else:
                print(f"⚠️ Aviso na conexão AWS: {e.response['Error']['Code']}")
        except Exception as e:
            print(f"⚠️ Teste de conexão: {str(e)}")
    
    async def extract_text_from_document(self, file_path: str) -> Dict[str, Any]:
        """
        Extrair texto avançado com AWS Textract
        Muito mais preciso que Tesseract - detecta tabelas e formulários
        """
        
        if not self.textract:
            return await self._fallback_to_tesseract(file_path)
        
        try:
            print(f"📄 Processando com AWS Textract: {os.path.basename(file_path)}")
            
            # Ler arquivo
            with open(file_path, 'rb') as document:
                document_bytes = document.read()
            
            print(f"📊 Tamanho do arquivo: {len(document_bytes)} bytes")
            
            # Verificar tamanho (limite AWS: 10MB)
            if len(document_bytes) > 10 * 1024 * 1024:
                print("⚠️ Arquivo muito grande para Textract (>10MB), usando fallback")
                return await self._fallback_to_tesseract(file_path)
            
            # Chamar Textract com análise completa
            print("🔍 Analisando documento com Textract...")
            response = self.textract.analyze_document(
                Document={'Bytes': document_bytes},
                FeatureTypes=['TABLES', 'FORMS']  # Extrair tabelas e formulários
            )
            
            print(f"✅ Textract processou {len(response['Blocks'])} blocos")
            
            # Processar resposta
            extracted_data = self._process_textract_response(response)
            
            # Calcular métricas
            extraction_metrics = self._calculate_extraction_metrics(response, extracted_data)
            
            return {
                "success": True,
                "service": "AWS Textract",
                "file_processed": os.path.basename(file_path),
                "timestamp": datetime.now().isoformat(),
                
                # Conteúdo extraído
                "extracted_text": extracted_data['text'],
                "tables": extracted_data['tables'],
                "forms": extracted_data['forms'],
                "key_value_pairs": extracted_data['key_value_pairs'],
                
                # Métricas de qualidade
                "confidence": extraction_metrics['average_confidence'],
                "blocks_processed": extraction_metrics['total_blocks'],
                "words_extracted": extraction_metrics['word_count'],
                "lines_extracted": extraction_metrics['line_count'],
                "tables_found": len(extracted_data['tables']),
                "forms_found": len(extracted_data['forms']),
                
                # Dados brutos para debug
                "raw_response": response if os.getenv('DEBUG_TEXTRACT') == 'true' else None
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"❌ Erro AWS Textract ({error_code}): {e.response['Error']['Message']}")
            
            # Fallback para Tesseract em caso de erro AWS
            print("🔄 Usando fallback Tesseract...")
            return await self._fallback_to_tesseract(file_path)
            
        except Exception as e:
            print(f"❌ Erro inesperado AWS Textract: {str(e)}")
            return await self._fallback_to_tesseract(file_path)
    
    def _process_textract_response(self, response: Dict) -> Dict[str, Any]:
        """Processar resposta do Textract de forma estruturada"""
        
        extracted_data = {
            'text': "",
            'tables': [],
            'forms': [],
            'key_value_pairs': {}
        }
        
        # Organizar blocos por tipo
        blocks_by_id = {block['Id']: block for block in response['Blocks']}
        
        # 1. EXTRAIR TEXTO LINHA POR LINHA
        lines = []
        for block in response['Blocks']:
            if block['BlockType'] == 'LINE':
                line_text = block.get('Text', '')
                lines.append({
                    'text': line_text,
                    'confidence': block.get('Confidence', 0),
                    'geometry': block.get('Geometry', {})
                })
        
        extracted_data['text'] = '\n'.join([line['text'] for line in lines])
        
        # 2. PROCESSAR TABELAS
        for block in response['Blocks']:
            if block['BlockType'] == 'TABLE':
                table_data = self._extract_table_data(block, blocks_by_id)
                if table_data:
                    extracted_data['tables'].append(table_data)
        
        # 3. PROCESSAR FORMULÁRIOS (KEY-VALUE PAIRS)
        key_value_pairs = self._extract_key_value_pairs(response['Blocks'], blocks_by_id)
        extracted_data['forms'] = [{'key_value_pairs': key_value_pairs}]
        extracted_data['key_value_pairs'] = key_value_pairs
        
        return extracted_data
    
    def _extract_table_data(self, table_block: Dict, blocks_by_id: Dict) -> Optional[Dict]:
        """Extrair dados estruturados de tabela"""
        
        try:
            table_data = {
                'table_id': table_block.get('Id', ''),
                'confidence': table_block.get('Confidence', 0),
                'rows': [],
                'headers': [],
                'cell_count': 0
            }
            
            # Obter células da tabela
            if 'Relationships' not in table_block:
                return None
            
            cells = []
            for relationship in table_block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for cell_id in relationship['Ids']:
                        if cell_id in blocks_by_id:
                            cell_block = blocks_by_id[cell_id]
                            if cell_block['BlockType'] == 'CELL':
                                cells.append(cell_block)
            
            # Organizar células por linha e coluna
            cells_by_position = {}
            for cell in cells:
                row_index = cell.get('RowIndex', 0)
                col_index = cell.get('ColumnIndex', 0)
                cell_text = self._extract_cell_text(cell, blocks_by_id)
                
                if row_index not in cells_by_position:
                    cells_by_position[row_index] = {}
                
                cells_by_position[row_index][col_index] = {
                    'text': cell_text,
                    'confidence': cell.get('Confidence', 0),
                    'is_header': row_index == 1  # Primeira linha como header
                }
            
            # Construir estrutura de tabela
            for row_index in sorted(cells_by_position.keys()):
                row_data = []
                for col_index in sorted(cells_by_position[row_index].keys()):
                    cell_data = cells_by_position[row_index][col_index]
                    row_data.append(cell_data['text'])
                
                if row_index == 1:  # Headers
                    table_data['headers'] = row_data
                else:
                    table_data['rows'].append(row_data)
            
            table_data['cell_count'] = len(cells)
            return table_data if table_data['cell_count'] > 0 else None
            
        except Exception as e:
            print(f"⚠️ Erro processando tabela: {str(e)}")
            return None
    
    def _extract_cell_text(self, cell_block: Dict, blocks_by_id: Dict) -> str:
        """Extrair texto de uma célula específica"""
        
        cell_text = ""
        
        if 'Relationships' in cell_block:
            for relationship in cell_block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        if child_id in blocks_by_id:
                            child_block = blocks_by_id[child_id]
                            if child_block['BlockType'] == 'WORD':
                                cell_text += child_block.get('Text', '') + ' '
        
        return cell_text.strip()
    
    def _extract_key_value_pairs(self, blocks: List[Dict], blocks_by_id: Dict) -> Dict[str, str]:
        """Extrair pares chave-valor de formulários"""
        
        key_value_pairs = {}
        
        # Encontrar blocos KEY_VALUE_SET
        key_blocks = {}
        value_blocks = {}
        
        for block in blocks:
            if block['BlockType'] == 'KEY_VALUE_SET':
                if 'KEY' in block.get('EntityTypes', []):
                    key_blocks[block['Id']] = block
                elif 'VALUE' in block.get('EntityTypes', []):
                    value_blocks[block['Id']] = block
        
        # Relacionar chaves com valores
        for key_id, key_block in key_blocks.items():
            key_text = self._extract_text_from_block(key_block, blocks_by_id)
            
            # Encontrar valor relacionado
            value_text = ""
            if 'Relationships' in key_block:
                for relationship in key_block['Relationships']:
                    if relationship['Type'] == 'VALUE':
                        for value_id in relationship['Ids']:
                            if value_id in value_blocks:
                                value_block = value_blocks[value_id]
                                value_text = self._extract_text_from_block(value_block, blocks_by_id)
                                break
            
            if key_text and len(key_text.strip()) > 0:
                key_value_pairs[key_text.strip()] = value_text.strip()
        
        return key_value_pairs
    
    def _extract_text_from_block(self, block: Dict, blocks_by_id: Dict) -> str:
        """Extrair texto de um bloco específico"""
        
        text = ""
        
        if 'Relationships' in block:
            for relationship in block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        if child_id in blocks_by_id:
                            child_block = blocks_by_id[child_id]
                            if child_block['BlockType'] == 'WORD':
                                text += child_block.get('Text', '') + ' '
        
        return text.strip()
    
    def _calculate_extraction_metrics(self, response: Dict, extracted_data: Dict) -> Dict[str, Any]:
        """Calcular métricas de qualidade da extração"""
        
        confidences = []
        word_count = 0
        line_count = 0
        
        for block in response['Blocks']:
            if 'Confidence' in block:
                confidences.append(block['Confidence'])
            
            if block['BlockType'] == 'WORD':
                word_count += 1
            elif block['BlockType'] == 'LINE':
                line_count += 1
        
        return {
            'total_blocks': len(response['Blocks']),
            'average_confidence': sum(confidences) / len(confidences) if confidences else 0,
            'min_confidence': min(confidences) if confidences else 0,
            'max_confidence': max(confidences) if confidences else 0,
            'word_count': word_count,
            'line_count': line_count,
            'text_length': len(extracted_data['text'])
        }
    
    async def _fallback_to_tesseract(self, file_path: str) -> Dict[str, Any]:
        """Fallback para Tesseract quando AWS Textract não disponível"""
        
        try:
            print("🔄 Fallback: Usando Tesseract...")
            
            # Importar OCR service existente
            from .ocr_service import OCRService
            ocr_service = OCRService()
            
            # Extrair texto com Tesseract
            if file_path.lower().endswith('.pdf'):
                extracted_text = await ocr_service.extract_from_pdf(file_path)
            else:
                extracted_text = await ocr_service.extract_from_image(file_path)
            
            return {
                "success": True,
                "service": "Tesseract (Fallback)",
                "file_processed": os.path.basename(file_path),
                "timestamp": datetime.now().isoformat(),
                "extracted_text": extracted_text,
                "tables": [],
                "forms": [],
                "key_value_pairs": {},
                "confidence": 0.7,  # Confiança estimada para Tesseract
                "blocks_processed": 0,
                "words_extracted": len(extracted_text.split()),
                "lines_extracted": len(extracted_text.split('\n')),
                "tables_found": 0,
                "forms_found": 0,
                "fallback_used": True
            }
            
        except Exception as e:
            print(f"❌ Erro no fallback Tesseract: {str(e)}")
            return {
                "success": False,
                "service": "Fallback Failed",
                "error": str(e),
                "extracted_text": "",
                "tables": [],
                "forms": [],
                "key_value_pairs": {}
            }
    
    def format_extraction_summary(self, extraction_result: Dict) -> str:
        """Formatar resumo da extração para logs/reports"""
        
        if not extraction_result.get('success'):
            return f"❌ Falha na extração: {extraction_result.get('error', 'Erro desconhecido')}"
        
        summary = f"""
📄 RESUMO DA EXTRAÇÃO - {extraction_result['service']}

📊 MÉTRICAS:
• Arquivo: {extraction_result['file_processed']}
• Confiança: {extraction_result['confidence']:.1f}%
• Palavras: {extraction_result['words_extracted']}
• Linhas: {extraction_result['lines_extracted']}
• Tabelas: {extraction_result['tables_found']}
• Formulários: {extraction_result['forms_found']}

📝 CONTEÚDO:
• Texto extraído: {len(extraction_result['extracted_text'])} caracteres
• Campos de formulário: {len(extraction_result['key_value_pairs'])} pares

⏰ Processado em: {extraction_result['timestamp']}
"""
        
        return summary.strip()

# ============================================================================
# INTEGRAÇÃO COM SISTEMA MÉDICO
# ============================================================================

class MedicalDocumentAnalyzer:
    """Analisador especializado para documentos médicos usando Textract"""
    
    def __init__(self):
        self.textract_service = AWSTextractService()
        self.medical_keywords = {
            'exames_laboratoriais': [
                'hemograma', 'glicemia', 'colesterol', 'triglicerídeos',
                'ureia', 'creatinina', 'tsh', 'hemoglobina', 'leucócitos'
            ],
            'exames_imagem': [
                'raio-x', 'tomografia', 'ressonância', 'ultrassom',
                'ecocardiograma', 'mamografia', 'densitometria'
            ],
            'medicamentos': [
                'mg', 'ml', 'comprimido', 'cápsula', 'prescrito',
                'posologia', 'dosagem', 'administrar'
            ]
        }
    
    async def analyze_medical_document(self, file_path: str) -> Dict[str, Any]:
        """Analisar documento médico com contexto especializado"""
        
        # Extrair conteúdo com Textract
        extraction_result = await self.textract_service.extract_text_from_document(file_path)
        
        if not extraction_result['success']:
            return extraction_result
        
        # Análise médica especializada
        medical_analysis = self._analyze_medical_content(extraction_result)
        
        # Combinar resultados
        return {
            **extraction_result,
            'medical_analysis': medical_analysis,
            'document_type': medical_analysis['document_type'],
            'medical_relevance': medical_analysis['relevance_score']
        }
    
    def _analyze_medical_content(self, extraction_result: Dict) -> Dict[str, Any]:
        """Análise especializada do conteúdo médico"""
        
        text = extraction_result['extracted_text'].lower()
        tables = extraction_result['tables']
        forms = extraction_result['key_value_pairs']
        
        # Detectar tipo de documento
        document_type = self._detect_document_type(text, tables, forms)
        
        # Extrair informações médicas relevantes
        medical_info = self._extract_medical_information(text, tables, forms)
        
        # Calcular score de relevância médica
        relevance_score = self._calculate_medical_relevance(text, medical_info)
        
        return {
            'document_type': document_type,
            'medical_info': medical_info,
            'relevance_score': relevance_score,
            'has_numerical_results': bool(medical_info['numerical_values']),
            'has_medication_info': bool(medical_info['medications']),
            'has_diagnostic_info': bool(medical_info['diagnostic_terms'])
        }
    
    def _detect_document_type(self, text: str, tables: List, forms: Dict) -> str:
        """Detectar tipo de documento médico"""
        
        if any(keyword in text for keyword in ['hemograma', 'leucócitos', 'hemoglobina']):
            return 'exame_laboratorial'
        elif any(keyword in text for keyword in ['raio-x', 'tomografia', 'ressonância']):
            return 'exame_imagem'
        elif any(keyword in text for keyword in ['prescri', 'medicament', 'posologia']):
            return 'receita_medica'
        elif any(keyword in text for keyword in ['laudo', 'diagnóstico', 'conclusão']):
            return 'laudo_medico'
        elif len(tables) > 0:
            return 'relatorio_estruturado'
        elif len(forms) > 0:
            return 'formulario_medico'
        else:
            return 'documento_generico'
    
    def _extract_medical_information(self, text: str, tables: List, forms: Dict) -> Dict[str, Any]:
        """Extrair informações médicas específicas"""
        
        import re
        
        medical_info = {
            'numerical_values': [],
            'medications': [],
            'diagnostic_terms': [],
            'dates': [],
            'reference_ranges': []
        }
        
        # Extrair valores numéricos com unidades médicas
        numerical_pattern = r'(\d+(?:\.\d+)?)\s*(mg|ml|mmol|g/dl|mg/dl|%|bpm|mmhg)'
        medical_info['numerical_values'] = re.findall(numerical_pattern, text, re.IGNORECASE)
        
        # Extrair medicamentos
        for keyword_group in self.medical_keywords['medicamentos']:
            if keyword_group in text:
                # Contexto ao redor da palavra
                context_pattern = rf'.{{0,50}}{keyword_group}.{{0,50}}'
                contexts = re.findall(context_pattern, text, re.IGNORECASE)
                medical_info['medications'].extend(contexts)
        
        # Extrair termos diagnósticos
        diagnostic_patterns = [
            r'diagnóstico:?\s*([^\n\.]+)',
            r'conclusão:?\s*([^\n\.]+)',
            r'hipótese:?\s*([^\n\.]+)'
        ]
        
        for pattern in diagnostic_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            medical_info['diagnostic_terms'].extend(matches)
        
        # Extrair datas
        date_pattern = r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}'
        medical_info['dates'] = re.findall(date_pattern, text)
        
        return medical_info
    
    def _calculate_medical_relevance(self, text: str, medical_info: Dict) -> float:
        """Calcular score de relevância médica (0-1)"""
        
        score = 0.0
        
        # Pontuação por valores numéricos
        score += min(len(medical_info['numerical_values']) * 0.1, 0.3)
        
        # Pontuação por medicamentos
        score += min(len(medical_info['medications']) * 0.15, 0.3)
        
        # Pontuação por termos diagnósticos
        score += min(len(medical_info['diagnostic_terms']) * 0.2, 0.4)
        
        # Pontuação por palavras-chave médicas gerais
        medical_word_count = 0
        for category in self.medical_keywords.values():
            for keyword in category:
                if keyword in text:
                    medical_word_count += 1
        
        score += min(medical_word_count * 0.05, 0.3)
        
        return min(score, 1.0)

# ============================================================================
# INSTÂNCIAS GLOBAIS
# ============================================================================

# Serviço principal
aws_textract_service = AWSTextractService()

# Analisador médico especializado
medical_document_analyzer = MedicalDocumentAnalyzer()

# Export para compatibilidade
__all__ = ['AWSTextractService', 'MedicalDocumentAnalyzer', 'aws_textract_service', 'medical_document_analyzer']

print("✅ AWS Textract Service implementado com analisador médico especializado!")
print("🏥 Funcionalidades: OCR Avançado + Tabelas + Formulários + Análise Médica")
print("📋 Fallback automático para Tesseract se AWS indisponível")