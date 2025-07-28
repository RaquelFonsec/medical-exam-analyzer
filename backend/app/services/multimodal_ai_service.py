"""
Serviço de análise multimodal médica
Integra RAG, transcrição, análise de imagens e classificação de benefícios
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai

logger = logging.getLogger(__name__)


class MedicalRAGService:
    """Serviço RAG para busca de casos médicos similares"""
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY não encontrada")
        
        openai.api_key = self.openai_api_key
        self.client = openai.OpenAI(api_key=self.openai_api_key)
        
        # Tentar carregar serviço RAG existente
        try:
            from .rag.medical_rag_service import MedicalRAGService as ExistingRAG
            self.rag_instance = ExistingRAG()
            self.rag_available = True
            print("✅ RAG Service carregado com sucesso")
        except Exception as e:
            print(f"⚠️ RAG não disponível: {e}")
            self.rag_available = False
            self.rag_instance = None

    def search_similar_cases(self, patient_text: str, k: int = 3) -> List[Dict]:
        """Busca casos similares usando RAG"""
        if not self.rag_available:
            return []
        
        try:
            return self.rag_instance.search_similar_cases(patient_text, k)
        except Exception as e:
            print(f"❌ Erro na busca RAG: {e}")
            return []

    def generate_embeddings(self, text: str) -> List[float]:
        """Gera embeddings para texto"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Erro ao gerar embeddings: {e}")
            return []


class MultimodalAIService:
    """Serviço principal de análise multimodal médica"""
    
    def __init__(self):
        # Forçar configuração da API key
        try:
            from .force_openai_env import setup_openai_env
            setup_openai_env()
        except:
            pass
        
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            print("❌ OPENAI_API_KEY não encontrada - sistema limitado")
            self.client = None
        else:
            openai.api_key = self.openai_api_key
            self.client = openai.OpenAI(api_key=self.openai_api_key)
            print(f"✅ OpenAI configurado: {self.openai_api_key[:20]}...")
        
        # Inicializar RAG
        try:
            self.rag_service = MedicalRAGService()
            print("✅ RAG integrado ao MultimodalAIService")
        except Exception as e:
            print(f"⚠️ RAG não disponível: {e}")
            self.rag_service = None

        # Inicializar AWS Textract se disponível
        try:
            from .aws_textract_service import AWSTextractService, MedicalDocumentAnalyzer
            self.textract_service = AWSTextractService()
            self.medical_analyzer = MedicalDocumentAnalyzer()
            print("✅ AWS Textract integrado ao MultimodalAIService")
        except ImportError as e:
            print(f"⚠️ AWS Textract não disponível: {e}")
            self.textract_service = None
            self.medical_analyzer = None

        # Inicializar OCR fallback
        try:
            from .ocr_service import OCRService
            self.ocr_service = OCRService()
            print("✅ OCR Service carregado")
        except ImportError as e:
            print(f"⚠️ OCR Service não disponível: {e}")
            self.ocr_service = None

        # Inicializar Pydantic AI
        try:
            from .pydantic_ai_medical_service import get_pydantic_medical_ai
            self.pydantic_ai = get_pydantic_medical_ai()
            print("✅ Pydantic AI integrado (LangGraph + RAG + FAISS)")
        except Exception as e:
            print(f"⚠️ Pydantic AI não disponível: {e}")
            self.pydantic_ai = None

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcreve áudio usando Whisper"""
        try:
            import tempfile
            
            print(f"🎤 Iniciando transcrição de áudio: {len(audio_bytes)} bytes")
            
            if len(audio_bytes) < 100:
                print("⚠️ Arquivo de áudio muito pequeno")
                return ""
            
            # Determinar extensão correta
            file_extension = ".webm"
            if filename:
                if filename.endswith(('.mp3', '.wav', '.m4a', '.mp4', '.mpeg')):
                    file_extension = os.path.splitext(filename)[1]
            
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file.flush()
                
                print(f"📝 Arquivo temporário criado: {temp_file.name}")
                
                # Verificar se API key está disponível
                if not self.openai_api_key:
                    print("❌ OpenAI API Key não encontrada para transcrição")
                    return ""
                
                try:
                    with open(temp_file.name, "rb") as audio_file:
                        print("🔄 Enviando para OpenAI Whisper...")
                        transcript = self.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="pt",
                            response_format="text"
                        )
                    
                    # Se transcript é objeto, pegar o texto
                    transcription = transcript.text if hasattr(transcript, 'text') else str(transcript)
                    
                    print(f"✅ Transcrição bem-sucedida: '{transcription[:100]}...'")
                    
                    # Salvar transcrição
                    self._save_transcription(transcription)
                    
                    return transcription
                    
                except Exception as api_error:
                    print(f"❌ Erro na API OpenAI: {api_error}")
                    return ""
                
                finally:
                    # Limpar arquivo temporário
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                        print("🗑️ Arquivo temporário removido")
                
        except Exception as e:
            print(f"❌ Erro geral na transcrição: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def _save_transcription(self, transcription: str):
        """Salva transcrição em arquivo"""
        try:
            os.makedirs("relatorios", exist_ok=True)
            with open("relatorios/transcription.txt", "w", encoding="utf-8") as f:
                f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Transcrição: {transcription}\n")
            print("✅ Transcrição salva")
        except Exception as e:
            print(f"⚠️ Erro ao salvar transcrição: {e}")


    def extract_patient_info(self, text: str) -> Dict[str, Any]:
        """Extrai informações do paciente do texto"""
        if not self.client:
            print("⚠️ Cliente OpenAI não disponível - usando fallback")
            return self._fallback_patient_data()
            
        try:
            prompt = f"""Você é um assistente médico especializado em extração de dados. Extraia as informações do paciente do texto fornecido.

