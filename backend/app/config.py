import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
# Tentar diferentes caminhos para o .env
import pathlib
project_root = pathlib.Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")  # /home/raquel/medical-exam-analyzer/.env
load_dotenv("../.env")  # fallback para path antigo
load_dotenv(".env")     # fallback para path relativo

class Settings:
    # APIs
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    
    # App
    SECRET_KEY = os.getenv("SECRET_KEY", "medical-exam-analyzer-secret-key-2024")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # Folders
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    REPORTS_FOLDER = os.getenv("REPORTS_FOLDER", "reports")
    
    # File settings
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "16777216"))
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff"}
    
    # Database PostgreSQL
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://medical_user:MedicalApp2024!@localhost:5432/medical_exams")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "medical_exams")
    DB_USER = os.getenv("DB_USER", "medical_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "MedicalApp2024!")
    
    # Security
    ENCRYPT_FILES = os.getenv("ENCRYPT_FILES", "True").lower() == "true"

settings = Settings()
