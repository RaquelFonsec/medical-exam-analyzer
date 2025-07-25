import os
import json
import faiss
import numpy as np
import pickle
from typing import Dict, List, Optional, Tuple, Any
from openai import OpenAI

class MedicalRAGService:
    """
    Serviço RAG especializado para análise de consultas médicas
    Integra com índices FAISS gerados a partir de PDFs médicos
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.index_dir = "index_faiss_openai"
        self.faiss_index = None
        self.documents = []
        self.embedding_model = "text-embedding-3-small"
        self.load_indexes()
    
    def load_indexes(self):
        """Carrega os índices FAISS e documentos salvos"""
        try:
            # Carrega o índice FAISS
            index_path = os.path.join(self.index_dir, "index.faiss")
            if os.path.exists(index_path):
                self.faiss_index = faiss.read_index(index_path)
                print(f"✅ Índice FAISS carregado: {self.faiss_index.ntotal} vetores")
            else:
                print(f"⚠️ Índice FAISS não encontrado em: {index_path}")
            
            # Carrega os documentos/chunks
            docs_path = os.path.join(self.index_dir, "documents.pkl")
            if os.path.exists(docs_path):
                with open(docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
                print(f"✅ Documentos carregados: {len(self.documents)} chunks")
            else:
                print(f"⚠️ Documentos não encontrados em: {docs_path}")
                
        except Exception as e:
            print(f"❌ Erro ao carregar índices: {e}")
            self.faiss_index = None
            self.documents = []
    
    def search_similar_documents(self, query: str, k: int = 5, min_similarity: float = 0.5) -> List[Tuple[str, float]]:
        """Busca documentos similares no índice FAISS"""
        if not self.faiss_index or not self.documents:
            print("❌ Índices não carregados")
            return []
        
        if not query.strip():
            return []
        
        try:
            # Gera embedding da query
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=query.strip()
            )
            query_embedding = response.data[0].embedding
            
            # Converte para numpy array
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # Busca no FAISS
            distances, indices = self.faiss_index.search(query_vector, min(k, len(self.documents)))
            
            # Filtra e retorna resultados
            results = []
            for distance, idx in zip(distances[0], indices[0]):
                if idx < len(self.documents) and idx >= 0:
                    # Converte distância euclidiana para similaridade
                    similarity = 1 / (1 + distance)
                    
                    if similarity >= min_similarity:
                        results.append((self.documents[idx], similarity))
            
            # Ordena por similaridade (maior primeiro)
            results.sort(key=lambda x: x[1], reverse=True)
            return results
            
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
            return []
    
    def get_rag_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema RAG"""
        return {
            "index_loaded": self.faiss_index is not None,
            "total_vectors": self.faiss_index.ntotal if self.faiss_index else 0,
            "total_documents": len(self.documents),
            "embedding_model": self.embedding_model,
            "index_directory": self.index_dir
        }