TEXTO PARA ANÁLISE:
{text}

Retorne APENAS um objeto JSON válido seguindo EXATAMENTE este formato:

{{
    "nome": "nome extraído do texto ou 'Paciente'",
    "idade": número_inteiro_ou_null,
    "sexo": "M", "F" ou null,
    "profissao": "profissão encontrada ou null",
    "sintomas": ["sintoma1", "sintoma2"],
    "medicamentos": ["medicamento1", "medicamento2"],
    "condicoes": ["condicao1", "condicao2"]
}}

REGRAS OBRIGATÓRIAS:
- Retorne APENAS o JSON, sem explicações
- Se não encontrar nome, use "Paciente"
- Se não encontrar idade, use null
- Listas vazias [] se não encontrar informações
- JSON deve ser válido e parseable"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um assistente médico especializado em extração de dados. Sempre retorne JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content.strip()
            
            print(f"🔍 DEBUG - Resposta OpenAI extract_patient_info: '{result_text[:200]}...'")
            
            if not result_text or result_text.isspace():
                print("⚠️ Resposta vazia do GPT - usando fallback")
                return self._fallback_patient_data()
            
            # Tentar limpar a resposta se não for JSON válido
            if not result_text.startswith('{'):
                # Procurar por JSON dentro da resposta
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    result_text = result_text[start_idx:end_idx+1]
                else:
                    print("⚠️ JSON não encontrado na resposta - usando fallback")
                    return self._fallback_patient_data()
            
            try:
                patient_data = json.loads(result_text)
                print(f"✅ Dados extraídos: {patient_data.get('nome', 'Não informado')}")
                return patient_data
            except json.JSONDecodeError as je:
                print(f"❌ Erro JSON específico: {je}")
                print(f"❌ Texto problemático: '{result_text}'")
                return self._fallback_patient_data()

        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            return self._fallback_patient_data()

    def _fallback_patient_data(self) -> Dict[str, Any]:
        """Dados fallback do paciente"""
        return {
            "nome": "Não informado",
            "idade": None,
            "sexo": None,
            "profissao": None,
            "sintomas": [],
            "medicamentos": [],
            "condicoes": []
        }

    def classify_benefit_and_cid(self, patient_data: Dict[str, Any], transcription: str = "") -> Dict[str, Any]:
        """Classifica tipo de benefício e CID"""
        if not self.client:
            print("⚠️ Cliente OpenAI não disponível - usando fallback")
            return self._fallback_classification()
            
        try:
            context = f"""
            DADOS DO PACIENTE: {json.dumps(patient_data, ensure_ascii=False)}
            TRANSCRIÇÃO: {transcription}
            """

            prompt = f"""Você é um médico perito previdenciário. Analise os dados médicos e classifique o caso.

DADOS MÉDICOS:
{context}

Retorne APENAS um objeto JSON válido seguindo EXATAMENTE este formato:

{{
    "tipo_beneficio": "AUXÍLIO-DOENÇA",
    "cid_principal": "I10.0", 
    "gravidade": "MODERADA",
    "prognostico": "Análise médica detalhada do prognóstico com base nos dados apresentados para determinação da capacidade funcional do paciente"
}}

OPÇÕES VÁLIDAS:
- tipo_beneficio: "AUXÍLIO-DOENÇA", "APOSENTADORIA POR INVALIDEZ", "BPC/LOAS", "AUXÍLIO-ACIDENTE", "ISENÇÃO IMPOSTO DE RENDA"
- cid_principal: formato A00.0 ou A00 (ex: I10.0, M54.5, F32.0)
- gravidade: "LEVE", "MODERADA", "GRAVE"
- prognostico: mínimo 30 caracteres

IMPORTANTE: Retorne APENAS o JSON válido, sem explicações adicionais."""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um médico perito previdenciário especializado. Sempre retorne JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=400,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content.strip()
            
            print(f"🔍 DEBUG - Resposta OpenAI classify_benefit: '{result_text[:200]}...'")
            
            if not result_text or result_text.isspace():
                print("⚠️ Resposta vazia na classificação - usando fallback")
                return self._fallback_classification()
            
            # Tentar limpar a resposta se não for JSON válido
            if not result_text.startswith('{'):
                # Procurar por JSON dentro da resposta
                start_idx = result_text.find('{')
                end_idx = result_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    result_text = result_text[start_idx:end_idx+1]
                else:
                    print("⚠️ JSON não encontrado na classificação - usando fallback")
                    return self._fallback_classification()
            
            try:
                classification = json.loads(result_text)
            except json.JSONDecodeError as je:
                print(f"❌ Erro JSON na classificação: {je}")
                print(f"❌ Texto problemático: '{result_text}'")
                return self._fallback_classification()
            
            # Validar e corrigir dados se necessário
            classification = self._validate_classification(classification)
            
            print(f"✅ Classificação: {classification.get('tipo_beneficio', 'AUXÍLIO-DOENÇA')}")
            return classification

        except Exception as e:
            print(f"❌ Erro na classificação: {e}")
            return self._fallback_classification()

    def _validate_classification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida e corrige dados de classificação"""
        # Corrigir tipo_beneficio se tiver "|"
        if "|" in str(data.get('tipo_beneficio', '')):
            data['tipo_beneficio'] = 'AUXÍLIO-DOENÇA'
        
        # Corrigir CID se for "não informado"
        if data.get('cid_principal', '').lower() in ['não informado', 'nao informado', '']:
            data['cid_principal'] = 'I10.0'
        
        # Corrigir gravidade se for "não informado"
        if data.get('gravidade', '').lower() in ['não informado', 'nao informado', '', 'não classificável']:
            data['gravidade'] = 'MODERADA'
        
        # Corrigir prognóstico se for muito curto
        if len(data.get('prognostico', '')) < 20:
            data['prognostico'] = 'Prognóstico requer avaliação médica continuada para determinação de capacidade funcional'
        
        return data

    def _fallback_classification(self) -> Dict[str, Any]:
        """Classificação fallback"""
        return {
            "tipo_beneficio": "AUXÍLIO-DOENÇA",
            "cid_principal": "I10.0",
            "gravidade": "MODERADA",
            "prognostico": "Prognóstico requer avaliação médica continuada"
        }

    def generate_structured_medical_report(self, patient_data: Dict[str, Any], 
                                          classification: Dict[str, Any],
                                          transcription: str = "") -> str:
        """Gera relatório médico estruturado conforme padrão profissional"""
        try:
            # Determinar tipo de benefício para conclusão específica
            tipo_beneficio = classification.get('tipo_beneficio', 'AUXÍLIO-DOENÇA')
            cid_principal = classification.get('cid_principal', 'I10.0')
            gravidade = classification.get('gravidade', 'MODERADA')
            nome_paciente = patient_data.get('nome', 'Paciente')
            idade = patient_data.get('idade', 0)
            
            # VERIFICAR IDADE E USAR PROMPT ESPECÍFICO
            is_child = idade and idade < 18
            
            if is_child:
                # PROMPT ESPECÍFICO PARA CRIANÇAS
                prompt = f"""
