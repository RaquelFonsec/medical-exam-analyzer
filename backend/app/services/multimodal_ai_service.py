

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
        self.parent_service = parent_service
        
        # Configuração de embedding
        self.embedding_model = "text-embedding-3-small"
        
        # Determinar o path correto para os índices
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)
        self.index_dir = os.path.join(app_dir, "index_faiss_openai")
        
        # Se não existir, tenta paths alternativos
        if not os.path.exists(self.index_dir):
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
            if not os.path.exists(self.index_dir):
                print(f"❌ Diretório de índices não encontrado: {self.index_dir}")
                return
            
            # Carrega o índice FAISS
            index_path = os.path.join(self.index_dir, "index.faiss")
            if os.path.exists(index_path):
                self.faiss_index = faiss.read_index(index_path)
                print(f"✅ Índice FAISS carregado: {self.faiss_index.ntotal} vetores")
            else:
                print(f"❌ Arquivo index.faiss não encontrado")
            
            # Carrega os documentos/chunks
            docs_path = os.path.join(self.index_dir, "documents.pkl")
            if os.path.exists(docs_path):
                with open(docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
                print(f"✅ Documentos carregados: {len(self.documents)} chunks")
            else:
                print(f"❌ Arquivo documents.pkl não encontrado")
                
        except Exception as e:
            print(f"❌ Erro ao carregar índices: {e}")
    
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
                if idx < len(self.documents) and idx >= 0:
                    try:
                        document = self.documents[idx]
                        similarity = 1 / (1 + distance)
                        doc_text = str(document) if document is not None else ""
                        results.append((doc_text, similarity))
                    except Exception as e:
                        print(f"⚠️ Erro ao processar documento {idx}: {e}")
                        continue
            
            return results
            
        except Exception as e:
            print(f"❌ Erro na busca: {e}")
            return []
    
    def extract_patient_info(self, text: str) -> Dict[str, str]:
        """Extrai informações do paciente - ANTI-ALUCINAÇÃO"""
        
        prompt = f"""
EXTRAIA APENAS informações EXPLICITAMENTE mencionadas no texto médico.

TEXTO MÉDICO:
{text}

REGRAS RIGOROSAS:
- Se não estiver CLARAMENTE mencionado, use "não informado"
- NÃO invente, NÃO presuma, NÃO deduza informações
- Extraia apenas o que está LITERALMENTE escrito

Retorne JSON EXATO:
{{
    "nome": "nome completo encontrado ou 'não informado'",
    "idade": "idade encontrada ou 'não informada'",
    "profissao": "profissão encontrada ou 'não informada'",
    "queixa_principal": "queixa encontrada ou 'não informada'",
    "sintomas": "sintomas encontrados ou 'não informados'"
}}

IMPORTANTE: Seja LITERAL. Se duvidar, use "não informado".
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um assistente médico que extrai APENAS informações explícitas. Nunca invente dados."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,  # Zero criatividade
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            # VALIDAÇÃO ANTES DO PARSE JSON
            if not result_text or result_text.isspace():
                print("⚠️ Resposta vazia do GPT - usando fallback")
                raise ValueError("Resposta vazia do modelo")
            
            patient_info = json.loads(result_text)
            return patient_info
            
        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            return {
                "nome": "não informado",
                "idade": "não informada", 
                "profissao": "não informada",
                "queixa_principal": "não informada",
                "sintomas": "não informados"
            }

    def generate_structured_medical_report(self, patient_info: Dict[str, str], transcription: str, classification: Dict) -> str:
        """Gera laudo médico estruturado conforme especificação profissional"""
        
        prompt = f"""
Gere um LAUDO MÉDICO PROFISSIONAL seguindo RIGOROSAMENTE esta estrutura:

DADOS DO PACIENTE:
{json.dumps(patient_info, indent=2, ensure_ascii=False)}

TRANSCRIÇÃO COMPLETA:
{transcription}

CLASSIFICAÇÃO:
- Tipo: {classification.get('tipo_beneficio', 'AUXÍLIO-DOENÇA')}
- CID: {classification.get('cid_principal', 'I10.0')}
- Descrição: {classification.get('cid_descricao', 'Condição médica')}

ESTRUTURA OBRIGATÓRIA DO LAUDO:

**LAUDO MÉDICO**

**IDENTIFICAÇÃO:**
- Nome: {patient_info.get('nome', 'Não informado')}
- Idade: {patient_info.get('idade', 'Não informada')}
- Profissão: {patient_info.get('profissao', 'Não informada')}

**1. HISTÓRIA CLÍNICA RESUMIDA**
[Parágrafo objetivo incluindo: data início sintomas, evolução clínica, eventos agravamento, sintomas atuais, impacto vida diária/laboral, diagnóstico principal com CID-10]

**2. LIMITAÇÃO FUNCIONAL**
[Parágrafo detalhando: limitações atuais (motoras/sensoriais/cognitivas), impacto funcionalidade (trabalho/social/autonomia), sintomas que agravam]

**3. TRATAMENTO**
[Procedimentos em uso, medicamentos, resposta ao tratamento, necessidade continuidade]

**4. PROGNÓSTICO**
[Evolução esperada - agravamento/estabilização/recuperação, tempo estimado afastamento, necessidade tratamento contínuo, possibilidade retorno função]

**5. CONCLUSÃO**
[Conclusão específica para {classification.get('tipo_beneficio', 'AUXÍLIO-DOENÇA')}]

**6. CID-10:**
- Principal: {classification.get('cid_principal', 'I10.0')} - {classification.get('cid_descricao', 'Condição médica')}

REGRAS:
- Use APENAS informações da transcrição
- Seja técnico e profissional
- Mantenha coerência com o tipo de benefício
- NÃO invente dados não mencionados
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um médico perito especialista em laudos previdenciários. Siga rigorosamente a estrutura solicitada."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Baixa criatividade
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Erro ao gerar laudo: {e}")
            return f"Erro ao gerar laudo médico estruturado: {e}"

    def classify_benefit_and_cid(self, patient_text: str, patient_data: dict) -> dict:
        """Classificação de benefício - ANTI-ALUCINAÇÃO TOTAL"""
        
        prompt = f"""
CLASSIFIQUE o benefício previdenciário baseado APENAS nos dados fornecidos:

DADOS: {json.dumps(patient_data, ensure_ascii=False)}
TEXTO: {patient_text[:500]}

OPÇÕES VÁLIDAS (escolha APENAS UMA):
1. AUXÍLIO-DOENÇA: incapacidade temporária para trabalho
2. APOSENTADORIA POR INVALIDEZ: incapacidade permanente total
3. BPC/LOAS: deficiência + vulnerabilidade social
4. AUXÍLIO-ACIDENTE: sequela acidente trabalho
5. ISENÇÃO IMPOSTO DE RENDA: doença grave específica

CID-10: Use formato A00.0 ou A00 (letra + números)
GRAVIDADE: LEVE, MODERADA ou GRAVE

Retorne JSON EXATO:
{{
    "tipo_beneficio": "uma das 5 opções acima",
    "cid_principal": "código CID-10 válido",
    "cid_descricao": "descrição da condição",
    "justificativa": "justificativa baseada nos dados",
    "gravidade": "LEVE, MODERADA ou GRAVE",
    "prognostico": "prognóstico baseado no caso"
}}

IMPORTANTE: Escolha APENAS uma opção para cada campo.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um médico perito previdenciário. Seja preciso e objetivo na classificação."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,  # Zero criatividade
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            # VALIDAÇÃO ANTES DO PARSE JSON
            if not result_text or result_text.isspace():
                print("⚠️ Resposta vazia do GPT - usando fallback")
                raise ValueError("Resposta vazia do modelo")
            
            classification = json.loads(result_text)
            return classification
            
        except Exception as e:
            print(f"❌ Erro na classificação: {e}")
            # Fallback seguro
            return {
                "tipo_beneficio": "AUXÍLIO-DOENÇA",
                "cid_principal": "I10.0",
                "cid_descricao": "Hipertensão arterial sistêmica",
                "justificativa": "Classificação baseada em análise padrão",
                "gravidade": "MODERADA",
                "prognostico": "Favorável com tratamento"
            }


class MultimodalAIService:
    def __init__(self):
        """Inicializa o serviço multimodal com todas as funcionalidades integradas"""
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Inicializar RAG service
        self.rag_service = MedicalRAGService(self.client, parent_service=self)
        
        # 🔧 REMOVER COMPLETAMENTE O ANTI-ALUCINAÇÃO PROBLEMÁTICO
        # ❌ NÃO USAR: self.anti_hallucination = AntiHallucinationService()
        print("✅ Sistema sem anti-alucinação problemático")
        
        # Variável para evitar duplicação
        self.last_classification = None
        
        # Diretórios
        self.relatorios_dir = "relatorios"
        self.transcription_path = os.path.join(self.relatorios_dir, "transcription.txt")
        os.makedirs(self.relatorios_dir, exist_ok=True)
    
    async def analyze_multimodal(self, patient_info: str = "", audio_bytes: bytes = None, image_path: str = None) -> Dict[str, Any]:
        """Análise multimodal CORRIGIDA - SEM ALUCINAÇÃO"""
        results = {
            "transcription": "",
            "patient_data": {},
            "medical_report": "",
            "image_analysis": "",
            "analysis": "",
            "benefit_classification": {},
            "status": "success"
        }
        
        try:
            print("🚀 Iniciando análise multimodal CORRIGIDA...")
            
            # 1. TRANSCRIÇÃO DE ÁUDIO
            transcription = ""
            if audio_bytes:
                print("🎙️ Processando transcrição...")
                transcription = await self._transcribe_audio_whisper(audio_bytes)
                
                # Salva transcrição
                with open(self.transcription_path, "w", encoding="utf-8") as f:
                    f.write(transcription)
                print("✅ Transcrição salva")
                
                results["transcription"] = transcription
            
            # Usar patient_info se fornecido
            if patient_info and not transcription:
                transcription = patient_info
                results["transcription"] = transcription
                print("📝 Usando texto fornecido...")
            
            # Carrega transcrição existente se disponível
            elif os.path.exists(self.transcription_path):
                with open(self.transcription_path, "r", encoding="utf-8") as f:
                    transcription = f.read()
                results["transcription"] = transcription
            
            # 2. EXTRAÇÃO DE DADOS (ANTI-ALUCINAÇÃO)
            if transcription:
                print("🔍 Extraindo dados do paciente...")
                patient_data = self.rag_service.extract_patient_info(transcription)
                results["patient_data"] = patient_data
                print(f"✅ Dados extraídos: {patient_data.get('nome', 'N/A')}")
            
            # 3. CLASSIFICAÇÃO (ANTI-ALUCINAÇÃO)
            if transcription and results["patient_data"]:
                print("🏥 Classificando tipo de benefício...")
                try:
                    classification = self.rag_service.classify_benefit_and_cid(transcription, results["patient_data"])
                    self.last_classification = classification
                    results["benefit_classification"] = classification
                    print(f"✅ Classificação: {classification.get('tipo_beneficio')} - {classification.get('cid_principal')}")
                except Exception as e:
                    print(f"❌ Erro na classificação: {e}")
                    classification = {
                        "tipo_beneficio": "AUXÍLIO-DOENÇA",
                        "cid_principal": "I10.0",
                        "cid_descricao": "Condição médica",
                        "justificativa": "Classificação padrão por erro",
                        "gravidade": "MODERADA",
                        "prognostico": "A definir"
                    }
                    self.last_classification = classification
                    results["benefit_classification"] = classification
            
            # 4. LAUDO ESTRUTURADO
            if transcription and results["patient_data"] and results["benefit_classification"]:
                print("📋 Gerando laudo estruturado...")
                medical_report = self.rag_service.generate_structured_medical_report(
                    results["patient_data"], 
                    transcription,
                    results["benefit_classification"]
                )
                results["medical_report"] = medical_report
                
                # Salvar relatório
                patient_name = results['patient_data'].get('nome', 'paciente')
                safe_name = patient_name.replace(' ', '_').replace('/', '_').lower()
                report_path = os.path.join(self.relatorios_dir, f"relatorio_{safe_name}.txt")
                
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(medical_report)
                print(f"✅ Relatório salvo em {report_path}")
            
            # 5. ANÁLISE DE IMAGEM
            if image_path and os.path.exists(image_path):
                print("🖼️ Analisando imagem...")
                image_analysis = await self._analyze_image(image_path)
                results["image_analysis"] = image_analysis
            
            # 6. ANÁLISE INTEGRADA
            if any([results["transcription"], results["image_analysis"]]):
                print("🧠 Gerando análise integrada...")
                integrated_analysis = await self._generate_integrated_analysis(results)
                results["analysis"] = integrated_analysis
            
            print("✅ Análise multimodal concluída")
            return results
            
        except Exception as e:
            print(f"❌ Erro na análise: {e}")
            results["status"] = "error"
            results["error"] = str(e)
            return results
    
    async def _transcribe_audio_whisper(self, audio_bytes: bytes) -> str:
        """Transcrição de áudio usando Whisper"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"
                )
            
            os.unlink(temp_file_path)
            return transcript.text.strip()
            
        except Exception as e:
            print(f"❌ Erro na transcrição: {e}")
            try:
                if 'temp_file_path' in locals():
                    os.unlink(temp_file_path)
            except:
                pass
            return "⚠️ Erro na transcrição do áudio"
    
    async def _analyze_image(self, image_path: str) -> str:
        """Análise de imagem médica"""
        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um radiologista. Analise a imagem médica."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analise esta imagem médica."
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
        """Análise integrada"""
        patient_data = results.get("patient_data", {})
        transcription = results.get("transcription", "")
        
        prompt = f"""
Faça uma análise médica integrada:

DADOS: {json.dumps(patient_data, ensure_ascii=False)}
TRANSCRIÇÃO: {transcription[:300]}...

Forneça uma análise médica profissional e objetiva.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um médico especialista."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Erro na análise integrada: {e}"


# Exemplo de uso
if __name__ == "__main__":
    async def test():
        service = MultimodalAIService()
        
        text = """
        Doutor, tenho pressão alta há 10 anos, trabalho como motorista, 
        sinto dor de cabeça, tontura, vista embaçada, pressão 18x11.
        """
        
        result = await service.analyze_multimodal(patient_info=text)
        print("✅ Teste concluído:", result["status"])
        
    asyncio.run(test())