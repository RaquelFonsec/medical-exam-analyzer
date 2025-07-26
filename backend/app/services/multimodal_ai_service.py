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
    def __init__(self, client, parent_service=None):
        """Inicializa o serviço RAG médico"""
        self.client = client
        self.parent_service = parent_service  # Referência ao MultimodalAIService
        
        # Configuração de embedding
        self.embedding_model = "text-embedding-3-small"
        
        # Determinar o path correto para os índices
        # Primeiro, tenta o diretório local app/index_faiss_openai
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)  # Sobe um nível para app/
        self.index_dir = os.path.join(app_dir, "index_faiss_openai")
        
        # Se não existir, tenta paths alternativos
        if not os.path.exists(self.index_dir):
            # Tenta na raiz do projeto
            project_root = os.path.dirname(os.path.dirname(app_dir))
            alternative_path = os.path.join(project_root, "index_faiss_openai")
            if os.path.exists(alternative_path):
                self.index_dir = alternative_path
        
        print(f"🔍 Tentando carregar índices de: {self.index_dir}")
        
        self.faiss_index = None
        self.documents = []
        self.load_indexes()
    
    def load_indexes(self):
        """Carrega os índices FAISS e documentos salvos"""
        try:
            # Verifica se o diretório existe
            if not os.path.exists(self.index_dir):
                print(f"❌ Diretório de índices não encontrado: {self.index_dir}")
                return
            
            # Carrega o índice FAISS
            index_path = os.path.join(self.index_dir, "index.faiss")
            if os.path.exists(index_path):
                self.faiss_index = faiss.read_index(index_path)
                print(f"✅ Índice FAISS carregado: {self.faiss_index.ntotal} vetores de {index_path}")
            else:
                print(f"❌ Arquivo index.faiss não encontrado em: {index_path}")
            
            # Carrega os documentos/chunks
            docs_path = os.path.join(self.index_dir, "documents.pkl")
            if os.path.exists(docs_path):
                with open(docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
                print(f"✅ Documentos carregados: {len(self.documents)} chunks de {docs_path}")
            else:
                print(f"❌ Arquivo documents.pkl não encontrado em: {docs_path}")
                
        except Exception as e:
            print(f"❌ Erro ao carregar índices: {e}")
            import traceback
            traceback.print_exc()
    
    def get_rag_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do sistema RAG"""
        return {
            "faiss_index_loaded": self.faiss_index is not None,
            "documents_loaded": len(self.documents) if self.documents else 0,
            "index_directory": self.index_dir,
            "vector_count": self.faiss_index.ntotal if self.faiss_index else 0
        }
    
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

    def generate_medical_report(self, patient_text: str, patient_data: dict) -> str:
        """Gera relatório médico completo com classificação de benefício"""
        
        # Primeiro gera a classificação para incluir no laudo
        benefit_classification = self.parent_service.classify_benefit_and_cid(patient_text, patient_data) if self.parent_service else {}
        
        # Montar informações da classificação para o prompt
        classification_info = ""
        if benefit_classification:
            classification_info = f"""
CLASSIFICAÇÃO PREVIDENCIÁRIA:
- Tipo de Benefício: {benefit_classification.get('tipo_beneficio', 'Não definido')}
- CID Principal: {benefit_classification.get('cid_principal', 'Não definido')} - {benefit_classification.get('cid_descricao', '')}
- Gravidade: {benefit_classification.get('gravidade', 'Não definida')}
- Prognóstico: {benefit_classification.get('prognóstico', 'Não definido')}
"""

        # Buscar casos similares no RAG primeiro
        similar_cases = []
        try:
            # Se temos uma instância RAG funcional, buscar casos similares
            if hasattr(self, 'search_similar_documents'):
                search_results = self.search_similar_documents(patient_text, k=3)
                # search_similar_documents retorna lista de tuplas (documento, similaridade)
                similar_cases = search_results if isinstance(search_results, list) else []
                print(f"🔍 RAG encontrou {len(similar_cases)} casos similares")
        except Exception as e:
            print(f"⚠️ RAG não disponível: {e}")

        # Preparar contexto RAG
        rag_context = ""
        if similar_cases:
            rag_context = "\n\nCASOS SIMILARES NA BASE DE CONHECIMENTO:\n"
            for i, case_data in enumerate(similar_cases[:2], 1):
                # case_data é uma tupla (documento, similaridade)
                case_text = case_data[0] if isinstance(case_data, tuple) else str(case_data)
                similarity = case_data[1] if isinstance(case_data, tuple) and len(case_data) > 1 else 0.0
                rag_context += f"\nCaso {i} (Similaridade: {similarity:.2f}):\n{case_text[:200]}...\n"

        prompt = f"""
Você é um médico perito previdenciário experiente. Gere um LAUDO MÉDICO PROFISSIONAL seguindo a estrutura específica abaixo.

⚠️ REGRAS IMPORTANTES:
- Base-se APENAS nas informações fornecidas pelo paciente
- NÃO invente exames físicos, sintomas ou detalhes não relatados
- Use linguagem médica técnica e precisa
- Seja detalhado nos aspectos funcionais e prognósticos

DADOS DO PACIENTE:
{patient_data}

INFORMAÇÕES RELATADAS:
{patient_text}

{classification_info}

{rag_context}

ESTRUTURE O LAUDO SEGUINDO ESTE FORMATO EXATO:

**LAUDO MÉDICO PREVIDENCIÁRIO**

**IDENTIFICAÇÃO:**
Nome: {patient_data.get('nome', 'Não informado')}
Idade: {patient_data.get('idade', 'Não informada')}  
Profissão: {patient_data.get('profissao', 'Não informada')}

**História Clínica Resumida**
[UM PARÁGRAFO COESO contendo: data de início dos sintomas, evolução clínica, eventos de agravamento, sintomas atuais e repercussões funcionais, impacto na vida diária/laboral, diagnóstico com CID-10. Baseie-se apenas no relatado pelo paciente]

**Limitação Funcional**
[UM PARÁGRAFO descrevendo: limitações atuais (motoras, sensoriais, cognitivas), como isso impacta a funcionalidade no trabalho/vida social/autonomia, sintomas que agravam. Use apenas informações relatadas]

**Tratamento**
[Descrever procedimentos, medicamentos, terapias em uso conforme relatado, resposta ou necessidade de continuidade]

**Prognóstico (Tendência Reservada/Desfavorável)**
[Indicar evolução esperada, tempo estimado de afastamento se aplicável, necessidade de tratamento contínuo, possibilidade de retorno à função habitual]

**Conclusão Congruente com o Benefício ({benefit_classification.get('tipo_beneficio', 'ANÁLISE_NECESSÁRIA')})**
[Conclusão específica para o tipo de benefício:
- AUXÍLIO-DOENÇA: incapacidade temporária, tempo estimado
- BPC/LOAS: impedimento de longo prazo, limitações para participação plena
- AUXÍLIO-ACIDENTE: redução parcial e permanente da capacidade
- APOSENTADORIA POR INVALIDEZ: incapacidade definitiva para qualquer trabalho
- ISENÇÃO IMPOSTO DE RENDA: doença grave conforme lei]

**CID-10**
{benefit_classification.get('cid_principal', 'A definir')} – {benefit_classification.get('cid_descricao', 'Diagnóstico a ser confirmado')} (principal)

**DATA:** [Data atual]  
**MÉDICO RESPONSÁVEL:** Dr. [Nome do Médico]  
**CRM:** [Número do CRM]

IMPORTANTE: Crie um laudo profissional, técnico e detalhado, mas baseado APENAS nas informações fornecidas.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um médico perito especialista em laudos previdenciários. Seja técnico, detalhado e preciso."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            report = response.choices[0].message.content.strip()
            
            # Salvar relatório em arquivo
            patient_name = patient_data.get('nome', 'não_informado').replace(' ', '_').lower()
            filename = f"relatorio_{patient_name}.txt"
            filepath = os.path.join("relatorios", filename)
            
            os.makedirs("relatorios", exist_ok=True)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)
            
            print(f"✅ Relatório médico completo salvo em {filepath}")
            return report
            
        except Exception as e:
            print(f"❌ Erro ao gerar relatório médico: {e}")
            return f"Erro ao gerar relatório médico: {e}"


class MultimodalAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Inicializar RAG service com referência a este service
        self.rag_service = MedicalRAGService(self.client, parent_service=self)
        
        # Path para salvar transcrições
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
            
            # SEM ÁUDIO: usar apenas se não tiver patient_info
            elif not patient_info and os.path.exists(self.transcription_path):
                with open(self.transcription_path, "r", encoding="utf-8") as f:
                    transcription = f.read()
                results["transcription"] = transcription
                print(f"✅ Transcrição carregada do arquivo (sem patient_info atual)")
            
            # 2. EXTRAÇÃO DE DADOS DO PACIENTE COM RAG
            # PRIORIZAR TEXTO ATUAL FORNECIDO
            combined_text = ""
            if patient_info and patient_info.strip():
                print("📝 Usando texto fornecido pelo usuário...")
                combined_text = patient_info.strip()
            elif transcription and not transcription.startswith("⚠️") and not transcription.startswith("Erro"):
                print("🎤 Usando transcrição de áudio...")
                combined_text = transcription
            else:
                print("⚠️ Nenhum texto disponível para análise")
                combined_text = ""
            
            # Sempre tentar extrair dados se temos algum texto
            if combined_text.strip():
                patient_data = self.rag_service.extract_patient_info(combined_text)
                results["patient_data"] = patient_data
                print(f"✅ Dados extraídos: {patient_data}")
            else:
                print("⚠️ Nenhum texto disponível para extração")
                results["patient_data"] = {
                    "nome": "não informado",
                    "idade": "não informada", 
                    "profissao": "não informada",
                    "queixa_principal": "não informada",
                    "sintomas": "não informados"
                }
            
            # 3. GERAÇÃO DE RELATÓRIO MÉDICO COM RAG
            if combined_text.strip() and results["patient_data"]:
                print("📋 Gerando relatório médico...")
                medical_report = self.rag_service.generate_medical_report(
                    combined_text, # Usar o texto combinado em vez de apenas transcrição
                    results["patient_data"]
                )
                results["medical_report"] = medical_report
                
                # Salva relatório
                patient_name = results['patient_data'].get('nome', 'paciente')
                safe_name = patient_name.replace(' ', '_').replace('/', '_').lower()
                report_path = os.path.join(self.relatorios_dir, f"relatorio_{safe_name}.txt")
                
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(medical_report)
                print(f"✅ Relatório salvo em {report_path}")
            else:
                print("⚠️ Dados insuficientes para gerar relatório")
            
            # 4. CLASSIFICAÇÃO DE BENEFÍCIO E CID
            if combined_text.strip():
                print("🏥 Classificando tipo de benefício e CID...")
                benefit_classification = self.classify_benefit_and_cid(combined_text, results["patient_data"])
                results["benefit_classification"] = benefit_classification
                print(f"✅ Classificação concluída: {benefit_classification['tipo_beneficio']}")
            else:
                print("⚠️ Texto insuficiente para classificação")
            
            # 5. ANÁLISE DE IMAGEM
            if image_path and os.path.exists(image_path):
                print("🖼️ Analisando imagem médica...")
                image_analysis = await self._analyze_image(image_path)
                results["image_analysis"] = image_analysis
                print("✅ Análise de imagem concluída")
            
            # 6. ANÁLISE INTEGRADA
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
            print(f"🎙️ Iniciando transcrição de {len(audio_bytes)} bytes")
            
            # Salva audio temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            print(f"📁 Arquivo temporário criado: {temp_file_path}")
            
            # Transcrição com Whisper
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"
                )
            
            # Remove arquivo temporário
            os.unlink(temp_file_path)
            
            transcription_text = transcript.text.strip()
            print(f"✅ Transcrição bem-sucedida: '{transcription_text[:100]}...'")
            
            return transcription_text
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Erro na transcrição: {error_msg}")
            
            # Remove arquivo temporário em caso de erro
            try:
                if 'temp_file_path' in locals():
                    os.unlink(temp_file_path)
            except:
                pass
            
            # Retorna erro mais amigável
            if "format" in error_msg.lower() or "decode" in error_msg.lower():
                return "⚠️ Formato de áudio não suportado. Tente gravar novamente ou use as informações do texto."
            elif "duration" in error_msg.lower():
                return "⚠️ Áudio muito curto. Grave por pelo menos 3 segundos."
            else:
                return f"⚠️ Erro na transcrição do áudio. Use as informações do texto."
    
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
            "avaliação clínica consulta médico"
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


    def classify_benefit_and_cid(self, patient_text: str, patient_data: dict) -> dict:
        """Classifica tipo de benefício previdenciário específico e sugere CID baseado nos dados do paciente"""
        
        prompt = f"""
Você é um médico perito especialista em classificação de benefícios previdenciários brasileiros.

DADOS DO PACIENTE:
{patient_data}

TEXTO COMPLETO DA CONSULTA:
{patient_text}

Analise os dados e classifique em um dos seguintes benefícios:

1. AUXÍLIO-DOENÇA:
   - Incapacidade temporária para trabalho (até 2 anos)
   - Doenças agudas com recuperação esperada
   - Fraturas, cirurgias simples, infecções tratáveis
   - Depressão leve/moderada com prognóstico favorável

2. APOSENTADORIA POR INVALIDEZ:
   - Incapacidade total e permanente para qualquer trabalho
   - Doenças crônicas degenerativas graves
   - Deficiências severas irreversíveis
   - Prognóstico sem perspectiva de melhora

3. BPC/LOAS:
   - Pessoa com deficiência ou idoso (65+) em vulnerabilidade social
   - Incapacidade para vida independente e trabalho
   - Renda familiar per capita < 1/4 salário mínimo
   - Deficiência que cause impedimentos de longo prazo

4. AUXÍLIO-ACIDENTE:
   - Acidente de trabalho ou doença ocupacional
   - Sequela que reduza capacidade laboral
   - Redução da capacidade de trabalho (não incapacidade total)
   - Consolidação com sequela

5. ISENÇÃO IMPOSTO DE RENDA:
   - Doenças graves especificadas em lei
   - Aposentadoria por invalidez
   - Pensão por morte de acidente em serviço público

Retorne APENAS um JSON:
{{
    "tipo_beneficio": "AUXÍLIO-DOENÇA" | "APOSENTADORIA POR INVALIDEZ" | "BPC/LOAS" | "AUXÍLIO-ACIDENTE" | "ISENÇÃO IMPOSTO DE RENDA",
    "cid_principal": "código CID-10",
    "cid_descricao": "descrição do CID",
    "justificativa": "explicação da classificação baseada nos critérios legais",
    "gravidade": "LEVE" | "MODERADA" | "GRAVE",
    "prognóstico": "descrição do prognóstico médico"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um médico perito especialista em classificação previdenciária. Seja preciso e objetivo."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Remove markdown se houver
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            classification = json.loads(result_text)
            
            print(f"✅ Classificação: {classification['tipo_beneficio']} - CID: {classification['cid_principal']}")
            return classification
            
        except Exception as e:
            print(f"❌ Erro na classificação: {e}")
            return {
                "tipo_beneficio": "ANALISE_MANUAL",
                "cid_principal": "Z00.0",
                "cid_descricao": "Exame médico geral",
                "justificativa": "Análise manual necessária",
                "gravidade": "A_DEFINIR",
                "prognóstico": "Avaliação médica presencial recomendada"
            }


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
    # service.save_transcription(test_transcription) # This line was removed as per the new_code
    
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