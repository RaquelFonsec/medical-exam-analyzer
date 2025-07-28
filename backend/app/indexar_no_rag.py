import os
import sys
import pickle
import numpy as np
from openai import OpenAI

# Carregar configuração
from dotenv import load_dotenv
load_dotenv()

def indexar_laudos_no_rag():
    """Indexar todos os laudos médicos no sistema RAG"""
    
    print("🚀 Iniciando indexação dos laudos no RAG...")
    
    # Inicializar OpenAI
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Ler todos os laudos
    laudos_dir = 'relatorios/'
    arquivos = [f for f in os.listdir(laudos_dir) if f.startswith('relatorio_') and f.endswith('.txt')]
    
    documentos = []
    embeddings = []
    
    print(f"📄 Processando {len(arquivos)} laudos...")
    
    for i, arquivo in enumerate(arquivos):
        try:
            with open(os.path.join(laudos_dir, arquivo), 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            # Criar documento estruturado
            documento = f"ARQUIVO: {arquivo}\n{conteudo}"
            documentos.append(documento)
            
            # Gerar embedding
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=conteudo[:8000]  # Limitar tamanho
            )
            
            embedding = response.data[0].embedding
            embeddings.append(embedding)
            
            print(f"✅ Processado {i+1}/{len(arquivos)}: {arquivo}")
            
        except Exception as e:
            print(f"❌ Erro ao processar {arquivo}: {e}")
    
    print(f"\n📊 Resultados:")
    print(f"  Laudos processados: {len(documentos)}")
    print(f"  Embeddings gerados: {len(embeddings)}")
    print(f"  Dimensão dos embeddings: {len(embeddings[0]) if embeddings else 0}")
    
    # Salvar no formato RAG existente
    if embeddings:
        try:
            import faiss
            
            # Criar índice FAISS
            dimension = len(embeddings[0])
            index = faiss.IndexFlatIP(dimension)  # Inner Product (similares ao cosine)
            
            # Normalizar embeddings para usar cosine similarity
            embeddings_array = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings_array)
            
            # Adicionar ao índice
            index.add(embeddings_array)
            
            # Salvar índice e documentos
            os.makedirs('index_faiss_openai', exist_ok=True)
            
            faiss.write_index(index, 'index_faiss_openai/index.faiss')
            
            with open('index_faiss_openai/documents.pkl', 'wb') as f:
                pickle.dump(documentos, f)
            
            print(f"\n✅ Índice RAG atualizado com sucesso!")
            print(f"  Arquivo: index_faiss_openai/index.faiss")
            print(f"  Documentos: index_faiss_openai/documents.pkl")
            print(f"  Total de vetores: {index.ntotal}")
            
        except Exception as e:
            print(f"❌ Erro ao salvar índice FAISS: {e}")
    
    return len(documentos)

if __name__ == "__main__":
    total = indexar_laudos_no_rag()
    print(f"\n🎉 Indexação concluída: {total} laudos adicionados ao RAG!")
