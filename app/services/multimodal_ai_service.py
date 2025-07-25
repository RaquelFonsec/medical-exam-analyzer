import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from openai import OpenAI
import base64
from io import BytesIO
import tempfile
import faiss
import numpy as np
import pickle

class MedicalRAGService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.index_dir = "index_faiss_openai"
        self.faiss_index = None
        self.documents = []
        self.load_indexes()
    
    def load_indexes(self):
        """Carrega os índices FAISS e documentos salvos"""
        try:
            # Carrega o índice FAISS
            index_path = os.path.join(self.index_dir, "index.faiss")
            if os.path.exists(index_path):
                self.faiss_index = faiss.read_index(index_path)
                print(f"✅ Índice FAISS carregado: {self.faiss_index.ntotal} vetores")
            
            # Carrega os documentos/chunks
            docs_path = os.path.join(self.index_dir, "documents.pkl")
            if os.path.exists(docs_path):
                with open(docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
                print(f"✅ Documentos carregados: {len(self.documents)} chunks")
                
        except Exception as e:
            print(f"❌ Erro ao carregar índices: {e}")
    
    def get_embedding(self, text: str) -> List[float]:
        """Gera embedding para um texto usando OpenAI"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Erro ao gerar embedding: {e}")
            return []
    
    def search_similar_documents(self, query: str, k: int = 5) -> List[tuple]:
        """Busca documentos similares no índice FAISS"""
        if not self.faiss_index or not self.documents:
            print("❌ Índices não carregados")
            return []
        
        try:
            # Gera embedding da query
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            # Converte para numpy array
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # Busca no FAISS
            distances, indices = self.faiss_index.search(query_vector, k)
            
            # Retorna documentos e scores
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.documents):
                    # Converte distância para similaridade (maior = mais similar)
                    similarity = 1 / (1 + distance)
                    results.append((self.documents[idx], similarity))
            
            return results
            
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
            return []
    
    def extract_patient_info(self, transcription: str) -> Dict[str, str]:
        """Extrai informações do paciente usando RAG + LLM"""
        
        # 1. Busca contexto relevante no RAG
        queries = [
            "nome do paciente",
            "idade do paciente", 
            "profissão do paciente",
            "dados pessoais identificação",
            transcription[:200]  # Primeiros 200 chars da transcrição
        ]
        
        context_docs = []
        for query in queries:
            similar_docs = self.search_similar_documents(query, k=3)
            context_docs.extend([doc for doc, score in similar_docs if score > 0.7])
        
        # Remove duplicatas
        context_docs = list(set(context_docs))
        context = "\n\n".join(context_docs[:10])  # Máximo 10 documentos
        
        # 2. Prompt para o LLM extrair informações
        prompt = f"""
Você é um assistente médico especializado em anamnese. Analise a transcrição da consulta médica e extraia as seguintes informações do paciente:

CONTEXTO MÉDICO RELEVANTE:
{context}

TRANSCRIÇÃO DA CONSULTA:
{transcription}

Extraia APENAS as seguintes informações se estiverem explicitamente mencionadas:
- Nome completo do paciente
- Idade 
- Profissão/ocupação
- Queixa principal
- Sintomas relatados

Retorne no formato JSON:
{{
    "nome": "nome completo ou 'não informado'",
    "idade": "idade ou 'não informada'", 
    "profissao": "profissão ou 'não informada'",
    "queixa_principal": "queixa principal ou 'não informada'",
    "sintomas": "lista de sintomas ou 'não informados'"
}}

IMPORTANTE: Se uma informação não estiver clara na transcrição, use "não informado" ou "não informada".
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um assistente médico especializado em extrair informações de anamnese. Seja preciso e objetivo."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            # Tenta parsear JSON
            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown se houver
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            patient_info = json.loads(result_text)
            return patient_info
            
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao parsear JSON: {e}")
            return self._extract_fallback(transcription)
        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            return self._extract_fallback(transcription)
    
    def _extract_fallback(self, transcription: str) -> Dict[str, str]:
        """Método de fallback para extração simples sem RAG"""
        try:
            prompt = f"""
Analise esta transcrição médica e extraia apenas as informações explícitas:

{transcription[:1000]}

Retorne JSON com: nome, idade, profissao, queixa_principal, sintomas
Use "não informado" se não encontrar a informação.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=300
            )
            
            result = response.choices[0].message.content.strip()
            if result.startswith('```json'):
                result = result.replace('```json', '').replace('```', '').strip()
                
            return json.loads(result)
            
        except:
            return {
                "nome": "não informado",
                "idade": "não informada", 
                "profissao": "não informada",
                "queixa_principal": "não informada",
                "sintomas": "não informados"
            }

    def generate_medical_report(self, patient_info: Dict[str, str], transcription: str) -> str:
        """Gera relatório médico estruturado"""
        
        # Busca contexto relevante para o relatório
        context_queries = [
            f"relatório médico {patient_info.get('queixa_principal', '')}",
            f"exame clínico {patient_info.get('sintomas', '')}",
            "estrutura relatório médico",
            "anamnese consulta médica"
        ]
        
        context_docs = []
        for query in context_queries:
            similar_docs = self.search_similar_documents(query, k=2)
            context_docs.extend([doc for doc, score in similar_docs if score > 0.6])
        
        context = "\n".join(list(set(context_docs))[:8])
        
        prompt = f"""
Com base na transcrição da consulta médica, gere um relatório médico estruturado e profissional.

INFORMAÇÕES DO PACIENTE:
{json.dumps(patient_info, indent=2, ensure_ascii=False)}

CONTEXTO MÉDICO RELEVANTE:
{context}

TRANSCRIÇÃO COMPLETA:
{transcription}

Gere um relatório médico seguindo esta estrutura:

**RELATÓRIO MÉDICO**

**IDENTIFICAÇÃO DO PACIENTE:**
- Nome: {patient_info.get('nome', 'Não informado')}
- Idade: {patient_info.get('idade', 'Não informada')}
- Profissão: {patient_info.get('profissao', 'Não informada')}

**ANAMNESE:**
- Queixa Principal: 
- História da Doença Atual:
- Sintomas e Sinais:

**EXAME CLÍNICO:**
[Descreva os achados do exame físico mencionados]

**HIPÓTESE DIAGNÓSTICA:**
[Baseado nos sintomas relatados]

**CONDUTA/PLANO:**
[Tratamento, exames solicitados, orientações]

**OBSERVAÇÕES:**
[Informações adicionais relevantes]

Seja profissional, claro e baseie-se apenas nas informações fornecidas na transcrição.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um médico especialista em elaborar relatórios médicos estruturados e profissionais."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Erro ao gerar relatório: {e}")
            return f"Erro ao gerar relatório médico: {e}"


class MultimodalAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.rag_service = MedicalRAGService()  # Nova instância do RAG
        
        # Configuração de caminhos
        self.relatorios_dir = "relatorios"
        self.transcription_path = os.path.join(self.relatorios_dir, "transcription.txt")
        
        # Cria diretório se não existir
        os.makedirs(self.relatorios_dir, exist_ok=True)
    
    async def analyze_multimodal(self, patient_info: str = "", audio_bytes: bytes = None, image_path: str = None) -> Dict[str, Any]:
        """Análise multimodal com RAG integrado"""
        results = {
            "transcription": "",
            "patient_data": {},
            "medical_report": "",
            "image_analysis": "",
            "analysis": "",
            "status": "success"
        }
        
        try:
            print("🚀 Iniciando análise multimodal com RAG...")
            
            # 1. TRANSCRIÇÃO DE ÁUDIO
            transcription = ""
            if audio_bytes:
                print("🎙️ Processando transcrição de áudio...")
                transcription = await self._transcribe_audio_whisper(audio_bytes)
                
                # Salva transcrição em arquivo
                with open(self.transcription_path, "w", encoding="utf-8") as f:
                    f.write(transcription)
                print(f"✅ Transcrição salva em {self.transcription_path}")
                
                results["transcription"] = transcription
            
            # Carrega transcrição existente se não houver áudio
            elif os.path.exists(self.transcription_path):
                with open(self.transcription_path, "r", encoding="utf-8") as f:
                    transcription = f.read()
                results["transcription"] = transcription
                print(f"✅ Transcrição carregada do arquivo existente")
            
            # 2. EXTRAÇÃO DE DADOS DO PACIENTE COM RAG
            if transcription:
                print("🔍 Extraindo informações do paciente com RAG...")
                patient_data = self.rag_service.extract_patient_info(transcription)
                results["patient_data"] = patient_data
                print(f"✅ Dados extraídos: {patient_data}")
            
            # 3. GERAÇÃO DE RELATÓRIO MÉDICO COM RAG
            if transcription and results["patient_data"]:
                print("📋 Gerando relatório médico...")
                medical_report = self.rag_service.generate_medical_report(
                    results["patient_data"], 
                    transcription
                )
                results["medical_report"] = medical_report
                
                # Salva relatório
                patient_name = results['patient_data'].get('nome', 'paciente')
                safe_name = patient_name.replace(' ', '_').replace('/', '_').lower()
                report_path = os.path.join(self.relatorios_dir, f"relatorio_{safe_name}.txt")
                
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(medical_report)
                print(f"✅ Relatório salvo em {report_path}")
            
            # 4. ANÁLISE DE IMAGEM
            if image_path and os.path.exists(image_path):
                print("🖼️ Analisando imagem médica...")
                image_analysis = await self._analyze_image(image_path)
                results["image_analysis"] = image_analysis
                print("✅ Análise de imagem concluída")
            
            # 5. ANÁLISE INTEGRADA
            if any([results["transcription"], results["image_analysis"]]):
                print("🧠 Gerando análise integrada...")
                integrated_analysis = await self._generate_integrated_analysis(results)
                results["analysis"] = integrated_analysis
                print("✅ Análise integrada concluída")
            
            print("🎉 Análise multimodal finalizada com sucesso!")
            return results
            
        except Exception as e:
            print(f"❌ Erro na análise multimodal: {e}")
            results["status"] = "error"
            results["error"] = str(e)
            return results
    
    async def _transcribe_audio_whisper(self, audio_bytes: bytes) -> str:
        """Transcrição de áudio usando Whisper da OpenAI"""
        try:
            # Salva audio temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            # Transcrição com Whisper
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"
                )
            
            # Remove arquivo temporário
            os.unlink(temp_file_path)
            
            return transcript.text
            
        except Exception as e:
            print(f"❌ Erro na transcrição: {e}")
            return f"Erro na transcrição: {e}"
    
    async def _analyze_image(self, image_path: str) -> str:
        """Análise de imagem médica usando GPT-4 Vision"""
        try:
            # Lê e codifica a imagem
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Análise com GPT-4 Vision
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um médico radiologista especialista. Analise a imagem médica fornecida e descreva os achados de forma detalhada e profissional."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analise esta imagem médica e forneça uma descrição detalhada dos achados, possíveis diagnósticos e recomendações."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Erro na análise de imagem: {e}")
            return f"Erro na análise de imagem: {e}"
    
    async def _generate_integrated_analysis(self, results: dict) -> str:
        """Gera análise integrada usando RAG para contexto médico"""
        
        # Busca contexto relevante baseado nos dados do paciente
        patient_data = results.get("patient_data", {})
        queries = [
            f"análise médica {patient_data.get('queixa_principal', '')}",
            f"diagnóstico {patient_data.get('sintomas', '')}",
            "avaliação clínica consulta médica"
        ]
        
        context_docs = []
        for query in queries:
            if query.strip():  # Só busca se a query não estiver vazia
                similar_docs = self.rag_service.search_similar_documents(query, k=3)
                context_docs.extend([doc for doc, score in similar_docs if score > 0.7])
        
        context = "\n".join(list(set(context_docs))[:5])
        
        prompt = f"""
Como médico especialista, faça uma análise integrada desta consulta médica:

DADOS DO PACIENTE:
{json.dumps(patient_data, indent=2, ensure_ascii=False)}

TRANSCRIÇÃO:
{results.get('transcription', 'Não disponível')[:500]}...

CONTEXTO MÉDICO RELEVANTE:
{context}

ANÁLISE DE IMAGEM:
{results.get('image_analysis', 'Não disponível')}

Forneça uma análise médica integrada considerando:
1. Correlação entre sintomas e achados
2. Hipóteses diagnósticas
3. Recomendações de conduta
4. Exames complementares sugeridos
5. Sinais de alerta

Seja objetivo e profissional.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um médico especialista fazendo análise clínica integrada."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Erro na análise integrada: {e}"

    # Métodos auxiliares
    def get_transcription(self) -> str:
        """Retorna a transcrição salva"""
        if os.path.exists(self.transcription_path):
            with open(self.transcription_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""
    
    def save_transcription(self, transcription: str) -> str:
        """Salva transcrição manualmente"""
        with open(self.transcription_path, "w", encoding="utf-8") as f:
            f.write(transcription)
        return self.transcription_path


# Função de teste e demonstração
async def test_multimodal_service():
    """Testa o serviço multimodal completo"""
    service = MultimodalAIService()
    
    # Simula uma transcrição de teste
    test_transcription = """
    Paciente João Silva, 45 anos, engenheiro civil. Comparece à consulta relatando
    dor torácica há 3 dias, tipo aperto, irradiando para braço esquerdo.
    Nega dispneia em repouso, mas refere cansaço aos pequenos esforços.
    Histórico familiar de doença coronariana. Tabagista há 20 anos.
    Pressão arterial: 150x95mmHg. Frequência cardíaca: 88bpm.
    Ausculta cardíaca: bulhas rítmicas, sem sopros.
    Solicita avaliação cardiológica.
    """
    
    # Salva transcrição para teste
    service.save_transcription(test_transcription)
    
    # Executa análise completa
    results = await service.analyze_multimodal()
    
    print("=== RESULTADOS DO TESTE ===")
    print(f"Transcrição: {len(results['transcription'])} caracteres")
    print(f"Dados do paciente: {results['patient_data']}")
    print(f"Relatório médico: {len(results['medical_report'])} caracteres")
    print(f"Status: {results['status']}")
    
    return results


# Exemplo de uso
if __name__ == "__main__":
    # Configura variável de ambiente se necessário
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️ Configure a variável OPENAI_API_KEY")
    else:
        # Executa teste
        asyncio.run(test_multimodal_service())