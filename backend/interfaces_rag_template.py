"""
TEMPLATE DAS INTERFACES PARA RAG E BANCO VETORIAL

Este arquivo mostra as interfaces que você deve implementar para conectar
o banco vetorial e serviço RAG ao sistema.

Não delete este arquivo - use como referência para implementação.
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

# ============================================================================
# INTERFACE DO BANCO VETORIAL
# ============================================================================

class VectorDatabaseInterface(ABC):
    """
    Interface que o banco vetorial deve implementar
    
    Exemplo de uso:
    
    from vector_db_service import MyVectorDB
    from app.services.multimodal_ai_service import connect_vector_db
    
    vector_db = MyVectorDB()
    connect_vector_db(vector_db)
    """
    
    @abstractmethod
    async def search_similar(self, query: str, limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Buscar documentos similares baseados na query
        
        Args:
            query: Texto da transcrição para buscar similares
            limit: Número máximo de resultados (5 para últimos 5 exemplos)
            threshold: Similaridade mínima (0.7 recomendado)
        
        Returns:
            Lista de documentos similares no formato:
            [
                {
                    "transcription": "transcrição do caso similar",
                    "extracted_data": { dados estruturados extraídos },
                    "anamnese": "anamnese do caso similar", 
                    "laudo_medico": "laudo do caso similar",
                    "timestamp": "2024-01-01T10:00:00",
                    "similarity_score": 0.85
                }
            ]
        """
        pass
    
    @abstractmethod
    async def save_document(self, document: Dict[str, Any]) -> str:
        """
        Salvar novo documento no banco vetorial
        
        Args:
            document: Documento no formato:
            {
                "transcription": "transcrição do áudio",
                "extracted_data": { dados estruturados },
                "anamnese": "anamnese gerada",
                "laudo_medico": "laudo gerado", 
                "timestamp": "2024-01-01T10:00:00",
                "vector_content": "texto para embedding"
            }
        
        Returns:
            ID do documento salvo
        """
        pass
    
    @abstractmethod
    async def get_document_count(self) -> int:
        """Retornar número total de documentos salvos"""
        pass

# ============================================================================
# INTERFACE DO SERVIÇO RAG
# ============================================================================

class RAGServiceInterface(ABC):
    """
    Interface que o serviço RAG deve implementar
    
    Exemplo de uso:
    
    from rag_service import MyRAGService
    from app.services.multimodal_ai_service import connect_rag_service
    
    rag_service = MyRAGService()
    connect_rag_service(rag_service)
    """
    
    @abstractmethod
    async def extract_structured_data(self, prompt: str, transcription: str, examples: List[Dict]) -> Dict[str, Any]:
        """
        Extrair dados estruturados usando RAG + exemplos
        
        Args:
            prompt: Prompt construído com exemplos
            transcription: Transcrição atual
            examples: Lista dos 5 exemplos similares do banco vetorial
        
        Returns:
            Dados estruturados no formato:
            {
                "paciente": {
                    "nome": "João Silva",
                    "idade": "45", 
                    "sexo": "M",
                    "profissao": "Pedreiro"
                },
                "condicao_medica": "Sequelas de acidente de trabalho",
                "sintomas": "Dor lombar, limitação de movimento",
                "limitacoes": "Incapacidade para levantamento de peso",
                "cronologia": "há 6 meses",
                "cid_sugerido": "M54.5 - Dor lombar baixa", 
                "especialidade": "Ortopedia",
                "beneficio": "auxilio-doenca"
            }
        """
        pass
    
    @abstractmethod
    async def generate_anamnese(self, prompt: str, transcription: str, 
                              extracted_data: Dict, examples: List[Dict]) -> str:
        """
        Gerar anamnese médica usando RAG + exemplos
        
        Args:
            prompt: Prompt com exemplos de anamneses
            transcription: Transcrição atual
            extracted_data: Dados estruturados extraídos
            examples: Exemplos similares
        
        Returns:
            Anamnese médica estruturada
        """
        pass
    
    @abstractmethod
    async def generate_laudo(self, prompt: str, transcription: str,
                           extracted_data: Dict, examples: List[Dict]) -> str:
        """
        Gerar laudo médico usando RAG + exemplos
        
        Args:
            prompt: Prompt com exemplos de laudos
            transcription: Transcrição atual
            extracted_data: Dados estruturados extraídos
            examples: Exemplos similares
        
        Returns:
            Laudo médico técnico
        """
        pass

