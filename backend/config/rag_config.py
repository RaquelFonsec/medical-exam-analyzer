"""Configuração do sistema RAG"""

import os

# Caminhos dos arquivos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAG_DATA_DIR = os.path.join(BASE_DIR, "data")
FAISS_INDEX_PATH = os.path.join(RAG_DATA_DIR, "medical_knowledge.faiss")
CHUNKS_PATH = os.path.join(RAG_DATA_DIR, "medical_chunks.pkl")
TRAINING_DATA_DIR = os.path.join(BASE_DIR, "training_data")

# Configurações do modelo
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 500
TOP_K_RESULTS = 10
SIMILARITY_THRESHOLD = 0.7

# Configurações OpenAI
OPENAI_MODEL = "gpt-4o-mini"
MAX_TOKENS = 2000
TEMPERATURE = 0.3

# Configurações FAISS
FAISS_INDEX_TYPE = "IndexFlatL2"

# Configurações de logging
ENABLE_DEBUG = True
LOG_SIMILARITY_SCORES = True
LOG_CHUNK_CLASSIFICATION = True

# Tipos de chunks suportados
CHUNK_TYPES = [
    'anamnese',
    'diagnostico', 
    'limitacoes',
    'tratamento',
    'exame_fisico',
    'conclusao',
    'geral'
]
