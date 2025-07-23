import asyncio
from typing import Dict, Any, List
from .transcription_service import TranscriptionService
from .ocr_service import OCRService
from .llm_service import LLMService
import os

class MedicalConsultationProcessor:
    def __init__(self):
        self.transcription_service = TranscriptionService()
        self.ocr_service = OCRService()
        self.llm_service = LLMService()
    
    async def process_consultation(self, consultation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa consulta médica completa"""
        try:
            print(f"🏥 Processando consulta médica")
            
            # 1. Transcrever áudio se fornecido
            transcription = ""
            if consultation_data.get("audio_file"):
                result = await self.transcription_service.transcribe_audio(
                    consultation_data["audio_file"]
                )
                transcription = result["transcription"]
                print(f"✅ Áudio transcrito: {len(transcription)} caracteres")
            
            # 2. Processar documentos anexados
            documents_summary = []
            if consultation_data.get("documents"):
                for doc_path in consultation_data["documents"]:
                    doc_text = await self._extract_document_text(doc_path)
                    summary = await self._summarize_document(doc_text, doc_path)
                    documents_summary.append({
                        "file": os.path.basename(doc_path),
                        "text": doc_text,
                        "summary": summary
                    })
                print(f"✅ Documentos processados: {len(documents_summary)}")
            
            # 3. Gerar laudo médico estruturado
            medical_report = await self._generate_medical_report(
                transcription, documents_summary, consultation_data
            )
            
            return {
                "transcription": transcription,
                "documents": documents_summary,
                "medical_report": medical_report,
                "status": "processed",
                "confidence": 0.85
            }
            
        except Exception as e:
            print(f"❌ Erro no processamento: {str(e)}")
            raise Exception(f"Erro no processamento: {str(e)}")
    
    async def _extract_document_text(self, file_path: str) -> str:
        """Extrai texto de documento"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return await self.ocr_service.extract_from_pdf(file_path)
        else:
            return await self.ocr_service.extract_from_image(file_path)
    
    async def _summarize_document(self, text: str, filename: str) -> str:
        """Gera resumo técnico do documento"""
        prompt = f"""
Analise este documento médico e gere um resumo técnico conciso:

DOCUMENTO: {filename}
CONTEÚDO: {text[:1000]}...

Crie um resumo técnico focando em:
- Tipo de exame/documento
- Principais achados/resultados
- Valores relevantes
- Conclusões importantes

Resumo técnico:
"""
        
        try:
            summary = await self.llm_service._openai_generate(prompt)
            return summary
        except:
            return f"Resumo: {text[:200]}..."
    
    async def _generate_medical_report(self, transcription: str, documents: List[Dict], consultation_data: Dict) -> str:
        """Gera laudo médico estruturado"""
        
        # Consolidar informações
        context = self._build_medical_context(transcription, documents, consultation_data)
        
        prompt = f"""
Você é um médico especialista gerando um laudo médico técnico e estruturado.

CONTEXTO CLÍNICO:
{context}

Gere um LAUDO MÉDICO ESTRUTURADO seguindo este formato:

##  IDENTIFICAÇÃO
- Paciente: [extrair das informações disponíveis]
- Data da consulta: [data atual ou fornecida]
- Modalidade: [teleconsulta/presencial]

##  QUEIXA PRINCIPAL
[Extrair da transcrição a queixa principal do paciente]

##  HISTÓRIA DA DOENÇA ATUAL (HDA)
[Descrever cronologicamente o quadro atual com:
- Data de início dos sintomas
- Evolução dos sintomas
- Fatores agravantes/atenuantes
- Tratamentos já realizados]

##  ACHADOS DE EXAME FÍSICO/DOCUMENTAL
[Consolidar achados de exames anexados e exame físico mencionado]

##  TRATAMENTO ATUAL
[Medicações e terapias em uso]

##  DIAGNÓSTICO CLÍNICO
[Diagnóstico baseado nos achados]

## PROGNÓSTICO
[Expectativa de evolução do quadro]

## CONCLUSÃO
[Síntese para fins de benefício/pleito se aplicável]

##  CID-10
[Códigos CID-10 compatíveis com o diagnóstico]

---
IMPORTANTE: Use linguagem técnica médica apropriada. Base-se apenas nas informações fornecidas.
Este é um RASCUNHO que deve ser revisado pelo médico responsável.
"""
        
        try:
            report = await self.llm_service._openai_generate(prompt)
            return report
        except Exception as e:
            return f"Erro na geração do laudo: {str(e)}"
    
    def _build_medical_context(self, transcription: str, documents: List[Dict], consultation_data: Dict) -> str:
        """Constrói contexto médico unificado"""
        context = ""
        
        if transcription:
            context += f"TRANSCRIÇÃO DA CONSULTA:\n{transcription}\n\n"
        
        if documents:
            context += "DOCUMENTOS ANEXADOS:\n"
            for doc in documents:
                context += f"- {doc['file']}: {doc['summary']}\n"
            context += "\n"
        
        if consultation_data.get("patient_info"):
            context += f"INFORMAÇÕES DO PACIENTE:\n{consultation_data['patient_info']}\n\n"
        
        return context
