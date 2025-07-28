"""
Pipeline Principal de Análise Médica com LangGraph
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Importações LangGraph
try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_IMPORTS_OK = True
except ImportError as e:
    print(f"❌ Erro nas importações LangGraph: {e}")
    LANGGRAPH_IMPORTS_OK = False

from ..models.state_models import MedicalAnalysisState
from ..models.pydantic_models import CompleteMedicalRecord
from ..nodes.medical_nodes import MedicalAnalysisNodes

class MedicalAnalysisPipeline:
    """Pipeline completo de análise médica com LangGraph"""
    
    def __init__(self, client, rag_service):
        self.client = client
        self.rag_service = rag_service
        self.nodes = MedicalAnalysisNodes(client, rag_service)
        self.graph = self._build_graph()
        
        # Configurações do pipeline
        self.pipeline_config = {
            "max_retries": 3,
            "timeout_seconds": 300,
            "enable_checkpoints": True,
            "log_level": "INFO"
        }
        
        # Métricas de performance
        self.metrics = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "average_processing_time": 0.0,
            "specialty_distribution": {},
            "benefit_classification_stats": {}
        }
    
    def _build_graph(self) -> StateGraph:
        """Constrói o grafo do pipeline"""
        
        # Verificar se LangGraph está disponível
        if not LANGGRAPH_IMPORTS_OK:
            raise ImportError("LangGraph não está disponível. Instale com: pip install langgraph")
        
        # Criar grafo com estado tipado
        workflow = StateGraph(MedicalAnalysisState)
        
        # Adicionar nodos com validações
        workflow.add_node("extract_basic", self._wrap_node_with_error_handling(
            self.nodes.extract_basic_data, "Extração de dados básicos"
        ))
        workflow.add_node("analyze_specialty", self._wrap_node_with_error_handling(
            self.nodes.analyze_by_specialty, "Análise por especialidade"
        ))
        workflow.add_node("detect_occupational", self._wrap_node_with_error_handling(
            self.nodes.detect_occupational_nexus, "Detecção de nexo ocupacional"
        ))
        workflow.add_node("classify_benefit", self._wrap_node_with_error_handling(
            self.nodes.classify_benefit, "Classificação de benefício"
        ))
        workflow.add_node("generate_record", self._wrap_node_with_error_handling(
            self.nodes.generate_medical_record, "Geração de prontuário"
        ))
        workflow.add_node("generate_report", self._wrap_node_with_error_handling(
            self.nodes.generate_final_report, "Geração de laudo final"
        ))
        
        # Definir fluxo sequencial com condicionais
        workflow.add_edge(START, "extract_basic")
        workflow.add_conditional_edges(
            "extract_basic",
            self._should_continue_after_extraction,
            {
                "continue": "analyze_specialty",
                "error": END
            }
        )
        workflow.add_edge("analyze_specialty", "detect_occupational")
        workflow.add_edge("detect_occupational", "classify_benefit")
        workflow.add_conditional_edges(
            "classify_benefit",
            self._should_generate_full_record,
            {
                "full_record": "generate_record",
                "simple_report": "generate_report"
            }
        )
        workflow.add_edge("generate_record", "generate_report")
        workflow.add_edge("generate_report", END)
        
        # Compilar com checkpointer para debugging e recuperação
        if self.pipeline_config["enable_checkpoints"]:
            memory = MemorySaver()
            compiled_graph = workflow.compile(checkpointer=memory)
        else:
            compiled_graph = workflow.compile()
        
        print("✅ Grafo LangGraph construído com sucesso")
        return compiled_graph
    
    def _wrap_node_with_error_handling(self, node_func, node_name: str):
        """Wraps node function with error handling and metrics"""
        async def wrapped_node(state: MedicalAnalysisState) -> MedicalAnalysisState:
            start_time = datetime.now()
            
            try:
                print(f"🔄 Executando: {node_name}")
                result_state = await node_func(state)
                
                # Log sucesso
                processing_time = (datetime.now() - start_time).total_seconds()
                print(f"✅ {node_name} concluído em {processing_time:.2f}s")
                
                return result_state
                
            except Exception as e:
                # Log erro
                error_msg = f"Erro em {node_name}: {str(e)}"
                print(f"❌ {error_msg}")
                
                # Adicionar erro ao estado
                if "errors" not in state:
                    state["errors"] = []
                state["errors"].append(error_msg)
                state["current_step"] = f"error_in_{node_name.lower().replace(' ', '_')}"
                
                return state
        
        return wrapped_node
    
    def _should_continue_after_extraction(self, state: MedicalAnalysisState) -> str:
        """Decide se deve continuar após extração básica"""
        if state.get("errors") and len(state["errors"]) > 0:
            return "error"
        
        extracted_data = state.get("extracted_data")
        if not extracted_data or not extracted_data.get("identificacao"):
            return "error"
        
        return "continue"
    
    def _should_generate_full_record(self, state: MedicalAnalysisState) -> str:
        """Decide se deve gerar prontuário completo ou apenas relatório simples"""
        # Se há muitos erros, gerar apenas relatório simples
        if state.get("errors") and len(state["errors"]) > 2:
            return "simple_report"
        
        # Se classificação foi bem-sucedida, gerar prontuário completo
        classification = state.get("benefit_classification")
        if classification and classification.get("tipo_beneficio"):
            return "full_record"
        
        return "simple_report"
    
    async def analyze_medical_case(self, patient_text: str) -> Tuple[CompleteMedicalRecord, str]:
        """Executa análise completa do caso médico"""
        
        analysis_start_time = datetime.now()
        analysis_id = f"analysis_{int(analysis_start_time.timestamp())}"
        
        print(f"🚀 INICIANDO PIPELINE DE ANÁLISE MÉDICA - ID: {analysis_id}")
        print(f"📄 Texto de entrada: {len(patient_text)} caracteres")
        
        # Atualizar métricas
        self.metrics["total_analyses"] += 1
        
        # Estado inicial com metadados
        initial_state = MedicalAnalysisState(
            original_text=patient_text,
            extracted_data=None,
            medical_record=None,
            benefit_classification=None,
            specialist_analysis=None,
            final_report=None,
            errors=[],
            current_step="pipeline_starting"
        )
        
        try:
            # Configuração da execução
            config = {
                "configurable": {
                    "thread_id": analysis_id,
                    "run_name": f"medical_analysis_{analysis_id}",
                    "tags": ["medical_analysis", "telemedicine"]
                }
            }
            
            # Executar pipeline com timeout
            print("⚡ Executando pipeline LangGraph...")
            
            if self.pipeline_config["timeout_seconds"]:
                final_state = await asyncio.wait_for(
                    self.graph.ainvoke(initial_state, config),
                    timeout=self.pipeline_config["timeout_seconds"]
                )
            else:
                final_state = await self.graph.ainvoke(initial_state, config)
            
            # Calcular tempo de processamento
            processing_time = (datetime.now() - analysis_start_time).total_seconds()
            
            # Verificar resultado
            if final_state.get("errors") and len(final_state["errors"]) > 0:
                print(f"⚠️  Pipeline concluído com {len(final_state['errors'])} erro(s):")
                for error in final_state["errors"]:
                    print(f"   - {error}")
                
                self._update_error_metrics(final_state["errors"])
            else:
                print("✅ Pipeline executado sem erros")
                self.metrics["successful_analyses"] += 1
            
            # Extrair resultados
            medical_record = final_state.get("medical_record")
            final_report = final_state.get("final_report", "")
            
            # Se não há relatório, gerar um básico
            if not final_report:
                final_report = self._generate_fallback_report(final_state, patient_text)
            
            # Atualizar métricas de performance
            self._update_performance_metrics(final_state, processing_time)
            
            # Log final
            print(f"🏁 PIPELINE CONCLUÍDO - Etapa final: {final_state.get('current_step', 'unknown')}")
            print(f"⏱️  Tempo total: {processing_time:.2f}s")
            
            if final_state.get("benefit_classification"):
                benefit_type = final_state["benefit_classification"].get("tipo_beneficio", "NÃO_CLASSIFICADO")
                print(f"🎯 Benefício classificado: {benefit_type}")
            
            return medical_record, final_report
            
        except asyncio.TimeoutError:
            error_msg = f"Pipeline excedeu timeout de {self.pipeline_config['timeout_seconds']}s"
            print(f"⏰ {error_msg}")
            self.metrics["failed_analyses"] += 1
            
            fallback_report = f"ANÁLISE INTERROMPIDA POR TIMEOUT\n\n{error_msg}\n\nTexto analisado parcialmente."
            return None, fallback_report
            
        except Exception as e:
            error_msg = f"Erro crítico no pipeline: {str(e)}"
            print(f"💥 {error_msg}")
            self.metrics["failed_analyses"] += 1
            
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            
            error_report = f"ERRO NO PROCESSAMENTO\n\n{error_msg}\n\nPor favor, verifique o texto de entrada e tente novamente."
            return None, error_report
    
    def _update_error_metrics(self, errors: List[str]):
        """Atualiza métricas de erro"""
        self.metrics["failed_analyses"] += 1
        
        for error in errors:
            if "extração" in error.lower():
                self.metrics.setdefault("extraction_errors", 0)
                self.metrics["extraction_errors"] += 1
            elif "classificação" in error.lower():
                self.metrics.setdefault("classification_errors", 0)
                self.metrics["classification_errors"] += 1
            elif "especialidade" in error.lower():
                self.metrics.setdefault("specialty_errors", 0)
                self.metrics["specialty_errors"] += 1
    
    def _update_performance_metrics(self, final_state: MedicalAnalysisState, processing_time: float):
        """Atualiza métricas de performance"""
        
        total_analyses = self.metrics["total_analyses"]
        current_avg = self.metrics["average_processing_time"]
        
        self.metrics["average_processing_time"] = (
            (current_avg * (total_analyses - 1) + processing_time) / total_analyses
        )
        
        specialist_analysis = final_state.get("specialist_analysis", {})
        if specialist_analysis.get("primary_specialty"):
            specialty = specialist_analysis["primary_specialty"]
            specialty_name = specialty.value if hasattr(specialty, 'value') else str(specialty)
            
            self.metrics["specialty_distribution"].setdefault(specialty_name, 0)
            self.metrics["specialty_distribution"][specialty_name] += 1
        
        classification = final_state.get("benefit_classification", {})
        if classification.get("tipo_beneficio"):
            benefit_type = classification["tipo_beneficio"]
            
            self.metrics["benefit_classification_stats"].setdefault(benefit_type, 0)
            self.metrics["benefit_classification_stats"][benefit_type] += 1
    
    def _generate_fallback_report(self, state: MedicalAnalysisState, original_text: str) -> str:
        """Gera relatório de fallback quando o pipeline falha"""
        
        return f"""
RELATÓRIO MÉDICO PARCIAL

⚠️  ATENÇÃO: Análise incompleta devido a erro no processamento

DADOS COLETADOS:
- Texto original: {len(original_text)} caracteres
- Etapa atual: {state.get('current_step', 'desconhecida')}
- Erros encontrados: {len(state.get('errors', []))}

ERROS IDENTIFICADOS:
{chr(10).join([f"• {error}" for error in state.get('errors', [])])}

RECOMENDAÇÃO:
Este caso requer revisão manual devido aos erros encontrados no processamento automático.

Data do processamento: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
"""
   
    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do pipeline"""
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful_analyses"] / max(self.metrics["total_analyses"], 1) * 100
            ),
            "error_rate": (
                self.metrics["failed_analyses"] / max(self.metrics["total_analyses"], 1) * 100
            ),
            "configuration": self.pipeline_config
        }
    
    def reset_metrics(self):
        """Reseta métricas do pipeline"""
        self.metrics = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "average_processing_time": 0.0,
            "specialty_distribution": {},
            "benefit_classification_stats": {}
        }
        print("📊 Métricas do pipeline resetadas")
