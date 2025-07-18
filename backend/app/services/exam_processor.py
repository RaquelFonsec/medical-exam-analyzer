import asyncio
from typing import Dict, Any
from .ocr_service import OCRService
from .llm_service import LLMService
import os

class ExamProcessor:
    def __init__(self):
        self.ocr_service = OCRService()
        self.llm_service = LLMService()
    
    async def process_exam(self, file_path: str, exam_type: str) -> Dict[str, Any]:
        """Processa exame médico completo"""
        try:
            print(f"🔍 Processando arquivo: {file_path}")
            print(f"📋 Tipo de exame: {exam_type}")
            
            # 1. Extrair texto do arquivo
            extracted_text = await self._extract_text(file_path)
            print(f"✅ Texto extraído: {len(extracted_text)} caracteres")
            
            # 2. Gerar relatório com LLM
            report = await self.llm_service.generate_medical_report(
                extracted_text, exam_type
            )
            print("✅ Relatório gerado")
            
            # 3. Calcular confiança
            confidence = self._calculate_confidence(extracted_text, report)
            
            return {
                "extracted_text": extracted_text,
                "report": report,
                "confidence": confidence,
                "exam_type": exam_type
            }
            
        except Exception as e:
            print(f"❌ Erro no processamento: {str(e)}")
            raise Exception(f"Erro no processamento: {str(e)}")
    
    async def _extract_text(self, file_path: str) -> str:
        """Extrai texto do arquivo"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return await self.ocr_service.extract_from_pdf(file_path)
        else:
            return await self.ocr_service.extract_from_image(file_path)
    
    def _calculate_confidence(self, text: str, report: str) -> float:
        """Calcula confiança do processamento"""
        text_length = len(text.strip())
        if text_length < 50:
            return 0.4
        elif text_length < 200:
            return 0.6
        else:
            return 0.9