Você é um médico especialista em perícia previdenciária PEDIÁTRICA. Gere um LAUDO MÉDICO para uma CRIANÇA de {idade} anos.

=== DADOS PARA ANÁLISE ===
PACIENTE: {json.dumps(patient_data, ensure_ascii=False)}
CLASSIFICAÇÃO: {json.dumps(classification, ensure_ascii=False)} 
TRANSCRIÇÃO: {transcription}

**LAUDO MÉDICO ESPECIALIZADO**

**1. HISTÓRIA CLÍNICA RESUMIDA**
Paciente {nome_paciente}, {idade} anos, apresenta [condição clínica] com início [temporal]. Evolução clínica com [sintomas principais]. Limitações funcionais evidentes para atividades escolares e interação social. Diagnóstico compatível com CID-10: {cid_principal}.

**2. LIMITAÇÃO FUNCIONAL**
Limitações funcionais para atividades de vida diária, desenvolvimento neuropsicomotor e participação escolar. Comprometimento da autonomia pessoal e necessidades educacionais especiais.

**3. TRATAMENTO**
Acompanhamento médico especializado com [tratamentos específicos]. Necessidade de suporte multidisciplinar e reabilitação continuada.

**4. PROGNÓSTICO**
Prognóstico reservado com necessidade de acompanhamento especializado contínuo. Limitações permanentes com necessidade de suporte familiar e educacional.

