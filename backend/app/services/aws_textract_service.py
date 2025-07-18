import boto3
import json
from typing import Dict, List, Any

class AWSTextractService:
    def __init__(self):
        self.textract = boto3.client('textract', region_name='us-east-1')
        print("✅ AWS Textract inicializado")
    
    async def extract_text_from_document(self, file_path: str) -> Dict[str, Any]:
        """Extrair texto com AWS Textract - MUITO mais preciso"""
        try:
            # Ler arquivo
            with open(file_path, 'rb') as document:
                document_bytes = document.read()
            
            # Chamar Textract
            response = self.textract.analyze_document(
                Document={'Bytes': document_bytes},
                FeatureTypes=['TABLES', 'FORMS']  # Extrair tabelas e formulários!
            )
            
            # Extrair texto
            extracted_text = ""
            tables = []
            forms = {}
            
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    extracted_text += block['Text'] + '\n'
                elif block['BlockType'] == 'TABLE':
                    # Processar tabelas
                    tables.append(self._process_table(block, response))
                elif block['BlockType'] == 'KEY_VALUE_SET':
                    # Processar formulários (campo: valor)
                    key, value = self._process_form_field(block, response)
                    if key and value:
                        forms[key] = value
            
            return {
                "success": True,
                "extracted_text": extracted_text,
                "tables": tables,
                "forms": forms,
                "confidence": self._calculate_confidence(response),
                "service": "AWS Textract",
                "blocks_processed": len(response['Blocks'])
            }
            
        except Exception as e:
            print(f"❌ Erro AWS Textract: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _calculate_confidence(self, response) -> float:
        """Calcular confiança média"""
        confidences = []
        for block in response['Blocks']:
            if 'Confidence' in block:
                confidences.append(block['Confidence'])
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _process_table(self, table_block, response) -> Dict[str, Any]:
        """Processar tabela extraída"""
        try:
            # Implementação simplificada - extrair células
            table_data = {
                "id": table_block.get('Id', ''),
                "confidence": table_block.get('Confidence', 0),
                "rows": [],
                "type": "table"
            }
            
            # Para implementação completa, seria necessário
            # processar as relações entre células
            return table_data
            
        except Exception as e:
            print(f"⚠️ Erro processando tabela: {str(e)}")
            return {"error": str(e)}
    
    def _process_form_field(self, block, response) -> tuple:
        """Processar campo de formulário"""
        try:
            # Implementação simplificada
            if block['BlockType'] == 'KEY_VALUE_SET':
                if 'KEY' in block.get('EntityTypes', []):
                    # Extrair chave
                    key = self._extract_text_from_block(block, response)
                    return key, None
                elif 'VALUE' in block.get('EntityTypes', []):
                    # Extrair valor
                    value = self._extract_text_from_block(block, response)
                    return None, value
            
            return None, None
            
        except Exception as e:
            print(f"⚠️ Erro processando formulário: {str(e)}")
            return None, None
    
    def _extract_text_from_block(self, block, response) -> str:
        """Extrair texto de um bloco específico"""
        try:
            text = ""
            if 'Relationships' in block:
                for relationship in block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        for child_id in relationship['Ids']:
                            # Encontrar bloco filho
                            child_block = next(
                                (b for b in response['Blocks'] if b['Id'] == child_id), 
                                None
                            )
                            if child_block and child_block['BlockType'] == 'WORD':
                                text += child_block.get('Text', '') + ' '
            
            return text.strip()
            
        except Exception as e:
            print(f"⚠️ Erro extraindo texto: {str(e)}")
            return ""
