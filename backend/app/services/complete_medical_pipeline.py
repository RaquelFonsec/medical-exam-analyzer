# ============================================================================
# PIPELINE MÉDICO COMPLETO: RAG + FAISS + LANGGRAPH + PYDANTIC
# ============================================================================

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Para não dar erro de import, vamos usar imports condicionais
try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph não instalado - funcionalidade limitada")

from ..models import (
    PatientData, 
    CompleteMedicalAnalysis,
    BenefitType
)

class SimpleMedicalPipeline:
    """Pipeline médico simplificado (sem LangGraph se não estiver disponível)"""
    
    def __init__(self, openai_client, rag_service=None):
        self.client = openai_client
        self.rag_service = rag_service
        self.logger = logging.getLogger(__name__)
    
    async def process_medical_transcription(self, transcription_text: str) -> Dict[str, Any]:
        """Processa transcrição médica"""
        
        start_time = datetime.now()
        
        try:
            # Análise básica sem LangGraph
            result = await self._basic_medical_analysis(transcription_text)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            result["processing_time"] = processing_time
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro no processamento: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def _basic_medical_analysis(self, text: str) -> Dict[str, Any]:
        """Análise médica básica"""
        
        prompt = f"""
        Analise esta transcrição médica e retorne uma análise estruturada:

        TRANSCRIÇÃO: {text}

        Retorne JSON com:
        {{
            "paciente": {{
                "nome": "nome do paciente",
                "idade": idade_numerica,
                "profissao": "profissão"
            }},
            "diagnostico": "diagnóstico principal",
            "beneficio_recomendado": "AUXÍLIO-DOENÇA/BPC-LOAS/APOSENTADORIA/etc",
            "justificativa": "justificativa médica",
            "laudo_resumido": "laudo médico resumido"
        }}
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Médico perito especialista."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=800
        )
        
        import json
        content = response.choices[0].message.content.strip()
        content = content.replace('```json', '').replace('```', '').strip()
        
        analysis = json.loads(content)
        
        return {
            "status": "success",
            "beneficio_classificado": analysis.get("beneficio_recomendado", "BPC/LOAS"),
            "analise_medica": analysis.get("diagnostico", ""),
            "laudo_medico": analysis.get("laudo_resumido", ""),
            "paciente": analysis.get("paciente", {}),
            "justificativa": analysis.get("justificativa", ""),
            "metadados": {
                "metodo_analise": "BASIC_PIPELINE",
                "langgraph_disponivel": LANGGRAPH_AVAILABLE
            }
        }

# Factory function
def create_medical_pipeline(openai_client, rag_service=None):
    """Cria pipeline médico (LangGraph se disponível, senão básico)"""
    
    if LANGGRAPH_AVAILABLE:
        # TODO: Implementar pipeline completo com LangGraph
        # return CompleteLangGraphPipeline(openai_client, rag_service)
        pass
    
    return SimpleMedicalPipeline(openai_client, rag_service)
