import os
import json
import faiss
import numpy as np
import pickle
from typing import Dict, List, Optional, Tuple
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
    
    def get_embedding(self, text: str) -> List[float]:
        """Gera embedding para um texto usando OpenAI"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text.strip()
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Erro ao gerar embedding: {e}")
            return []
    
    def search_similar_documents(self, query: str, k: int = 5, min_similarity: float = 0.5) -> List[Tuple[str, float]]:
        """
        Busca documentos similares no índice FAISS
        
        Args:
            query: Texto de busca
            k: Número de documentos a retornar
            min_similarity: Similaridade mínima (0-1)
            
        Returns:
            Lista de tuplas (documento, similaridade)
        """
        if not self.faiss_index or not self.documents:
            print("❌ Índices não carregados")
            return []
        
        if not query.strip():
            return []
        
        try:
            # Gera embedding da query
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
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
    
    def extract_patient_info(self, transcription: str) -> Dict[str, str]:
        """
        Extrai informações estruturadas do paciente usando RAG + LLM
        
        Args:
            transcription: Texto da transcrição da consulta
            
        Returns:
            Dicionário com informações do paciente
        """
        if not transcription.strip():
            return self._get_empty_patient_info()
        
        # 1. Busca contexto relevante no RAG
        search_queries = [
            "identificação do paciente nome idade",
            "dados pessoais profissão ocupação",
            "anamnese queixa principal sintomas",
            transcription[:200]  # Primeiros 200 chars da transcrição
        ]
        
        context_docs = []
        for query in search_queries:
            similar_docs = self.search_similar_documents(query, k=3, min_similarity=0.6)
            context_docs.extend([doc for doc, score in similar_docs])
        
        # Remove duplicatas e limita contexto
        unique_docs = list(dict.fromkeys(context_docs))  # Remove duplicatas preservando ordem
        context = "\n\n".join(unique_docs[:8])  # Máximo 8 documentos
        
        # 2. Prompt estruturado para extração
        prompt = self._build_extraction_prompt(transcription, context)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "Você é um assistente médico especializado em extrair informações estruturadas de anamnese. Seja preciso e objetivo. Retorne apenas JSON válido."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=600
            )
            
            # Parse do resultado
            result_text = response.choices[0].message.content.strip()
            return self._parse_patient_info(result_text)
            
        except Exception as e:
            print(f"❌ Erro na extração com RAG: {e}")
            return self._extract_fallback(transcription)
    
    def _build_extraction_prompt(self, transcription: str, context: str) -> str:
        """Constrói prompt para extração de informações"""
        return f"""
Analise a transcrição da consulta médica e extraia as informações do paciente.

CONTEXTO MÉDICO RELEVANTE (use como referência):
{context}

TRANSCRIÇÃO DA CONSULTA:
{transcription}

Extraia APENAS informações explicitamente mencionadas na transcrição:

1. Nome completo do paciente
2. Idade (anos)
3. Profissão/ocupação
4. Queixa principal (motivo da consulta)
5. Sintomas relatados
6. Histórico médico relevante
7. Medicamentos em uso

Retorne no formato JSON exato:
{{
    "nome": "nome completo ou 'não informado'",
    "idade": "idade ou 'não informada'",
    "profissao": "profissão ou 'não informada'",
    "queixa_principal": "descrição da queixa ou 'não informada'",
    "sintomas": "lista dos sintomas ou 'não informados'",
    "historico_medico": "histórico relevante ou 'não informado'",
    "medicamentos": "medicamentos em uso ou 'não informados'"
}}

