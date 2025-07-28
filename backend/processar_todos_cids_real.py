#!/usr/bin/env python3
import csv
import os
import faiss
import numpy as np
import pickle
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

def safe_read_csv(filename):
    """Lê CSV com encoding correto"""
    try:
        with open(filename, 'r', encoding='iso-8859-1') as f:
            delimiter = ';' if ';' in f.read(1000) else ','
            f.seek(0)
            reader = csv.reader(f, delimiter=delimiter)
            rows = list(reader)
            print(f"✅ Leu {len(rows)} linhas")
            return rows
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

def create_enhanced_chunks():
    """Cria chunks com TODOS os CIDs + regras"""
    
    print("🔄 Processando TODOS os CIDs...")
    
    chunks = []
    
    # 1. REGRAS FUNDAMENTAIS (sempre primeiro)
    rules_chunk = """REGRAS DE CLASSIFICAÇÃO MÉDICA:

DIABETES FUNDAMENTAL:
- SE paciente USA INSULINA (aplico insulina, injeto insulina, uso insulina) = E10.x
- SE paciente NÃO USA INSULINA (metformina, comprimidos) = E11.x

HIPERTENSÃO:
- Pressão alta, hipertensão, losartana, captopril = I10

DEPRESSÃO:
- Depressão, tristeza, fluoxetina, sertralina = F32.x

ANSIEDADE:
- Ansiedade, pânico, clonazepam, alprazolam = F41.x

INFARTO:
- Infarto, coração, dor no peito = I21.x

COLUNA:
- Hérnia disco, coluna, lombar = M51.x"""
    
    chunks.append(rules_chunk)
    
    # 2. PROCESSAR ARQUIVO CSV
    rows = safe_read_csv('CID-10-SUBCATEGORIAS.CSV')
    
    if not rows:
        print("⚠️ Usando apenas regras básicas")
        return chunks
    
    current_chunk = ""
    processed = 0
    
    for row in rows:
        if len(row) >= 2:
            codigo = row[0].strip()
            descricao = row[1].strip()
            
            # Filtros básicos
            if (len(codigo) >= 3 and 
                codigo[0].isalpha() and 
                len(descricao) > 5 and
                'não classificad' not in descricao.lower()):
                
                line = f"{codigo} - {descricao}"
                
                # Adicionar palavras-chave para CIDs importantes
                if codigo.startswith('E10'):
                    line += " | DIABETES INSULINA"
                elif codigo.startswith('E11'):
                    line += " | DIABETES SEM INSULINA"
                elif codigo.startswith('I10'):
                    line += " | HIPERTENSÃO"
                elif codigo.startswith('F32'):
                    line += " | DEPRESSÃO"
                elif codigo.startswith('F41'):
                    line += " | ANSIEDADE PÂNICO"
                elif codigo.startswith('I21'):
                    line += " | INFARTO"
                elif codigo.startswith('M51'):
                    line += " | HÉRNIA DISCO"
                
                # Adicionar ao chunk atual
                if len(current_chunk + line) < 600:
                    current_chunk += line + "\n"
                else:
                    # Salvar chunk atual
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = line + "\n"
                
                processed += 1
                
                # Progresso
                if processed % 2000 == 0:
                    print(f"   Processados: {processed} CIDs...")
    
    # Adicionar último chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    print(f"✅ Processados {processed} CIDs em {len(chunks)} chunks")
    return chunks

def update_faiss():
    """Atualiza FAISS com todos os CIDs"""
    
    print("🧠 Atualizando FAISS...")
    
    # Verificar API
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY necessária!")
        return False
    
    client = OpenAI(api_key=api_key)
    
    # Criar chunks
    chunks = create_enhanced_chunks()
    
    if len(chunks) < 10:
        print(f"⚠️ Poucos chunks: {len(chunks)}")
        return False
    
    print(f"📚 Gerando embeddings para {len(chunks)} chunks...")
    
    # Gerar embeddings em lotes
    embeddings = []
    batch_size = 50
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        print(f"🔄 Lote {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
        
        for j, chunk in enumerate(batch):
            try:
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=chunk
                )
                embeddings.append(response.data[0].embedding)
                
                # Progresso
                total_done = i + j + 1
                print(f"   {total_done}/{len(chunks)}", end='\r')
                
            except Exception as e:
                print(f"\n❌ Erro no embedding {i+j+1}: {e}")
                return False
    
    print(f"\n✅ {len(embeddings)} embeddings gerados!")
    
    # Criar índice
    embeddings_array = np.array(embeddings, dtype=np.float32)
    
    # Localizar diretório
    index_dir = "app/index_faiss_openai"
    os.makedirs(index_dir, exist_ok=True)
    
    # Criar novo índice
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_array)
    
    # Salvar
    index_path = os.path.join(index_dir, "index.faiss")
    docs_path = os.path.join(index_dir, "documents.pkl")
    
    faiss.write_index(index, index_path)
    
    with open(docs_path, 'wb') as f:
        pickle.dump(chunks, f)
    
    # Estatísticas
    file_size = os.path.getsize(index_path) / 1024 / 1024
    
    print(f"✅ FAISS COMPLETO atualizado!")
    print(f"📊 Vetores: {index.ntotal}")
    print(f"📄 Documentos: {len(chunks)}")
    print(f"💾 Tamanho: {file_size:.1f} MB")
    print(f"📁 Local: {index_dir}")
    
    return True

if __name__ == "__main__":
    print("🚀 PROCESSAMENTO COMPLETO DE TODOS OS CIDs")
    print("=" * 50)
    
    if update_faiss():
        print("\n🎯 MISSÃO CUMPRIDA!")
        print("✅ Todos os CIDs processados")
        print("🧠 Sistema RAG COMPLETO")
        print("🚀 Classificação universal ativa!")
    else:
        print("\n❌ Falha no processamento")
