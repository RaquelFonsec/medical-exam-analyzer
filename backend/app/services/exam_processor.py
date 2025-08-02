"""
Exam Processor - Processador de exames médicos
"""

import os
import tempfile
import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import UploadFile

# Import do serviço que acabamos de criar
from .textract_service import MedicalDocumentAnalyzer

logger = logging.getLogger(__name__)

class ExamProcessor:
    """Processador de exames médicos"""
    
    def __init__(self):
        self.analyzer = MedicalDocumentAnalyzer()
        logger.info("✅ ExamProcessor inicializado")
    
    async def process_exam(self, file: UploadFile, exam_type: str = "auto") -> Dict[str, Any]:
        """Processar exame médico"""
        
        try:
            logger.info(f"🔍 Processando exame: {file.filename} (tipo: {exam_type})")
            
            # Salvar arquivo temporário
            temp_path = await self._save_temp_file(file)
            
            try:
                # Analisar documento
                result = await self.analyzer.analyze_medical_document(temp_path)
                
                # Adicionar metadados
                result.update({
                    'filename': file.filename,
                    'exam_type': exam_type,
                    'timestamp': datetime.now().isoformat(),
                    'processor': 'ExamProcessor'
                })
                
                logger.info(f"✅ Exame processado: {file.filename}")
                return result
                
            finally:
                # Limpar arquivo temporário
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        except Exception as e:
            logger.error(f"❌ Erro ao processar exame: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': file.filename,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _save_temp_file(self, file: UploadFile) -> str:
        """Salvar arquivo temporário"""
        
        content = await file.read()
        await file.seek(0)  # Reset
        
        suffix = os.path.splitext(file.filename or '')[1] or '.tmp'
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as temp_file:
            temp_file.write(content)
            return temp_file.name