IMPORTANTE: 
- Use "não informado/a/os" se a informação não estiver clara
- Seja fiel ao texto da transcrição
- Não invente informações"""

    def _parse_patient_info(self, result_text: str) -> Dict[str, str]:
        """Parse do resultado JSON da extração"""
        try:
            # Remove markdown se houver
            clean_text = result_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text.replace('```json', '').replace('```', '').strip()
            elif clean_text.startswith('```'):
                clean_text = clean_text.replace('```', '').strip()
            
            patient_info = json.loads(clean_text)
            
            # Valida campos obrigatórios
            required_fields = ['nome', 'idade', 'profissao', 'queixa_principal', 'sintomas']
            for field in required_fields:
                if field not in patient_info:
                    patient_info[field] = 'não informado'
            
            return patient_info
            
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao parsear JSON: {e}")
            print(f"Texto recebido: {result_text[:200]}...")
            return self._extract_fallback_simple(result_text)
    
    def _extract_fallback_simple(self, text: str) -> Dict[str, str]:
        """Extração simples em caso de erro no JSON"""
        # Tenta extrair informações básicas do texto
        info = self._get_empty_patient_info()
        
        text_lower = text.lower()
        
        # Busca padrões simples
        if 'nome' in text_lower:
            lines = text.split('\n')
            for line in lines:
                if 'nome' in line.lower() and ':' in line:
                    info['nome'] = line.split(':', 1)[1].strip().strip('"').strip("'")
                    break
        
        return info
    
    def _extract_fallback(self, transcription: str) -> Dict[str, str]:
        """Método de fallback para extração sem RAG"""
        try:
            prompt = f"""
Analise esta transcrição médica e extraia as informações básicas:

{transcription[:800]}

