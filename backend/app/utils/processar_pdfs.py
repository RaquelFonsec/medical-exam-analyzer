import os
import glob
import hashlib
import json
from datetime import datetime
from PyPDF2 import PdfReader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter

class PDFProcessor:
    def __init__(self):
        # Configura caminhos relativos corretamente
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Pega diretório do script (utils)
        app_dir = os.path.dirname(script_dir)  # Sobe para o diretório app
        self.pdf_dir = os.path.join(app_dir, "relatorios")  # Diretório dos PDFs
        self.index_dir = os.path.join(app_dir, "index_faiss_openai")
        self.state_file = os.path.join(app_dir, "pdf_processing_state.json")
        
        # Verifica e cria diretórios se necessário
        os.makedirs(self.pdf_dir, exist_ok=True)
        os.makedirs(self.index_dir, exist_ok=True)
        
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.state = self._load_state()
        
        # Debug: mostra os caminhos configurados
        print(f"Script location: {__file__}")
        print(f"PDF directory: {self.pdf_dir}")
        print(f"Index directory: {self.index_dir}")

    def _index_exists(self):
        """Verifica se o índice FAISS existe completamente"""
        required_files = ['index.faiss', 'index.pkl']
        return all(os.path.exists(os.path.join(self.index_dir, f)) for f in required_files)

    def _load_state(self):
        """Carrega o estado de processamento anterior"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar estado: {e}")
        return {"processed_files": {}}

    def _save_state(self):
        """Salva o estado atual de processamento"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar estado: {e}")

    def _get_file_hash(self, filepath):
        """Calcula hash do arquivo para detectar alterações"""
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            print(f"Erro ao calcular hash do arquivo {filepath}: {e}")
            return None

    def _is_file_modified(self, filepath):
        """Verifica se o arquivo foi modificado desde o último processamento"""
        filename = os.path.basename(filepath)
        
        if filename not in self.state["processed_files"]:
            return True
            
        try:
            file_stat = os.stat(filepath)
            last_processed = self.state["processed_files"][filename]
            
            current_hash = self._get_file_hash(filepath)
            if current_hash is None:
                return False
                
            return (last_processed["hash"] != current_hash) or \
                   (last_processed["mtime"] < file_stat.st_mtime)
        except Exception as e:
            print(f"Erro ao verificar modificação do arquivo {filename}: {e}")
            return True

    def _read_pdf(self, pdf_path):
        """Lê o conteúdo do PDF"""
        try:
            reader = PdfReader(pdf_path)
            text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
            if not text:
                print(f"Aviso: PDF {os.path.basename(pdf_path)} não contém texto extraível")
            return text
        except Exception as e:
            print(f"Erro ao ler PDF {pdf_path}: {e}")
            return None

    def _create_documents(self, text, source):
        """Cria documentos LangChain"""
        return [Document(
            page_content=text,
            metadata={
                "source": os.path.basename(source),
                "timestamp": datetime.now().isoformat(),
                "file_size": os.path.getsize(source)
            }
        )]

    def _chunk_documents(self, documents):
        """Divide documentos em chunks"""
        text_splitter = CharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separator="\n",
            length_function=len
        )
        return text_splitter.split_documents(documents)

    def _process_pdfs(self, pdf_files, rebuild=False):
        """Processa os PDFs conforme necessário"""
        documents = []
        
        for pdf_path in pdf_files:
            try:
                text = self._read_pdf(pdf_path)
                if text:
                    docs = self._create_documents(text, pdf_path)
                    documents.extend(docs)
                    
            except Exception as e:
                print(f"Erro ao processar {pdf_path}: {e}")
        
        if not documents:
            print("Nenhum documento válido para processar.")
            return None
        
        chunks = self._chunk_documents(documents)
        
        try:
            if not rebuild and self._index_exists():
                vectorstore = FAISS.load_local(
                    self.index_dir,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                vectorstore.add_documents(chunks)
            else:
                vectorstore = FAISS.from_documents(chunks, self.embeddings)
            
            vectorstore.save_local(self.index_dir)
            
            # Atualiza o estado para os arquivos processados
            for pdf_path in pdf_files:
                filename = os.path.basename(pdf_path)
                file_stat = os.stat(pdf_path)
                self.state["processed_files"][filename] = {
                    "hash": self._get_file_hash(pdf_path),
                    "mtime": file_stat.st_mtime,
                    "processed_at": datetime.now().isoformat()
                }
            
            self._save_state()
            print(f"Índice {'recriado' if rebuild else 'atualizado'} com sucesso!")
            return vectorstore
            
        except Exception as e:
            print(f"Erro ao salvar índice: {e}")
            return None

    def process_files(self):
        """Processa arquivos PDF de forma inteligente"""
        pdf_files = glob.glob(os.path.join(self.pdf_dir, "*.pdf"))
        
        if not pdf_files:
            print(f"\nERRO: Nenhum PDF encontrado em: {self.pdf_dir}")
            print("Por favor, coloque os arquivos PDF na pasta 'relatorios' com estrutura:")
            print("\nmedical-exam-analyzer/backend/app/")
            print("├── relatorios/")
            print("│   ├── arquivo1.pdf")
            print("│   └── arquivo2.pdf")
            print("└── utils/")
            print("    └── processar_pdfs.py\n")
            return None
            
        if not self._index_exists():
            print("Índice não encontrado - processando todos os arquivos como novos")
            return self._process_pdfs(pdf_files, rebuild=True)
        
        # Processa apenas arquivos modificados
        modified_files = [f for f in pdf_files if self._is_file_modified(f)]
        if modified_files:
            print(f"Processando {len(modified_files)} arquivo(s) modificado(s)...")
            return self._process_pdfs(modified_files)
        
        print("Nenhum arquivo modificado encontrado.")
        return None

if __name__ == "__main__":
    processor = PDFProcessor()
    processor.process_files()