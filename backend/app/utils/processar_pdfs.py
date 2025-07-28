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
from dotenv import load_dotenv
import tiktoken
import time

load_dotenv(override=True)

class PDFTXTProcessor: # Renomeada a classe para ser mais descritiva
    MAX_TOKENS_PER_OPENAI_REQUEST = 300000 
    EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(script_dir)
        backend_dir = os.path.dirname(app_dir)
        self.project_root = os.path.dirname(backend_dir) # Guarda a raiz do projeto

        self.docs_dir = os.path.join(self.project_root, "relatorios") 
        self.index_dir = os.path.join(self.project_root, "index_faiss_openai")
        self.state_file = os.path.join(app_dir, "pdf_processing_state.json") # Mantém o estado no app_dir
        
        os.makedirs(self.docs_dir, exist_ok=True)
        os.makedirs(self.index_dir, exist_ok=True)
        
        self.embeddings = OpenAIEmbeddings(model=self.EMBEDDING_MODEL)
        self.state = self._load_state()
        
        print(f"Script location: {__file__}")
        print(f"Documents directory: {self.docs_dir}")
        print(f"Index directory: {self.index_dir}")
        print(f"State file: {self.state_file}")

    def _num_tokens_from_string(self, string: str) -> int:
        encoding = tiktoken.encoding_for_model(self.EMBEDDING_MODEL)
        return len(encoding.encode(string))

    def _index_exists(self):
        required_files = ['index.faiss', 'index.pkl']
        return all(os.path.exists(os.path.join(self.index_dir, f)) for f in required_files)

    def _load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar estado: {e}")
        return {"processed_files": {}}

    def _save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar estado: {e}")

    def _get_file_hash(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            print(f"Erro ao calcular hash do arquivo {filepath}: {e}")
            return None

    def _is_file_modified(self, filepath):
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

    def _read_pdf_and_convert_to_txt(self, pdf_path):
        """Lê o conteúdo do PDF, extrai texto e o salva como um arquivo TXT."""
        txt_output_path = os.path.splitext(pdf_path)[0] + ".txt"
        pdf_filename = os.path.basename(pdf_path)
        txt_filename = os.path.basename(txt_output_path)

        # Checa se o PDF original foi modificado ou se o TXT correspondente não existe/está desatualizado
        pdf_hash = self._get_file_hash(pdf_path)
        pdf_mtime = os.stat(pdf_path).st_mtime

        should_convert = False
        if txt_filename not in self.state["processed_files"]:
            should_convert = True # TXT correspondente não foi processado antes
        else:
            # Verifica se o PDF é mais novo ou se o hash do PDF mudou
            last_processed_pdf_info = self.state["processed_files"].get(pdf_filename, {})
            if last_processed_pdf_info.get("hash") != pdf_hash or \
               last_processed_pdf_info.get("mtime") < pdf_mtime:
               should_convert = True # PDF original foi modificado

        if should_convert:
            print(f"Convertendo PDF: {pdf_filename} para TXT: {txt_filename}...")
            try:
                reader = PdfReader(pdf_path)
                text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
                
                if not text:
                    print(f"Aviso: PDF {pdf_filename} não contém texto extraível. Nenhum TXT será gerado.")
                    return None # Retorna None se não houver texto para salvar
                
                with open(txt_output_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"Conversão de {pdf_filename} concluída. TXT salvo em {txt_output_path}")

                # Atualiza o estado para o PDF original, indicando que ele foi processado para conversão
                self.state["processed_files"][pdf_filename] = {
                    "hash": pdf_hash,
                    "mtime": pdf_mtime,
                    "processed_at": datetime.now().isoformat()
                }
                return txt_output_path # Retorna o caminho do TXT gerado
            except Exception as e:
                print(f"Erro ao converter PDF {pdf_filename}: {e}")
                return None
        else:
            print(f"PDF {pdf_filename} não modificado, usando TXT existente: {txt_filename}")
            return txt_output_path if os.path.exists(txt_output_path) else None # Retorna o TXT existente se ele já existir

    def _read_txt(self, txt_path):
        """Lê o conteúdo de um arquivo TXT e retorna como texto"""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Erro ao ler TXT {txt_path}: {e}")
            return None

    def _create_documents(self, text, source, file_type):
        """Cria documentos LangChain, incluindo o tipo de arquivo nos metadados"""
        return [Document(
            page_content=text,
            metadata={
                "source": os.path.basename(source),
                "timestamp": datetime.now().isoformat(),
                "file_size": os.path.getsize(source),
                "file_type": file_type
            }
        )]

    def _chunk_documents(self, documents):
        text_splitter = CharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separator="\n",
            length_function=len
        )
        return text_splitter.split_documents(documents)

    def _process_text_files(self, text_files_to_index, rebuild=False): # Agora só processa TXT
        all_chunks = []
        
        for file_path in text_files_to_index:
            try:
                # Sempre será um TXT aqui, já que a filtragem acontece antes
                text = self._read_txt(file_path)
                file_type = "txt"

                if text:
                    docs = self._create_documents(text, file_path, file_type)
                    chunks_from_file = self._chunk_documents(docs)
                    all_chunks.extend(chunks_from_file)
                    print(f"Lido e chunkado {len(chunks_from_file)} chunks de {os.path.basename(file_path)} (TXT)")
                
            except Exception as e:
                print(f"Erro ao processar {os.path.basename(file_path)}: {e}")
        
        if not all_chunks:
            print("Nenhum chunk válido para processar.")
            return None
        
        print(f"Total de chunks TXT a serem processados para indexing: {len(all_chunks)}")

        vectorstore = None
        if not rebuild and self._index_exists():
            try:
                vectorstore = FAISS.load_local(
                    self.index_dir,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"Índice FAISS existente carregado de: {self.index_dir}")
            except Exception as e:
                print(f"Erro ao carregar índice FAISS existente: {e}. Reconstruindo índice.")
                vectorstore = None 

        current_batch_docs = []
        current_batch_tokens = 0

        for i, chunk in enumerate(all_chunks):
            chunk_text = chunk.page_content
            chunk_tokens = self._num_tokens_from_string(chunk_text)

            if current_batch_tokens + chunk_tokens > self.MAX_TOKENS_PER_OPENAI_REQUEST:
                print(f"  Enviando lote de {len(current_batch_docs)} chunks ({current_batch_tokens} tokens) para a OpenAI...")
                try:
                    if vectorstore is None:
                        vectorstore = FAISS.from_documents(current_batch_docs, embedding=self.embeddings)
                        print(f"  Vectorstore FAISS criada com {len(current_batch_docs)} documentos.")
                    else:
                        vectorstore.add_documents(current_batch_docs)
                        print(f"  Adicionados {len(current_batch_docs)} documentos ao FAISS. Total no FAISS: {vectorstore.index.ntotal}")

                except Exception as e:
                    print(f"  Erro ao adicionar lote de documentos ao FAISS: {e}")
                    if "RateLimitError" in str(e):
                        print("  Limite de taxa da OpenAI atingido. Esperando 60 segundos antes de tentar novamente o mesmo lote...")
                        time.sleep(60)
                        try:
                            if vectorstore is None:
                                vectorstore = FAISS.from_documents(current_batch_docs, embedding=self.embeddings)
                            else:
                                vectorstore.add_documents(current_batch_docs)
                            print(f"  Lote reprocessado após espera. Adicionados {len(current_batch_docs)} documentos ao FAISS.")
                        except Exception as retry_e:
                            print(f"  Erro persistente após re-tentativa: {retry_e}. Pulando este lote.")
                    else:
                        print("  Erro não relacionado a limite de taxa. Pulando este lote.")
                    current_batch_docs = []
                    current_batch_tokens = 0
                    continue 

                current_batch_docs = []
                current_batch_tokens = 0
            
            current_batch_docs.append(chunk)
            current_batch_tokens += chunk_tokens

        if current_batch_docs:
            print(f"  Enviando lote final de {len(current_batch_docs)} chunks ({current_batch_tokens} tokens) para a OpenAI...")
            try:
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(current_batch_docs, embedding=self.embeddings)
                    print(f"  Vectorstore FAISS criada com o lote final de {len(current_batch_docs)} documentos.")
                else:
                    vectorstore.add_documents(current_batch_docs)
                    print(f"  Adicionados {len(current_batch_docs)} documentos ao FAISS (lote final). Total in FAISS: {vectorstore.index.ntotal}")
            except Exception as e:
                print(f"  Erro ao adicionar lote final de documentos ao FAISS: {e}")
                if "RateLimitError" in str(e):
                    print("  Limite de taxa da OpenAI atingido no lote final. Esperando 60 segundos...")
                    time.sleep(60)
                    try:
                        if vectorstore is None:
                            vectorstore = FAISS.from_documents(current_batch_docs, embedding=self.embeddings)
                        else:
                            vectorstore.add_documents(current_batch_docs)
                        print(f"  Lote final reprocessado após espera. Adicionados {len(current_batch_docs)} documentos ao FAISS.")
                    except Exception as retry_e:
                        print(f"  Erro persistente no lote final após re-tentativa: {retry_e}.")
                else:
                    print("  Erro não relacionado a limite de taxa no lote final.")

        if vectorstore:
            vectorstore.save_local(self.index_dir)
            
            # Atualiza o estado para os arquivos TXT que foram efetivamente indexados
            for file_path in text_files_to_index:
                filename = os.path.basename(file_path)
                file_stat = os.stat(file_path)
                self.state["processed_files"][filename] = {
                    "hash": self._get_file_hash(file_path),
                    "mtime": file_stat.st_mtime,
                    "processed_at": datetime.now().isoformat()
                }
            self._save_state()
            print(f"Índice {'recriado' if rebuild else 'atualizado'} com sucesso! Total de chunks no índice: {vectorstore.index.ntotal}")
            return vectorstore
        else:
            print("Nenhum vectorstore criado ou atualizado. Verifique os logs de erro.")
            return None

    def process_all_documents(self):
        """
        Processa PDFs (convertendo para TXT) e TXTs (diretamente),
        e então indexa todos os TXTs novos/modificados.
        """
        
        print("\n--- Etapa 1: Conversão de PDFs para TXT ---")
        pdf_files = glob.glob(os.path.join(self.docs_dir, "*.pdf"))
        converted_txt_paths = []
        for pdf_path in pdf_files:
            txt_path = self._read_pdf_and_convert_to_txt(pdf_path)
            if txt_path:
                converted_txt_paths.append(txt_path)
        
        # Após a conversão, coletamos TODOS os TXTs presentes no diretório,
        # sejam eles originais ou recém-convertidos.
        print("\n--- Etapa 2: Coletando todos os arquivos TXT para Indexação ---")
        all_txt_files = glob.glob(os.path.join(self.docs_dir, "*.txt"))
        
        if not all_txt_files:
            print(f"\nERRO: Nenhum arquivo TXT (original ou convertido) encontrado em: {self.docs_dir}")
            print("Por favor, garanta que há PDFs para conversão ou TXTs diretamente na pasta 'relatorios'.")
            return None
            
        # Determinar quais arquivos TXT precisam ser indexados (novos ou modificados)
        text_files_to_index = [f for f in all_txt_files if self._is_file_modified(f)]

        if not self._index_exists():
            print("Índice não encontrado - processando todos os arquivos TXT para recriação.")
            # Se o índice não existe, processamos todos os TXTs
            return self._process_text_files(all_txt_files, rebuild=True) 
        
        if text_files_to_index:
            print(f"Processando {len(text_files_to_index)} arquivo(s) TXT novo(s) ou modificado(s) para indexação...")
            return self._process_text_files(text_files_to_index) 
        
        print("Nenhum arquivo TXT novo ou modificado encontrado. O índice está atualizado.")
        return None

if __name__ == "__main__":
    processor = PDFTXTProcessor() # Instancia a classe renomeada
    processor.process_all_documents()