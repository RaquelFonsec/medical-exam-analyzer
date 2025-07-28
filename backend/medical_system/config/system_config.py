"""
Configurações do Sistema Médico Integrado
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime

class MedicalSystemConfiguration:
    """Configuração central do sistema médico integrado"""
    
    DEFAULT_CONFIG = {
        "openai_model": "gpt-4o",
        "openai_model_mini": "gpt-4o-mini",
        "openai_max_tokens": 800,
        "openai_temperature": 0.0,
        "pipeline_timeout_seconds": 300,
        "pipeline_max_retries": 3,
        "pipeline_enable_checkpoints": True,
        "pipeline_log_level": "INFO",
        "rag_chunk_size": 500,
        "rag_similarity_threshold": 0.7,
        "rag_max_docs": 3,
        "system_enable_audit_log": True,
        "system_log_file": "medical_analysis.log",
        "telemedicine_allow_occupational_nexus": False,
        "telemedicine_require_disclaimer": True
    }
    
    @classmethod
    def load_from_env(cls) -> Dict[str, Any]:
        """Carrega configurações das variáveis de ambiente"""
        config = cls.DEFAULT_CONFIG.copy()
        
        # Carregar variáveis de ambiente se existirem
        env_mappings = {
            "OPENAI_MODEL": "openai_model",
            "OPENAI_MODEL_MINI": "openai_model_mini",
            "PIPELINE_TIMEOUT": "pipeline_timeout_seconds",
            "PIPELINE_MAX_RETRIES": "pipeline_max_retries"
        }
        
        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if config_key in ["pipeline_timeout_seconds", "pipeline_max_retries"]:
                    config[config_key] = int(env_value)
                elif config_key in ["openai_temperature"]:
                    config[config_key] = float(env_value)
                else:
                    config[config_key] = env_value
        
        return config
    
    @classmethod
    def create_complete_system(cls, openai_api_key: str, rag_service, 
                             faiss_index=None, custom_config: Optional[Dict] = None):
        """Cria sistema completo configurado"""
        
        # Carregar configurações
        config = cls.load_from_env()
        if custom_config:
            config.update(custom_config)
        
        # Validar API key
        if not openai_api_key:
            raise ValueError("OpenAI API key é obrigatória")
        
        # Importar e criar cliente OpenAI
        try:
            import openai
            client = openai.OpenAI(api_key=openai_api_key)
        except ImportError:
            raise ImportError("OpenAI library não instalada. Execute: pip install openai")
        
        # Importar e criar sistema integrado
        from ..services.integrated_service import IntegratedMedicalAnalysisService  
        
        medical_system = IntegratedMedicalAnalysisService(
            openai_client=client,
            rag_service=rag_service,
            faiss_index=faiss_index
        )
        
        # Aplicar configurações ao pipeline se possível
        if hasattr(medical_system.pipeline, 'pipeline_config'):
            pipeline_configs = {
                k.replace('pipeline_', ''): v 
                for k, v in config.items() 
                if k.startswith('pipeline_')
            }
            medical_system.pipeline.pipeline_config.update(pipeline_configs)
        
        return medical_system, config
    
    @classmethod
    def validate_system_requirements(cls) -> Dict[str, Any]:
        """Valida se todos os requisitos do sistema estão atendidos"""
        
        issues = []
        warnings = []
        
        # Verificar dependências Python obrigatórias
        required_packages = [
            ("openai", "OpenAI library"),
            ("pydantic", "Pydantic for data validation")
        ]
        
        for package, description in required_packages:
            try:
                __import__(package)
            except ImportError:
                issues.append(f"{description} não instalado: pip install {package}")
        
        # Verificar dependências opcionais
        optional_packages = [
            ("langgraph", "LangGraph for pipeline (opcional)")
        ]
        
        for package, description in optional_packages:
            try:
                __import__(package)
            except ImportError:
                warnings.append(f"{description} não instalado")
        
        # Verificar variáveis de ambiente críticas
        if not os.getenv("OPENAI_API_KEY"):
            issues.append("Variável OPENAI_API_KEY não configurada")
        
        return {
            "system_ready": len(issues) == 0,
            "critical_issues": issues,
            "warnings": warnings,
            "recommendations": [
                "Configure variável OPENAI_API_KEY",
                "Instale dependências opcionais se necessário"
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    @classmethod
    def generate_config_template(cls, output_file: str = "medical_system_config.json"):
        """Gera arquivo template de configuração"""
        
        template = {
            "_comment": "Configuração do Sistema Médico Integrado",
            "_generated": datetime.now().isoformat(),
            "openai": {
                "model": cls.DEFAULT_CONFIG["openai_model"],
                "model_mini": cls.DEFAULT_CONFIG["openai_model_mini"],
                "max_tokens": cls.DEFAULT_CONFIG["openai_max_tokens"],
                "temperature": cls.DEFAULT_CONFIG["openai_temperature"]
            },
            "pipeline": {
                "timeout_seconds": cls.DEFAULT_CONFIG["pipeline_timeout_seconds"],
                "max_retries": cls.DEFAULT_CONFIG["pipeline_max_retries"],
                "enable_checkpoints": cls.DEFAULT_CONFIG["pipeline_enable_checkpoints"]
            },
            "rag": {
                "chunk_size": cls.DEFAULT_CONFIG["rag_chunk_size"],
                "similarity_threshold": cls.DEFAULT_CONFIG["rag_similarity_threshold"],
                "max_docs": cls.DEFAULT_CONFIG["rag_max_docs"]
            }
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Template de configuração criado: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar template: {e}")
            return False

# Funções de conveniência
def load_system_config() -> Dict[str, Any]:
    """Carrega configuração do sistema"""
    return MedicalSystemConfiguration.load_from_env()

def validate_system_setup() -> bool:
    """Valida se sistema está pronto para uso"""
    requirements = MedicalSystemConfiguration.validate_system_requirements()
    return requirements["system_ready"]

def create_medical_system(openai_api_key: str, rag_service, **kwargs):
    """Função de conveniência para criar sistema médico"""
    return MedicalSystemConfiguration.create_complete_system(
        openai_api_key, rag_service, **kwargs
    )