# ============================================================================
# EXEMPLO DE IMPLEMENTAÇÃO MOCK (para testes)
# ============================================================================

class MockVectorDB(VectorDatabaseInterface):
    """Implementação mock para testes"""
    
    def __init__(self):
        self.documents = []
    
    async def search_similar(self, query: str, limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        # Mock: retorna exemplos fixos
        return [
            {
                "transcription": "Doutor, sou pedreiro há 15 anos, sofri acidente na obra...",
                "extracted_data": {
                    "paciente": {"nome": "João", "idade": "45", "profissao": "Pedreiro"},
                    "condicao_medica": "Sequelas de acidente de trabalho",
                    "especialidade": "Ortopedia"
                },
                "anamnese": "ANAMNESE - Paciente masculino, 45 anos...",
                "laudo_medico": "LAUDO MÉDICO - Apresenta sequelas...",
                "similarity_score": 0.85
            }
        ]
    
    async def save_document(self, document: Dict[str, Any]) -> str:
        doc_id = f"doc_{len(self.documents) + 1}"
        document["id"] = doc_id
        self.documents.append(document)
        return doc_id
    
    async def get_document_count(self) -> int:
        return len(self.documents)

class MockRAGService(RAGServiceInterface):
    """Implementação mock para testes"""
    
    async def extract_structured_data(self, prompt: str, transcription: str, examples: List[Dict]) -> Dict[str, Any]:
        # Mock: extração básica
        return {
            "paciente": {"nome": "Conforme informado", "idade": "45", "profissao": "Não informado"},
            "condicao_medica": "Condição médica relatada",
            "especialidade": "Clínica Geral",
            "beneficio": "avaliacao-medica"
        }
    
    async def generate_anamnese(self, prompt: str, transcription: str, 
                              extracted_data: Dict, examples: List[Dict]) -> str:
        return "ANAMNESE MÉDICA gerada via RAG mock"
    
    async def generate_laudo(self, prompt: str, transcription: str,
                           extracted_data: Dict, examples: List[Dict]) -> str:
        return "LAUDO MÉDICO gerado via RAG mock"

# ============================================================================
# COMO CONECTAR OS SERVIÇOS
# ============================================================================

"""
EXEMPLO DE CONEXÃO:

# No seu arquivo principal ou startup:

from app.services.multimodal_ai_service import connect_vector_db, connect_rag_service
from your_vector_db import YourVectorDB
from your_rag_service import YourRAGService

# Inicializar serviços
vector_db = YourVectorDB(connection_string="your_connection")
rag_service = YourRAGService(model="gpt-4", api_key="your_key")

# Conectar ao sistema
connect_vector_db(vector_db)
connect_rag_service(rag_service)

print("✅ RAG e Banco Vetorial conectados!")

# Agora o sistema usará automaticamente RAG quando analyze_multimodal for chamado
"""

# ============================================================================
# FLUXO COMPLETO DO SISTEMA RAG
# ============================================================================

"""
FLUXO COMPLETO:

1. USUÁRIO ENVIA ÁUDIO
   ↓
2. WHISPER TRANSCREVE ÁUDIO  
   ↓
3. BANCO VETORIAL busca 5 exemplos similares baseados na transcrição
   ↓
4. RAG SERVICE recebe transcrição + 5 exemplos + prompt estruturado
   ↓
5. RAG SERVICE extrai dados estruturados (nome, idade, CID, etc.)
   ↓
6. RAG SERVICE gera anamnese baseada na transcrição + exemplos
   ↓
7. RAG SERVICE gera laudo baseado na transcrição + exemplos  
   ↓
8. SISTEMA salva caso atual no banco vetorial para futuros exemplos
   ↓
9. RETORNA resultado completo para frontend

VANTAGENS:
- Aprendizado contínuo (cada caso melhora os próximos)
- Consistência baseada em exemplos reais
- Extração mais precisa usando casos similares
- Escalabilidade automática
""" 