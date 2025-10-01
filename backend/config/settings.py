# ============================================================================
# SETTINGS.PY - CONFIGURAÇÕES CENTRALIZADAS DO SISTEMA
# config/settings.py
# ============================================================================

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

class Settings:
   """Configurações centralizadas do sistema médico"""
   
   # ========================================================================
   # OPENAI CONFIGURATION
   # ========================================================================
   OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
   
   # ========================================================================
   # AWS CONFIGURATION
   # ========================================================================
   AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
   AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
   AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
   AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
   
   # ========================================================================
   # LLM CONFIGURATION
   # ========================================================================
   LLM_MODEL_DEFAULT = os.getenv('LLM_MODEL_DEFAULT', 'gpt-3.5-turbo-1106')
   LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '500'))
   LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.3'))
   LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '30'))
   
   # Circuit breaker settings
   CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv('CIRCUIT_BREAKER_FAILURE_THRESHOLD', '3'))
   CIRCUIT_BREAKER_TIMEOUT = int(os.getenv('CIRCUIT_BREAKER_TIMEOUT', '300'))  # 5 minutes
   
   # ========================================================================
   # TEXTRACT CONFIGURATION
   # ========================================================================
   TEXTRACT_MAX_PAGES = int(os.getenv('TEXTRACT_MAX_PAGES', '10'))
   TEXTRACT_CONFIDENCE_THRESHOLD = float(os.getenv('TEXTRACT_CONFIDENCE_THRESHOLD', '50.0'))
   
   # ========================================================================
   # WHISPER CONFIGURATION
   # ========================================================================
   WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'whisper-1')
   WHISPER_LANGUAGE = os.getenv('WHISPER_LANGUAGE', 'pt')
   WHISPER_TEMPERATURE = float(os.getenv('WHISPER_TEMPERATURE', '0.1'))
   
   # ========================================================================
   # FILE PROCESSING LIMITS
   # ========================================================================
   MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '25'))
   MAX_AUDIO_DURATION_MINUTES = int(os.getenv('MAX_AUDIO_DURATION_MINUTES', '10'))
   
   SUPPORTED_IMAGE_FORMATS = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']
   SUPPORTED_AUDIO_FORMATS = ['.mp3', '.mp4', '.wav', '.webm', '.m4a']
   
   # ========================================================================
   # SYSTEM CONFIGURATION
   # ========================================================================
   DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
   LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
   ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
   
   # ========================================================================
   # VALIDATION METHODS
   # ========================================================================
   
   def validate_openai_config(self) -> bool:
       """Valida se configuração OpenAI está completa"""
       return bool(self.OPENAI_API_KEY)
   
   def validate_aws_config(self) -> bool:
       """Valida se configuração AWS está completa"""
       return bool(
           self.AWS_ACCESS_KEY_ID and 
           self.AWS_SECRET_ACCESS_KEY and 
           self.AWS_REGION
       )
   
   def get_missing_config(self) -> list:
       """Retorna lista de configurações em falta"""
       missing = []
       
       if not self.OPENAI_API_KEY:
           missing.append('OPENAI_API_KEY')
       
       if not self.AWS_ACCESS_KEY_ID:
           missing.append('AWS_ACCESS_KEY_ID')
       
       if not self.AWS_SECRET_ACCESS_KEY:
           missing.append('AWS_SECRET_ACCESS_KEY')
       
       return missing
   
   def get_config_summary(self) -> dict:
       """Retorna resumo das configurações (sem expor chaves)"""
       return {
           'openai_configured': bool(self.OPENAI_API_KEY),
           'aws_configured': self.validate_aws_config(),
           'aws_region': self.AWS_REGION,
           'llm_model': self.LLM_MODEL_DEFAULT,
           'environment': self.ENVIRONMENT,
           'debug_mode': self.DEBUG,
           'max_file_size_mb': self.MAX_FILE_SIZE_MB,
           'supported_formats': {
               'images': self.SUPPORTED_IMAGE_FORMATS,
               'audio': self.SUPPORTED_AUDIO_FORMATS
           }
       }

# Instância global das configurações
settings = Settings()

