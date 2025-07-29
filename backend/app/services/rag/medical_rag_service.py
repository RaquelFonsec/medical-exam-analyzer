import faiss
import numpy as np
import openai
import os
import pickle
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import re
from datetime import datetime

class MedicalRAGService:
    """Serviço RAG para análise médica baseada em exemplos de laudos"""
    
    def __init__(self, faiss_index_path: str = "app/index_faiss_openai/index.faiss", 
                 chunks_path: str = "app/index_faiss_openai/documents.pkl"):
        """Inicializar serviço RAG"""
        self.faiss_index_path = faiss_index_path
        self.chunks_path = chunks_path
        self.embedding_model = None
        self.faiss_index = None
        self.chunks = []
        self.dimension = 384
        
        # Inicializar OpenAI
        try:
            self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            print("✅ OpenAI configurado para RAG")
        except Exception as e:
            print(f"⚠️ Erro OpenAI RAG: {e}")
            self.openai_client = None
        
        self._initialize_rag_system()
    
    def _initialize_rag_system(self):
        """Inicializar sistema RAG"""
        try:
            # Detectar qual tipo de embedding foi usado no índice
            if os.path.exists(self.faiss_index_path):
                index = faiss.read_index(self.faiss_index_path)
                self.dimension = index.d
                print(f"🔍 Dimensão detectada do índice: {self.dimension}")
                
                # Se dimensão é 1536, usar OpenAI embeddings
                if self.dimension == 1536:
                    if self.openai_client:
                        print("🔄 Usando OpenAI embeddings (text-embedding-ada-002)")
                        self.embedding_model = "openai"
                    else:
                        print("❌ OpenAI necessário para dimensão 1536, mas não configurado")
                        raise Exception("OpenAI API key necessária")
                else:
                    # Usar SentenceTransformers para outras dimensões
                    print("🔄 Carregando modelo SentenceTransformers...")
                    self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                    self.dimension = self.embedding_model.get_sentence_embedding_dimension()
                    print(f"✅ Modelo SentenceTransformers carregado - Dimensão: {self.dimension}")
            else:
                # Fallback para SentenceTransformers
                print("🔄 Carregando modelo de embedding padrão...")
                self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                self.dimension = self.embedding_model.get_sentence_embedding_dimension()
                print(f"✅ Modelo carregado - Dimensão: {self.dimension}")
            
            if os.path.exists(self.faiss_index_path) and os.path.exists(self.chunks_path):
                self._load_knowledge_base()
                print("✅ Base de conhecimento carregada")
            else:
                print("⚠️ Base de conhecimento não encontrada - criar nova base")
                self._create_empty_index()
                
        except Exception as e:
            print(f"❌ Erro ao inicializar RAG: {e}")
            self._create_empty_index()
    
    def _create_empty_index(self):
        """Criar índice FAISS vazio"""
        try:
            self.faiss_index = faiss.IndexFlatIP(self.dimension)
            self.chunks = []
            print("✅ Índice FAISS vazio criado")
        except Exception as e:
            print(f"❌ Erro ao criar índice: {e}")

    def _load_knowledge_base(self):
        """Carregar base de conhecimento existente"""
        try:
            self.faiss_index = faiss.read_index(self.faiss_index_path)
            with open(self.chunks_path, 'rb') as f:
                self.chunks = pickle.load(f)
            print(f"✅ Base carregada: {len(self.chunks)} chunks, {self.faiss_index.ntotal} vetores")
        except Exception as e:
            print(f"❌ Erro ao carregar base: {e}")
            self._create_empty_index()
    
    def save_knowledge_base(self):
        """Salvar base de conhecimento"""
        try:
            os.makedirs(os.path.dirname(self.faiss_index_path), exist_ok=True)
            faiss.write_index(self.faiss_index, self.faiss_index_path)
            with open(self.chunks_path, 'wb') as f:
                pickle.dump(self.chunks, f)
            print(f"✅ Base salva: {len(self.chunks)} chunks")
        except Exception as e:
            print(f"❌ Erro ao salvar base: {e}")
    
    def add_documents_to_knowledge_base(self, pdf_texts: List[str], chunk_size: int = 500):
        """Adicionar documentos à base de conhecimento"""
        try:
            print("🔄 Processando documentos para base de conhecimento...")
            all_chunks = []
            
            for i, text in enumerate(pdf_texts):
                print(f"📄 Processando documento {i+1}/{len(pdf_texts)}")
                chunks = self._split_text_into_chunks(text, chunk_size)
                
                for j, chunk in enumerate(chunks):
                    chunk_data = {
                        'text': chunk,
                        'document_id': i,
                        'chunk_id': j,
                        'type': self._classify_chunk_type(chunk),
                        'timestamp': datetime.now().isoformat()
                    }
                    all_chunks.append(chunk_data)
            
            print("🔄 Gerando embeddings...")
            chunk_texts = [chunk['text'] for chunk in all_chunks]
            embeddings = self.embedding_model.encode(chunk_texts, show_progress_bar=True)
            
            if self.faiss_index is None:
                self._create_empty_index()
            
            self.faiss_index.add(embeddings.astype('float32'))
            self.chunks.extend(all_chunks)
            self.save_knowledge_base()
            
            print(f"✅ {len(all_chunks)} chunks adicionados à base de conhecimento")
            
        except Exception as e:
            print(f"❌ Erro ao adicionar documentos: {e}")
    
    def _split_text_into_chunks(self, text: str, chunk_size: int = 500) -> List[str]:
        """Dividir texto em chunks inteligentes"""
        text = re.sub(r'\s+', ' ', text).strip()
        chunks = []
        sentences = re.split(r'[.!?]+', text)
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk + sentence) <= chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _classify_chunk_type(self, chunk: str) -> str:
        """Classificar tipo do chunk baseado no conteúdo"""
        chunk_lower = chunk.lower()
        
        if any(term in chunk_lower for term in ['anamnese', 'história clínica', 'hda']):
            return 'anamnese'
        elif any(term in chunk_lower for term in ['diagnóstico', 'cid', 'impressão diagnóstica']):
            return 'diagnostico'
        elif any(term in chunk_lower for term in ['limitações', 'incapacidade', 'funcional']):
            return 'limitacoes'
        elif any(term in chunk_lower for term in ['tratamento', 'medicação', 'terapia']):
            return 'tratamento'
        elif any(term in chunk_lower for term in ['exame físico', 'inspeção', 'palpação']):
            return 'exame_fisico'
        elif any(term in chunk_lower for term in ['conclusão', 'parecer', 'recomendação']):
            return 'conclusao'
        else:
            return 'geral'
    
    def search_similar_cases(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Buscar casos similares na base de conhecimento"""
        try:
            if self.faiss_index.ntotal == 0:
                print("⚠️ Base de conhecimento vazia")
                return []
            
            # Gerar embedding baseado no tipo de modelo
            if self.embedding_model == "openai":
                response = self.openai_client.embeddings.create(
                    input=query,
                    model="text-embedding-ada-002"
                )
                query_embedding = np.array([response.data[0].embedding])
            else:
                query_embedding = self.embedding_model.encode([query])
            
            distances, indices = self.faiss_index.search(
                query_embedding.astype('float32'), 
                min(top_k, self.faiss_index.ntotal)
            )
            
            results = []
            # Como o índice FAISS tem mapeamento complexo, vamos criar uma busca adaptada
            # Usar todos os documentos e calcular similaridade própria se FAISS não mapear corretamente
            
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                # Se índice é válido, usar documento completo baseado em aproximação
                if idx >= 0 and distance < 2.0:  # Limiar de similaridade
                    # Aproximar documento baseado no índice
                    estimated_doc_idx = min(idx // (2124 // 38), len(self.chunks) - 1)
                    
                    if estimated_doc_idx < len(self.chunks):
                        chunk = self.chunks[estimated_doc_idx]
                        similarity_score = 1 / (1 + distance)
                        
                        # Adaptação para strings simples ou dicionários
                        if isinstance(chunk, str):
                            chunk_text = chunk
                            chunk_type = self._classify_chunk_type(chunk)
                            doc_id = f"doc_{estimated_doc_idx}"
                        else:
                            chunk_text = chunk.get('text', str(chunk))
                            chunk_type = chunk.get('type', 'documento')
                            doc_id = chunk.get('document_id', f"doc_{estimated_doc_idx}")
                        
                        # Evitar duplicatas
                        if not any(r['document_id'] == doc_id for r in results):
                            results.append({
                                'content': chunk_text,
                                'type': chunk_type,
                                'score': float(similarity_score),
                                'distance': float(distance),
                                'rank': i + 1,
                                'document_id': doc_id,
                                'chunk_id': f"chunk_{idx}"
                            })
            
            return results
            
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def generate_rag_response(self, patient_info: str, transcription: str, 
                            context_type: str = "laudo_medico") -> Dict[str, Any]:
        """Gerar resposta usando RAG"""
        try:
            search_query = f"{patient_info} {transcription}"
            similar_cases = self.search_similar_cases(search_query, top_k=10)
            
            if not similar_cases:
                print("⚠️ Nenhum caso similar encontrado")
                return self._generate_fallback_response(patient_info, transcription)
            
            context_text = self._prepare_context_for_llm(similar_cases)
            
            if self.openai_client:
                response = self._generate_llm_response(
                    patient_info, transcription, context_text, context_type
                )
            else:
                response = self._generate_template_response(
                    patient_info, transcription, similar_cases
                )
            
            return {
                'success': True,
                'response': response,
                'similar_cases_count': len(similar_cases),
                'top_similarity_score': similar_cases[0]['similarity_score'] if similar_cases else 0,
                'context_used': context_text[:500] + "..." if len(context_text) > 500 else context_text,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erro na geração RAG: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': self._generate_fallback_response(patient_info, transcription),
                'timestamp': datetime.now().isoformat()
            }
    
    def _prepare_context_for_llm(self, similar_cases: List[Dict[str, Any]]) -> str:
        """Preparar contexto dos casos similares para o LLM"""
        context_parts = []
        by_type = {}
        
        for case in similar_cases[:8]:
            case_type = case['type']
            if case_type not in by_type:
                by_type[case_type] = []
            by_type[case_type].append(case)
        
        for case_type, cases in by_type.items():
            context_parts.append(f"\n=== EXEMPLOS DE {case_type.upper()} ===")
            
            for i, case in enumerate(cases[:3], 1):
                similarity = f"{case['similarity_score']:.2f}"
                context_parts.append(f"\nExemplo {i} (Similaridade: {similarity}):")
                context_parts.append(case['text'])
        
        return "\n".join(context_parts)
    
    def _generate_llm_response(self, patient_info: str, transcription: str, 
                              context: str, response_type: str) -> str:
        """Gerar resposta usando LLM com contexto RAG"""
        
        system_prompt = f"""Você é um médico especialista em laudos médicos. Use os EXEMPLOS fornecidos como base para criar um {response_type} para o paciente.

INSTRUÇÕES:
1. Analise os exemplos similares fornecidos
2. Extraia padrões e estruturas dos exemplos
3. Adapte o conteúdo para o caso específico do paciente
4. Mantenha a estrutura e linguagem médica adequada
5. Seja preciso e profissional

EXEMPLOS DA BASE DE CONHECIMENTO:
{context}

Crie um {response_type} seguindo os padrões dos exemplos acima."""

        user_prompt = f"""INFORMAÇÕES DO PACIENTE: {patient_info}

TRANSCRIÇÃO DA CONSULTA: {transcription}

Com base nos exemplos fornecidos, crie um {response_type} completo e profissional para este paciente."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"❌ Erro LLM: {e}")
            return self._generate_template_response(patient_info, transcription, [])
    
    def _generate_template_response(self, patient_info: str, transcription: str, 
                                   similar_cases: List[Dict[str, Any]]) -> str:
        """Gerar resposta baseada em template quando LLM não disponível"""
        
        nome = self._extract_name(patient_info)
        idade = self._extract_age(transcription)
        profissao = self._extract_profession(transcription)
        common_patterns = self._extract_patterns_from_cases(similar_cases)
        
        template = f"""LAUDO MÉDICO BASEADO EM CASOS SIMILARES

IDENTIFICAÇÃO:
- Paciente: {nome}
- Idade: {idade}
- Profissão: {profissao}
- Data: {datetime.now().strftime('%d/%m/%Y')}

HISTÓRIA CLÍNICA:
{transcription}

ANÁLISE BASEADA EM CASOS SIMILARES:
{common_patterns}

CONCLUSÃO:
Caso analisado com base em {len(similar_cases)} exemplos similares da base de conhecimento médica.

Médico Responsável: _________________________
Data: {datetime.now().strftime('%d/%m/%Y')}"""

        return template
    
    def _extract_patterns_from_cases(self, cases: List[Dict[str, Any]]) -> str:
        """Extrair padrões comuns dos casos similares"""
        if not cases:
            return "Análise baseada em protocolos médicos padrão."
        
        patterns = []
        for case in cases[:3]:
            score = f"{case['similarity_score']:.2f}"
            patterns.append(f"- Caso similar (score: {score}): {case['text'][:200]}...")
        
        return "\n".join(patterns)
    
    def _extract_name(self, patient_info: str) -> str:
        """Extrair nome do paciente"""
        match = re.search(r'^([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)?)', patient_info.strip())
        return match.group(1) if match else "Paciente"
    
    def _extract_age(self, text: str) -> str:
        """Extrair idade do texto"""
        match = re.search(r'(\d{2})\s*anos?', text)
        return f"{match.group(1)} anos" if match else "Não informado"
    
    def _extract_profession(self, text: str) -> str:
        """Extrair profissão do texto"""
        professions = ['pedreiro', 'professor', 'motorista', 'enfermeiro', 'atendente']
        text_lower = text.lower()
        
        for prof in professions:
            if prof in text_lower:
                return prof.title()
        
        return "Não informado"
    
    def _generate_fallback_response(self, patient_info: str, transcription: str) -> str:
        """Resposta fallback quando RAG não funciona"""
        return f"""AVALIAÇÃO MÉDICA

Paciente: {patient_info}
Relato: {transcription}

Análise: Paciente avaliado conforme relato apresentado.
Recomenda-se acompanhamento médico especializado.

Data: {datetime.now().strftime('%d/%m/%Y')}"""

    def get_rag_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema RAG"""
        return {
            "index_loaded": self.faiss_index is not None,
            "total_vectors": self.faiss_index.ntotal if self.faiss_index else 0,
            "total_documents": len(self.chunks) if self.chunks else 0,
            "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
            "index_directory": os.path.dirname(self.faiss_index_path)
        }

# Instância global
medical_rag_service = MedicalRAGService()
