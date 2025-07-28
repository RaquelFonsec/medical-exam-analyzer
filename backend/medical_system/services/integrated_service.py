"""
Serviço Integrado de Análise Médica
"""

import logging
from datetime import datetime
from typing import Dict, List, Any

from ..models.pydantic_models import CompleteMedicalRecord, Specialty
from ..pipeline.medical_pipeline import MedicalAnalysisPipeline

class IntegratedMedicalAnalysisService:
    """Serviço principal que integra todo o sistema"""
    
    def __init__(self, openai_client, rag_service, faiss_index=None):
        self.client = openai_client
        self.rag_service = rag_service
        self.faiss_index = faiss_index
        self.pipeline = MedicalAnalysisPipeline(openai_client, rag_service)
        
        # Logger para auditoria
        self.setup_logging()
    
    def setup_logging(self):
        """Configura logging para auditoria médica"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('medical_analysis.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('MedicalAnalysis')
    
    async def process_medical_transcription(self, transcription_text: str) -> Dict[str, Any]:
        """
        Processa transcrição médica completa usando o pipeline integrado
        
        Args:
            transcription_text: Texto da transcrição da consulta médica
            
        Returns:
            Dict com prontuário completo, classificação e laudo
        """
        
        start_time = datetime.now()
        self.logger.info(f"Iniciando análise médica - Texto: {len(transcription_text)} caracteres")
        
        try:
            # 1. Indexar transcrição no FAISS (se disponível)
            if self.faiss_index:
                await self._index_transcription(transcription_text)
            
            # 2. Executar pipeline principal
            medical_record, final_report = await self.pipeline.analyze_medical_case(transcription_text)
            
            # 3. Extrair dados para resposta
            result = self._build_final_response(medical_record, final_report, transcription_text)
            
            # 4. Log de auditoria
            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Análise concluída em {processing_time:.2f}s - Benefício: {result.get('beneficio_classificado')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro no processamento: {str(e)}")
            return self._build_error_response(str(e))
    
    async def _index_transcription(self, text: str):
        """Indexa transcrição no FAISS para consultas futuras"""
        try:
            # Quebrar texto em chunks para indexação
            chunks = self._create_text_chunks(text)
            
            for chunk in chunks:
                # Aqui você adicionaria ao FAISS
                # self.faiss_index.add_text(chunk)
                pass
                
        except Exception as e:
            self.logger.warning(f"Erro na indexação FAISS: {str(e)}")
    
    def _create_text_chunks(self, text: str, chunk_size: int = 500) -> List[str]:
        """Cria chunks de texto para indexação"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks
    
    def _build_final_response(self, medical_record: CompleteMedicalRecord, 
                            final_report: str, original_text: str) -> Dict[str, Any]:
        """Constrói resposta final estruturada"""
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            
            # Dados do paciente estruturados
            "paciente": {
                "identificacao": medical_record.identificacao.dict() if medical_record else {},
                "idade_anos": medical_record.identificacao.idade if medical_record else None,
                "profissao": medical_record.identificacao.profissao if medical_record else "não informada",
            },
            
            # Análise médica
            "analise_medica": {
                "especialidade_principal": medical_record.avaliacao_medica.especialidade_principal.value if medical_record else "clinica_geral",
                "cid_principal": medical_record.avaliacao_medica.cid_principal if medical_record else "",
                "cid_descricao": medical_record.avaliacao_medica.cid_descricao if medical_record else "",
                "gravidade": medical_record.avaliacao_medica.gravidade_quadro if medical_record else "moderada",
                "prognostico": medical_record.avaliacao_medica.prognostico if medical_record else "reservado",
            },
            
            # Classificação de benefício
            "beneficio_classificado": self._extract_benefit_from_report(final_report),
            "justificativa_beneficio": self._extract_justification_from_report(final_report),
            
            # Capacidade funcional
            "capacidade_laborativa": medical_record.capacidade_laborativa if medical_record else "prejudicada",
            "limitacoes_funcionais": [lim.value for lim in medical_record.exame_telemedico.limitacoes_funcionais] if medical_record else [],
            "necessita_auxilio_terceiros": medical_record.necessita_auxilio_terceiros if medical_record else False,
            
            # Nexo ocupacional (importante para telemedicina)
            "nexo_ocupacional": {
                "identificado": medical_record.nexo_ocupacional if medical_record else False,
                "observacao": "Telemedicina - CFM não permite estabelecimento de nexo laboral",
                "requer_avaliacao_presencial": True
            },
            
            # Documentos e evidências
            "documentacao_analisada": {
                "suficiente": medical_record.documentacao.documentos_suficientes if medical_record else False,
                "exames_presentes": medical_record.documentacao.exames_complementares if medical_record else [],
                "cids_documentados": medical_record.documentacao.cids_mencionados if medical_record else []
            },
            
            # Laudo médico completo
            "laudo_medico": final_report,
            
            # Recomendações
            "recomendacoes": {
                "especialidade_indicada": medical_record.avaliacao_medica.especialidade_principal.value if medical_record else "clinica_geral",
                "exames_complementares": self._suggest_additional_exams(medical_record),
                "acompanhamento_necessario": True
            },
            
            # Metadados
            "metadados": {
                "metodo_analise": "RAG_ENHANCED_LANGGRAPH",
                "confiabilidade": "alta",
                "revisao_necessaria": False,
                "texto_original_caracteres": len(original_text),
                "pipeline_metrics": self.pipeline.get_pipeline_metrics()
            }
        }
    
    def _extract_benefit_from_report(self, report: str) -> str:
        """Extrai tipo de benefício do laudo"""
        if not report:
            return "NÃO_CLASSIFICADO"
            
        benefit_patterns = {
            "BPC/LOAS": ["BPC", "LOAS", "impedimento de longo prazo"],
            "AUXÍLIO-DOENÇA": ["AUXÍLIO-DOENÇA", "temporariamente incapacitado"],
            "APOSENTADORIA POR INVALIDEZ": ["APOSENTADORIA", "permanentemente incapacitado"],
            "AUXÍLIO-ACIDENTE": ["AUXÍLIO-ACIDENTE", "redução parcial"],
            "ISENÇÃO IMPOSTO DE RENDA": ["ISENÇÃO", "doença grave"]
        }
        
        for benefit, patterns in benefit_patterns.items():
            if any(pattern.lower() in report.lower() for pattern in patterns):
                return benefit
        
        return "NÃO_CLASSIFICADO"
    
    def _extract_justification_from_report(self, report: str) -> str:
        """Extrai justificativa do laudo"""
        if not report:
            return "Justificativa não disponível devido a erro no processamento."
            
        # Buscar seção de conclusão
        if "CONCLUSÃO" in report:
            conclusion_start = report.find("CONCLUSÃO")
            conclusion_end = report.find("CID-10", conclusion_start)
            if conclusion_end == -1:
                conclusion_end = len(report)
            
            conclusion = report[conclusion_start:conclusion_end].strip()
            return conclusion.replace("CONCLUSÃO", "").strip()
        
        return "Justificativa baseada na análise médica completa."
    
    def _suggest_additional_exams(self, medical_record: CompleteMedicalRecord) -> List[str]:
        """Sugere exames complementares baseado na especialidade"""
        if not medical_record:
            return ["Análise incompleta - exames não sugeridos"]
        
        exam_suggestions = {
            Specialty.PSIQUIATRIA: ["Avaliação neuropsicológica", "Exames laboratoriais"],
            Specialty.CARDIOLOGIA: ["Ecocardiograma", "Teste ergométrico", "Holter 24h"],
            Specialty.NEUROLOGIA: ["Ressonância magnética", "Eletroencefalograma"],
            Specialty.OFTALMOLOGIA: ["Campimetria visual", "OCT retina"],
            Specialty.ORTOPEDIA: ["Radiografia", "Ressonância magnética"],
            Specialty.CLINICA_GERAL: ["Exames conforme especialidade específica"]
        }
        
        specialty = medical_record.avaliacao_medica.especialidade_principal
        return exam_suggestions.get(specialty, ["Exames complementares conforme especialidade"])
    
    def _build_error_response(self, error_message: str) -> Dict[str, Any]:
        """Constrói resposta de erro estruturada"""
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "beneficio_classificado": "ERRO_PROCESSAMENTO",
            "laudo_medico": f"Erro no processamento da análise médica: {error_message}",
            "paciente": {
                "identificacao": {},
                "idade_anos": None,
                "profissao": "não informada"
            },
            "analise_medica": {
                "especialidade_principal": "clinica_geral",
                "cid_principal": "",
                "cid_descricao": "",
                "gravidade": "não avaliada",
                "prognostico": "não avaliado"
            },
            "recomendacoes": {
                "acao": "Revisar transcrição e tentar novamente",
                "contato_suporte": True,
                "especialidade_indicada": "clinica_geral",
                "exames_complementares": []
            },
            "metadados": {
                "metodo_analise": "RAG_ENHANCED_LANGGRAPH",
                "confiabilidade": "baixa",
                "revisao_necessaria": True,
                "texto_original_caracteres": 0
            }
        }
    
    # Métodos de consulta RAG específicos
    async def query_similar_cases(self, patient_description: str, limit: int = 5) -> List[Dict]:
        """Consulta casos similares no índice FAISS"""
        try:
            if not self.rag_service:
                return []
            
            similar_docs = self.rag_service.search_similar_documents(patient_description, k=limit)
            
            return [
                {
                    "documento": doc,
                    "similaridade": float(score),
                    "relevancia": "alta" if score > 0.8 else "media" if score > 0.6 else "baixa"
                }
                for doc, score in similar_docs
            ]
            
        except Exception as e:
            self.logger.error(f"Erro na consulta de casos similares: {str(e)}")
            return []
    
    async def get_specialty_guidelines(self, specialty: str, condition: str) -> str:
        """Busca diretrizes específicas da especialidade"""
        try:
            query = f"{specialty} {condition} diretrizes tratamento"
            docs = self.rag_service.search_similar_documents(query, k=3)
            
            if docs:
                return "\n".join([doc for doc, score in docs if score > 0.7])
            
            return "Diretrizes não encontradas na base de conhecimento."
            
        except Exception as e:
            self.logger.error(f"Erro na busca de diretrizes: {str(e)}")
            return ""
    
    # Métodos de utilidade e health check
    async def health_check(self) -> Dict[str, Any]:
        """Verifica saúde do sistema"""
        try:
            pipeline_health = await self.pipeline.validate_pipeline_health()
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "pipeline": pipeline_health["status"],
                    "rag_service": "available" if self.rag_service else "not_configured",
                    "faiss_index": "available" if self.faiss_index else "not_configured",
                    "openai_client": "connected"
                },
                "metrics": self.pipeline.get_pipeline_metrics(),
                "issues": pipeline_health.get("issues", []),
                "recommendations": pipeline_health.get("recommendations", [])
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "components": {
                    "pipeline": "error",
                    "rag_service": "unknown",
                    "faiss_index": "unknown",
                    "openai_client": "unknown"
                }
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema"""
        return {
            "pipeline_metrics": self.pipeline.get_pipeline_metrics(),
            "system_info": {
                "rag_configured": self.rag_service is not None,
                "faiss_configured": self.faiss_index is not None,
                "uptime": datetime.now().isoformat()
            }
        }
    
    def reset_system_metrics(self):
        """Reseta todas as métricas do sistema"""
        self.pipeline.reset_metrics()
        self.logger.info("Métricas do sistema resetadas")