**5. CONCLUSÃO CONGRUENTE COM O BENEFÍCIO**
Criança apresenta impedimento de longo prazo que impede participação plena na sociedade. Fundamenta indicação de {tipo_beneficio} considerando as necessidades especiais e suporte continuado.

**6. CID-10**
Código(s): {cid_principal}

REGRAS OBRIGATÓRIAS PARA CRIANÇAS:
- JAMAIS mencione trabalho, laboral, profissional, emprego
- Foque em desenvolvimento, escola, autonomia
- Use linguagem adequada para contexto pediátrico
- Máximo 3-4 linhas por seção
"""
            else:
                # PROMPT ESPECÍFICO PARA ADULTOS
                prompt = f"""
Você é um médico especialista em perícia previdenciária. Gere um LAUDO MÉDICO para ADULTO de {idade} anos.

=== DADOS PARA ANÁLISE ===
PACIENTE: {json.dumps(patient_data, ensure_ascii=False)}
CLASSIFICAÇÃO: {json.dumps(classification, ensure_ascii=False)} 
TRANSCRIÇÃO: {transcription}

**LAUDO MÉDICO ESPECIALIZADO**

**1. HISTÓRIA CLÍNICA RESUMIDA**
Paciente {nome_paciente}, {idade} anos, {patient_data.get('profissao', 'profissão não informada')}, refere início dos sintomas [temporal]. Evolução clínica com [sintomas principais]. Limitações funcionais evidentes para atividades laborais. Diagnóstico compatível com CID-10: {cid_principal}.

**2. LIMITAÇÃO FUNCIONAL**
Limitações funcionais que comprometem a capacidade laborativa e autonomia pessoal. Impacto direto sobre o desempenho profissional.

**3. TRATAMENTO**
Acompanhamento médico especializado conforme necessidade clínica. Tratamento continuado necessário.

**4. PROGNÓSTICO**
Prognóstico reservado com [expectativa temporal]. Possibilidade de readaptação profissional a ser avaliada.

**5. CONCLUSÃO CONGRUENTE COM O BENEFÍCIO**
Paciente apresenta [justificativa conforme benefício]. Fundamenta indicação de {tipo_beneficio}.

**6. CID-10**
Código(s): {cid_principal}

REGRAS PARA ADULTOS:
- Mencione impacto laboral adequadamente
- Use terminologia médica profissional
- Máximo 3-4 linhas por seção
"""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um médico especialista em perícia previdenciária. Siga RIGOROSAMENTE as instruções de idade."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )

            report = response.choices[0].message.content.strip()
            
            # Salvar relatório
            self._save_report(report, patient_data.get('nome', 'não_informado'))
            
            return report

        except Exception as e:
            print(f"❌ Erro ao gerar relatório: {e}")
            return self._fallback_report()

    def _save_report(self, report: str, patient_name: str):
        """Salva relatório em arquivo"""
        try:
            os.makedirs("relatorios", exist_ok=True)
            filename = f"relatorios/relatorio_{patient_name.lower().replace(' ', '_')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Relatório Médico\n")
                f.write("=" * 50 + "\n")
                f.write(report)
            print(f"✅ Relatório salvo em {filename}")
        except Exception as e:
            print(f"⚠️ Erro ao salvar relatório: {e}")

    def _fallback_report(self) -> str:
        """Relatório fallback quando há erro"""
        return """**LAUDO MÉDICO ESPECIALIZADO**

**1. HISTÓRIA CLÍNICA RESUMIDA**
Paciente apresenta quadro clínico que requer avaliação médica especializada para determinação da capacidade funcional e elegibilidade para benefícios previdenciários.

**2. LIMITAÇÃO FUNCIONAL**
Limitações funcionais evidentes que comprometem a autonomia e participação nas atividades cotidianas.

**3. TRATAMENTO**
Acompanhamento médico especializado conforme necessidade clínica do caso.

**4. PROGNÓSTICO**
Prognóstico a ser determinado mediante avaliação médica presencial detalhada.

**5. CONCLUSÃO CONGRUENTE COM O BENEFÍCIO**
Recomenda-se avaliação médica presencial para determinação adequada do benefício previdenciário.

**6. CID-10**
A ser determinado mediante avaliação clínica presencial.

