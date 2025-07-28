from PyPDF2 import PdfReader
import os
import glob
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from dotenv import load_dotenv
import tiktoken # Importar tiktoken
import time # Para adicionar delays em caso de RateLimitError
import openai # Importar openai para lidar com RateLimitError

load_dotenv(override=True)

print("OpenAI API Key:", os.getenv("OPENAI_API_KEY"))

# Definir o limite de tokens por requisição da OpenAI
# text-embedding-3-small e text-embedding-3-large tem um limite de 300,000 tokens por requisição
MAX_TOKENS_PER_OPENAI_REQUEST = 300000 
EMBEDDING_MODEL = "text-embedding-3-small" # Definir o modelo de embedding

# Função para contar tokens usando tiktoken (mais precisa)
def num_tokens_from_string(string: str, model_name: str = EMBEDDING_MODEL) -> int:
    """Retorna o número de tokens em uma string para um determinado modelo."""
    encoding = tiktoken.encoding_for_model(model_name)
    return len(encoding.encode(string))

def get_relative_path(relative_path):
    """Resolve caminhos relativos de forma confiável"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(script_dir, relative_path))

def ler_pdf(pdf_path):
    """Lê o conteúdo de um arquivo PDF e retorna como texto"""
    try:
        reader = PdfReader(pdf_path)
        # Extrair texto de cada página, ignorando páginas vazias
        text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        return text
    except Exception as e:
        print(f"Erro ao ler o PDF {pdf_path}: {e}")
        return ""

def ler_txt(txt_path):
    """Lê o conteúdo de um arquivo TXT e retorna como texto"""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Erro ao ler o TXT {txt_path}: {e}")
        return ""

def criar_chunks(docs_dir):
    """Processa arquivos (PDFs e TXTs) e cria chunks para RAG"""
    documents = []
    
    # Processa PDFs
    for pdf_path in glob.glob(os.path.join(docs_dir, '*.pdf')):
        try:
            text = ler_pdf(pdf_path)
            print(f"Lendo arquivo PDF: {os.path.basename(pdf_path)}")
            if text:
                doc = Document(
                    page_content=text,
                    metadata={
                        "source": os.path.basename(pdf_path),
                        "type": "pdf"
                    }
                )
                documents.append(doc)
        except Exception as e:
            print(f"Erro ao processar PDF {os.path.basename(pdf_path)}: {e}")
    
    # Processa TXTs
    for txt_path in glob.glob(os.path.join(docs_dir, '*.txt')):
        try:
            text = ler_txt(txt_path)
            print(f"Lendo arquivo TXT: {os.path.basename(txt_path)}")
            if text:
                doc = Document(
                    page_content=text,
                    metadata={
                        "source": os.path.basename(txt_path),
                        "type": "txt"
                    }
                )
                documents.append(doc)
        except Exception as e:
            print(f"Erro ao processar TXT {os.path.basename(txt_path)}: {e}")
    
    # Configuração do splitter de texto
    # chunk_size e chunk_overlap devem ser ajustados de acordo com o tamanho típico das descrições de CID
    # Para CID, talvez um chunk_size menor ou até mesmo 0 overlap se cada chunk for uma descrição completa
    # Se o PDF tem múltiplas CIDs por linha, e você quer cada CID como um chunk, a lógica de parseamento
    # no ler_pdf precisaria ser mais sofisticada (ex: regex para separar cada CID)
    text_splitter = CharacterTextSplitter(
        chunk_size=1000, # Ajuste este valor conforme o tamanho do seu conteúdo de texto.
                         # Para CIDs, se você não parserar linha por linha, o chunk pode ser grande.
        chunk_overlap=200,
        separator="\n" # Assumindo que CIDs estão separados por linhas
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Total de chunks criados: {len(chunks)}")
    return chunks

def main():
    # Configura caminhos relativos
    docs_relative_path = "../relatorios"
    docs_dir = get_relative_path(docs_relative_path)
    
    db_name = get_relative_path("../index_faiss_openai")
    
    print(f"Procurando documentos em: {docs_dir}")
    
    # Verifica se o diretório existe
    if not os.path.exists(docs_dir):
        print(f"Diretório não encontrado: {docs_dir}")
        return
    
    # Cria chunks dos documentos
    chunks = criar_chunks(docs_dir)
    
    if not chunks:
        print("Nenhum chunk foi criado. Verifique os arquivos.")
        return
    
    # Inicializa o objeto de embeddings
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    
    print("Criando vetores e armazenando no FAISS em lotes para evitar limite de tokens...")
    
    # Inicializa o FAISS vazio ou carrega um existente se já houver
    vectorstore = None
    
    current_batch_docs = []
    current_batch_tokens = 0
    total_chunks_processed = 0

    # Iterar sobre os chunks e enviar em lotes
    for i, chunk in enumerate(chunks):
        chunk_text = chunk.page_content
        chunk_tokens = num_tokens_from_string(chunk_text, EMBEDDING_MODEL)

        # Verificar se adicionar este chunk excederá o limite
        if current_batch_tokens + chunk_tokens > MAX_TOKENS_PER_OPENAI_REQUEST:
            print(f"Enviando lote de {len(current_batch_docs)} chunks ({current_batch_tokens} tokens) para a OpenAI...")
            try:
                if vectorstore is None:
                    # Se for o primeiro lote, crie a vectorstore
                    vectorstore = FAISS.from_documents(current_batch_docs, embedding=embeddings)
                    print(f"Vectorstore FAISS criada com {len(current_batch_docs)} documentos.")
                else:
                    # Se não for o primeiro, adicione os documentos
                    vectorstore.add_documents(current_batch_docs)
                    print(f"Adicionados {len(current_batch_docs)} documentos ao FAISS. Total no FAISS: {vectorstore.index.ntotal}")

            except openai.RateLimitError:
                print("Limite de taxa da OpenAI atingido. Esperando 60 segundos...")
                time.sleep(60)
                # Tentar re-enviar o mesmo lote
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(current_batch_docs, embedding=embeddings)
                else:
                    vectorstore.add_documents(current_batch_docs)
                print(f"Lote reprocessado após espera. Adicionados {len(current_batch_docs)} documentos ao FAISS.")
            except Exception as e:
                print(f"Erro ao adicionar lote de documentos ao FAISS: {e}")
                # Dependendo do erro, você pode querer tentar novamente ou pular
                break # Para o processo em caso de erro grave

            # Resetar o lote atual
            current_batch_docs = []
            current_batch_tokens = 0
            
        # Adicionar o chunk atual ao lote
        current_batch_docs.append(chunk)
        current_batch_tokens += chunk_tokens
        total_chunks_processed += 1
        print(f"Adicionando chunk {i+1}/{len(chunks)} ao lote. Tokens no lote: {current_batch_tokens}")

    # Processar quaisquer chunks restantes no último lote
    if current_batch_docs:
        print(f"Enviando lote final de {len(current_batch_docs)} chunks ({current_batch_tokens} tokens) para a OpenAI...")
        try:
            if vectorstore is None:
                vectorstore = FAISS.from_documents(current_batch_docs, embedding=embeddings)
                print(f"Vectorstore FAISS criada com o lote final de {len(current_batch_docs)} documentos.")
            else:
                vectorstore.add_documents(current_batch_docs)
                print(f"Adicionados {len(current_batch_docs)} documentos ao FAISS (lote final). Total no FAISS: {vectorstore.index.ntotal}")
        except Exception as e:
            print(f"Erro ao adicionar lote final de documentos ao FAISS: {e}")

    if vectorstore:
        vectorstore.save_local(db_name)
        print(f"Índice FAISS salvo em: {db_name}")
    else:
        print("Nenhum vectorstore foi criado. Verifique os logs de erro.")

if __name__ == "__main__":
    main()