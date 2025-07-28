import os
import sys
import pickle
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

def extrair_texto_pdf(caminho_pdf):
    """Extrair texto de PDF usando diferentes métodos"""
    try:
        # Tentar com PyPDF2 primeiro
        import PyPDF2
        with open(caminho_pdf, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            texto = ""
            for page in reader.pages:
                texto += page.extract_text() + "\n"
        return texto.strip()
    except:
        try:
            # Tentar com pdfplumber
            import pdfplumber
            with pdfplumber.open(caminho_pdf) as pdf:
                texto = ""
                for page in pdf.pages:
                    texto += page.extract_text() + "\n"
            return texto.strip()
        except:
            try:
                # Tentar com pymupdf
                import fitz
                doc = fitz.open(caminho_pdf)
                texto = ""
                for page in doc:
                    texto += page.get_text()
                return texto.strip()
            except:
                return None

def processar_pdfs_medicos():
    """Processar PDFs médicos e adicionar ao RAG"""
    
    print("🚀 Processando PDFs médicos...")
    
    # Encontrar todos os PDFs de relatórios
    pdfs_encontrados = []
    
    # Procurar em várias pastas
    diretorios = [
        'relatorios/',
        '../relatorios/',
        '../../relatorios/',
        '../../backend/relatorios/'
    ]
    
    for diretorio in diretorios:
        if os.path.exists(diretorio):
            for arquivo in os.listdir(diretorio):
                if arquivo.lower().endswith('.pdf') and ('relat' in arquivo.lower() or 'laudo' in arquivo.lower()):
                    caminho_completo = os.path.join(diretorio, arquivo)
                    pdfs_encontrados.append(caminho_completo)
    
    print(f"📄 Encontrados {len(pdfs_encontrados)} PDFs médicos:")
    for pdf in pdfs_encontrados:
        print(f"  - {os.path.basename(pdf)}")
    
    if not pdfs_encontrados:
        print("❌ Nenhum PDF encontrado")
        return 0
    
    # Instalar dependências se necessário
    try:
        import PyPDF2
    except ImportError:
        print("⚠️ Instalando PyPDF2...")
        os.system("pip install PyPDF2")
    
    # Processar cada PDF
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    novos_documentos = []
    novos_embeddings = []
    
    for i, pdf_path in enumerate(pdfs_encontrados):
        print(f"\n📖 Processando {i+1}/{len(pdfs_encontrados)}: {os.path.basename(pdf_path)}")
        
        # Extrair texto
        texto = extrair_texto_pdf(pdf_path)
        
        if texto and len(texto.strip()) > 100:
            print(f"✅ Texto extraído: {len(texto)} caracteres")
            
            # Criar documento estruturado
            nome_arquivo = os.path.basename(pdf_path)
            documento = f"ARQUIVO PDF: {nome_arquivo}\n{texto}"
            novos_documentos.append(documento)
            
            # Gerar embedding
            try:
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texto[:8000]  # Limitar tamanho
                )
                
                embedding = response.data[0].embedding
                novos_embeddings.append(embedding)
                
                print(f"✅ Embedding gerado (dimensão: {len(embedding)})")
                
            except Exception as e:
                print(f"❌ Erro ao gerar embedding: {e}")
                novos_documentos.pop()  # Remove o documento se não conseguiu gerar embedding
        else:
            print(f"❌ Não foi possível extrair texto ou texto muito pequeno")
    
    # Adicionar aos índices existentes
    if novos_embeddings:
        print(f"\n🔄 Adicionando {len(novos_embeddings)} novos documentos ao RAG...")
        
        try:
            import faiss
            
            # Carregar índice existente
            index_existente = faiss.read_index('index_faiss_openai/index.faiss')
            
            with open('index_faiss_openai/documents.pkl', 'rb') as f:
                documentos_existentes = pickle.load(f)
            
            print(f"📊 Índice atual: {index_existente.ntotal} vetores")
            
            # Preparar novos embeddings
            novos_embeddings_array = np.array(novos_embeddings, dtype=np.float32)
            faiss.normalize_L2(novos_embeddings_array)
            
            # Adicionar ao índice
            index_existente.add(novos_embeddings_array)
            
            # Combinar documentos
            todos_documentos = documentos_existentes + novos_documentos
            
            # Salvar índice atualizado
            faiss.write_index(index_existente, 'index_faiss_openai/index.faiss')
            
            with open('index_faiss_openai/documents.pkl', 'wb') as f:
                pickle.dump(todos_documentos, f)
            
            print(f"✅ RAG atualizado com sucesso!")
            print(f"  Total de vetores: {index_existente.ntotal}")
            print(f"  Total de documentos: {len(todos_documentos)}")
            
            return len(novos_embeddings)
            
        except Exception as e:
            print(f"❌ Erro ao atualizar RAG: {e}")
            return 0
    else:
        print("❌ Nenhum embedding foi gerado")
        return 0

if __name__ == "__main__":
    total = processar_pdfs_medicos()
    print(f"\n🎉 Processamento concluído: {total} PDFs adicionados ao RAG!")
