from PyPDF2 import PdfReader
import os
import glob
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

def get_relative_path(relative_path):
    """Resolve caminhos relativos de forma confiável"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(script_dir, relative_path))

def ler_pdf(pdf_path):
    """Lê o conteúdo de um arquivo PDF e retorna como texto"""
    try:
        reader = PdfReader(pdf_path)
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
            print(f"Lendo arquivo PDF: {pdf_path}")
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
            print(f"Erro ao processar PDF {pdf_path}: {e}")
    
    # Processa TXTs
    for txt_path in glob.glob(os.path.join(docs_dir, '*.txt')):
        try:
            text = ler_txt(txt_path)
            print(f"Lendo arquivo TXT: {txt_path}")
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
            print(f"Erro ao processar TXT {txt_path}: {e}")
    
    # Configuração do splitter de texto
    text_splitter = CharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separator="\n"
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
    
    # Cria embeddings e armazena no FAISS
    print("Criando vetores e armazenando...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_documents(chunks, embedding=embeddings)
    vectorstore.save_local(db_name)
    print(f"Índice FAISS salvo em: {db_name}")

if __name__ == "__main__":
    main()