Data: """ + datetime.now().strftime('%d/%m/%Y') + """
Observação: Laudo gerado por sistema de IA médica - Validação médica presencial OBRIGATÓRIA."""

    async def analyze_multimodal(self, patient_info: str = "", 
                                audio_bytes: bytes = None, 
                                image_path: str = None,
                                document_paths: List[str] = None) -> Dict[str, Any]:
        """Análise multimodal completa"""
        try:
            print("🚀 Iniciando análise multimodal...")
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "transcription": "",
                "patient_data": {},
                "classification": {},
                "medical_report": "",
                "rag_results": [],
                "image_analysis": None,
                "document_analysis": None
            }
            
            # 1. Transcrever áudio se fornecido
            if audio_bytes:
                print("🎙️ Processando áudio...")
                result["transcription"] = await self.transcribe_audio(audio_bytes)
            
            # 2. Combinar informações
            combined_text = f"{patient_info}\n{result['transcription']}"
            
            # 3. USAR PYDANTIC AI SE DISPONÍVEL (MELHOR PERFORMANCE)
            if self.pydantic_ai:
                print("🎯 Usando PYDANTIC AI + LANGGRAPH + RAG + FAISS...")
                try:
                    pydantic_result = await self.pydantic_ai.analyze_complete(
                        patient_text=patient_info,
                        transcription=result["transcription"]
                    )
                    
                    # Converter para formato compatível
                    result["patient_data"] = pydantic_result.patient_data.dict()
                    result["classification"] = pydantic_result.classification.dict()
                    result["medical_report"] = pydantic_result.laudo_medico
                    result["anamnese"] = pydantic_result.anamnese
                    result["confidence_score"] = pydantic_result.confidence_score
                    result["pydantic_analysis"] = True
                    
                    print("✅ Análise Pydantic AI concluída com sucesso!")
                    
                except Exception as e:
                    print(f"❌ Erro no Pydantic AI, usando fallback: {e}")
                    # Fallback para método original
                    result = await self._analyze_with_fallback(result, combined_text, patient_info)
            else:
                # Método original
                result = await self._analyze_with_fallback(result, combined_text, patient_info)
            
            # 6. Buscar casos similares com RAG
            if self.rag_service:
                print("🔍 Buscando casos similares...")
                result["rag_results"] = self.rag_service.search_similar_cases(combined_text)
            
            # 7. Analisar documentos se fornecidos
            if document_paths:
                print("📄 Analisando documentos...")
                result["document_analysis"] = await self._analyze_documents(document_paths)
            
            print("✅ Análise multimodal concluída")
            return result
            
        except Exception as e:
            print(f"❌ Erro na análise multimodal: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _analyze_documents(self, document_paths: List[str]) -> Dict[str, Any]:
        """Analisa documentos usando Textract ou OCR"""
        try:
            results = []
            
            for doc_path in document_paths:
                if self.textract_service:
                    # Usar AWS Textract
                    analysis = await self.textract_service.extract_text_from_document(doc_path)
                    if self.medical_analyzer:
                        medical_analysis = await self.medical_analyzer.analyze_medical_document(analysis)
                        results.append({
                            "path": doc_path,
                            "method": "AWS Textract",
                            "text": analysis.get("text", ""),
                            "medical_analysis": medical_analysis
                        })
                elif self.ocr_service:
                    # Usar OCR básico
                    text = self.ocr_service.extract_text_from_file(doc_path)
                    results.append({
                        "path": doc_path,
                        "method": "OCR",
                        "text": text,
                        "medical_analysis": None
                    })
            
            return {"documents": results, "total": len(results)}
            
        except Exception as e:
            print(f"❌ Erro na análise de documentos: {e}")
            return {"error": str(e), "documents": [], "total": 0} 

    async def _analyze_with_fallback(self, result: Dict[str, Any], combined_text: str, patient_info: str) -> Dict[str, Any]:
        """Método fallback usando análise original"""
        try:
            print("📝 Extraindo dados do paciente (fallback)...")
            result["patient_data"] = self.extract_patient_info(combined_text)
            
            print("🏥 Classificando benefício (fallback)...")
            result["classification"] = self.classify_benefit_and_cid(
                result["patient_data"], result["transcription"]
            )
            
            print("📋 Gerando relatório (fallback)...")
            result["medical_report"] = self.generate_structured_medical_report(
                result["patient_data"], result["classification"], result["transcription"]
            )
            
            result["pydantic_analysis"] = False
            return result
            
        except Exception as e:
            print(f"❌ Erro no fallback: {e}")
            result["error"] = str(e)
            result["pydantic_analysis"] = False
            return result 