Retorne JSON com: nome, idade, profissao, queixa_principal, sintomas
Use "não informado" para informações ausentes.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=400
            )
            
            result = response.choices[0].message.content.strip()
            return self._parse_patient_info(result)
            
        except Exception as e:
            print(f"❌ Erro no fallback: {e}")
            return self._get_empty_patient_info()
    
    def _get_empty_patient_info(self) -> Dict[str, str]:
        """Retorna estrutura vazia de informações do paciente"""
        return {
            "nome": "não informado",
            "idade": "não informada",
            "profissao": "não informada",
            "queixa_principal": "não informada",
            "sintomas": "não informados",
            "historico_medico": "não informado",
            "medicamentos": "não informados"
        }

    def generate_medical_report(self, patient_info: Dict[str, str], transcription: str) -> str:
        """
        Gera relatório médico estruturado usando RAG para contexto
        
        Args:
            patient_info: Informações extraídas do paciente
            transcription: Transcrição completa da consulta
            
        Returns:
            Relatório médico formatado
        """
        # Busca contexto relevante para o relatório
        context_queries = [
            f"relatório médico {patient_info.get('queixa_principal', '')}",
            f"exame clínico {patient_info.get('sintomas', '')}",
            "estrutura relatório médico anamnese",
            "consulta médica diagnóstico"
        ]
        
        context_docs = []
        for query in context_queries:
            if query.strip():
                similar_docs = self.search_similar_documents(query, k=2, min_similarity=0.6)
                context_docs.extend([doc for doc, score in similar_docs])
        
        # Contexto limitado e sem duplicatas
        unique_context = list(dict.fromkeys(context_docs))
        context = "\n---\n".join(unique_context[:6])
        
        prompt = self._build_report_prompt(patient_info, transcription, context)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "Você é um médico especialista em elaborar relatórios médicos estruturados, claros e profissionais."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1800
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Erro ao gerar relatório: {e}")
            return self._generate_basic_report(patient_info, transcription)
    
    def _build_report_prompt(self, patient_info: Dict[str, str], transcription: str, context: str) -> str:
        """Constrói prompt para geração do relatório"""
        return f"""
Gere um relatório médico estruturado e profissional baseado nas informações da consulta.

INFORMAÇÕES DO PACIENTE:
{json.dumps(patient_info, indent=2, ensure_ascii=False)}

CONTEXTO MÉDICO RELEVANTE:
{context}

TRANSCRIÇÃO COMPLETA DA CONSULTA:
{transcription}

Gere um relatório seguindo EXATAMENTE esta estrutura:

**RELATÓRIO MÉDICO**

**IDENTIFICAÇÃO DO PACIENTE:**
- Nome: {patient_info.get('nome', 'Não informado')}
- Idade: {patient_info.get('idade', 'Não informada')}
- Profissão: {patient_info.get('profissao', 'Não informada')}

**ANAMNESE:**
- Queixa Principal: [descreva a queixa principal do paciente]
- História da Doença Atual: [histórico detalhado dos sintomas]
- Sintomas Relatados: [liste os sintomas mencionados]
- Histórico Médico: [histórico médico relevante se mencionado]

**EXAME FÍSICO:**
[Descreva os achados do exame físico mencionados na consulta]

**MEDICAMENTOS EM USO:**
[Liste medicamentos mencionados ou "Não informado"]

**AVALIAÇÃO CLÍNICA:**
[Suas impressões clínicas baseadas nos dados coletados]

**HIPÓTESES DIAGNÓSTICAS:**
[Liste as possíveis hipóteses diagnósticas]

**CONDUTA/PLANO TERAPÊUTICO:**
[Tratamento proposto, exames solicitados, orientações]

**OBSERVAÇÕES:**
[Informações adicionais relevantes ou recomendações]

IMPORTANTE: Base-se APENAS nas informações fornecidas na transcrição. Seja profissional e objetivo."""

    def _generate_basic_report(self, patient_info: Dict[str, str], transcription: str) -> str:
        """Gera relatório básico em caso de erro"""
        return f"""
**RELATÓRIO MÉDICO**

**IDENTIFICAÇÃO DO PACIENTE:**
- Nome: {patient_info.get('nome', 'Não informado')}
- Idade: {patient_info.get('idade', 'Não informada')}
- Profissão: {patient_info.get('profissao', 'Não informada')}

**ANAMNESE:**
- Queixa Principal: {patient_info.get('queixa_principal', 'Não informada')}
- Sintomas: {patient_info.get('sintomas', 'Não informados')}

**TRANSCRIÇÃO DA CONSULTA:**
{transcription[:500]}...

**OBSERVAÇÕES:**
Relatório gerado automaticamente. Revisar informações com base na consulta completa.
"""

    def search_medical_context(self, query: str, max_results: int = 5) -> List[str]:
        """
        Busca contexto médico específico no RAG
        
        Args:
            query: Consulta médica
            max_results: Número máximo de resultados
            
        Returns:
            Lista de documentos relevantes
        """
        results = self.search_similar_documents(query, k=max_results, min_similarity=0.7)
        return [doc for doc, score in results]
    
    def get_rag_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema RAG"""
        return {
            "index_loaded": self.faiss_index is not None,
            "total_vectors": self.faiss_index.ntotal if self.faiss_index else 0,
            "total_documents": len(self.documents),
            "embedding_model": self.embedding_model,
            "index_directory": self.index_dir
        }


# Função de teste
def test_medical_rag():
    """Testa o serviço RAG médico"""
    rag = MedicalRAGService()
    
    # Exibe estatísticas
    stats = rag.get_rag_stats()
    print("=== ESTATÍSTICAS DO RAG ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Teste de busca
    print("\n=== TESTE DE BUSCA ===")
    results = rag.search_similar_documents("dor no peito", k=3)
    for i, (doc, score) in enumerate(results):
        print(f"{i+1}. Similaridade: {score:.3f}")
        print(f"   Documento: {doc[:100]}...")
    
    # Teste de extração
    print("\n=== TESTE DE EXTRAÇÃO ===")
    test_transcription = """
    Paciente João Silva, 45 anos, engenheiro. Queixa de dor torácica há 3 dias,
    tipo aperto, irradiando para braço esquerdo. Nega dispneia. PA: 140x90mmHg.
    """
    
    patient_info = rag.extract_patient_info(test_transcription)
    print("Informações extraídas:")
    print(json.dumps(patient_info, indent=2, ensure_ascii=False))
    
    # Teste de relatório
    print("\n=== TESTE DE RELATÓRIO ===")
    report = rag.generate_medical_report(patient_info, test_transcription)
    print(f"Relatório gerado ({len(report)} caracteres):")
    print(report[:300] + "...")


if __name__ == "__main__":
    test_medical_rag()