import asyncio
import openai
import tempfile
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# CFM COMPLIANCE INTEGRADO
class CFMComplianceService:
    """Serviço de Compliance CFM para Telemedicina"""
    
    def __init__(self):
        self.restricted_contexts = {
            "auxilio_acidente": {
                "allowed": False,
                "reason": "Nexo causal trabalhista requer exame físico presencial obrigatório",
                "cfm_resolution": "CFM 2.314/2022 - Art. 4º",
                "alternative": "Avaliação clínica geral sem estabelecimento de nexo causal trabalhista",
                "warning": "⚠️ ATENÇÃO CFM: Nexo causal trabalhista NÃO pode ser estabelecido por telemedicina",
                "recommendation": "Orientar reavaliação presencial para estabelecimento de nexo causal"
            },
            "acidente_trabalho": {
                "allowed": False,
                "reason": "Perícia ocupacional e medicina do trabalho exigem exame físico presencial",
                "cfm_resolution": "CFM 2.314/2022 - Art. 4º",
                "alternative": "Descrição clínica das limitações funcionais sem nexo causal",
                "warning": "⚠️ ATENÇÃO CFM: Perícia trabalhista requer avaliação presencial obrigatória",
                "recommendation": "Encaminhar para perícia médica presencial"
            }
        }
        
        self.allowed_contexts = {
            "bpc": {"allowed": True, "description": "Benefício de Prestação Continuada"},
            "incapacidade": {"allowed": True, "description": "Auxílio-doença/Aposentadoria por invalidez"},
            "isencao_ir": {"allowed": True, "description": "Isenção de Imposto de Renda"},
            "pericia": {"allowed": True, "description": "Perícia médica"},
            "clinica": {"allowed": True, "description": "Consulta clínica geral"}
        }
        
        self.restriction_keywords = {
            "nexo_causal": [
                "nexo causal", "acidente trabalho", "acidente na obra", 
                "acidente na fabrica", "cat", "comunicação acidente"
            ]
        }
    
    def validate_telemedicine_scope(self, context_type: str, transcription: str = "") -> Dict[str, Any]:
        """Validar se o contexto é permitido por telemedicina"""
        
        context_lower = context_type.lower()
        transcription_lower = transcription.lower()
        
        # 1. VERIFICAR CONTEXTOS EXPLICITAMENTE RESTRITOS
        for restricted_context, details in self.restricted_contexts.items():
            if restricted_context in context_lower:
                return {
                    "compliant": False,
                    "restricted": True,
                    "context_found": restricted_context,
                    "restriction_details": details,
                    "warning": details["warning"],
                    "alternative": details["alternative"],
                    "recommendation": details["recommendation"],
                    "cfm_resolution": details["cfm_resolution"]
                }
        
        # 2. VERIFICAR PALAVRAS-CHAVE RESTRITAS NA TRANSCRIÇÃO
        for restriction_type, keywords in self.restriction_keywords.items():
            for keyword in keywords:
                if keyword in transcription_lower:
                    return {
                        "compliant": False,
                        "restricted": True,
                        "detected_keyword": keyword,
                        "warning": "⚠️ ATENÇÃO CFM: Nexo causal trabalhista detectado - requer avaliação presencial",
                        "alternative": "Avaliação clínica geral sem estabelecimento de nexo causal",
                        "recommendation": "Considerar reavaliação presencial"
                    }
        
        # 3. CONTEXTO PERMITIDO
        return {
            "compliant": True,
            "allowed": True,
            "warning": None
        }

# CONTEXT CLASSIFIER INTEGRADO
class IntegratedContextClassifier:
    """Context Classifier integrado com CFM"""
    
    def __init__(self):
        self.cfm_service = CFMComplianceService()
        
        self.specialty_keywords = {
            "ortopedia": ["coluna", "fratura", "carregar peso", "dor nas costas", "lombar"],
            "psiquiatria": ["depressao", "ansiedade", "panico", "transtorno mental"],
            "cardiologia": ["coracao", "infarto", "pressao alta", "cardiovascular"],
            "otorrinolaringologia": ["perda auditiva", "surdez", "ouvido", "headset"],
            "clinica_geral": ["geral", "clinico"]
        }
        
        self.benefit_keywords = {
            "auxilio_acidente": ["acidente trabalho", "nexo causal", "cat", "acidente na obra"],
            "bpc": ["bpc", "loas", "vida independente", "cuidador"],
            "incapacidade": ["incapacidade", "auxilio doenca", "nao consigo trabalhar"],
            "isencao_ir": ["cancer", "tumor", "isencao"],
            "clinica": ["consulta", "avaliacao"]
        }
    
    def classify_context(self, patient_info: str, transcription: str, documents_text: str = "") -> Dict[str, Any]:
        """Classificar contexto com CFM integrado"""
        
        full_text = f"{patient_info} {transcription} {documents_text}".lower()
        
        print(f"🔍 Analisando texto: {full_text[:200]}...")
        
        # 1. DETECTAR ESPECIALIDADE
        specialty_scores = {}
        for specialty, keywords in self.specialty_keywords.items():
            score = sum(1 for keyword in keywords if keyword in full_text)
            if score > 0:
                specialty_scores[specialty] = score
        
        detected_specialty = max(specialty_scores.items(), key=lambda x: x[1])[0] if specialty_scores else "clinica_geral"
        print(f"🏥 Especialidade detectada: {detected_specialty}")
        
        # 2. DETECTAR BENEFÍCIO
        benefit_scores = {}
        for benefit, keywords in self.benefit_keywords.items():
            score = sum(1 for keyword in keywords if keyword in full_text)
            if score > 0:
                benefit_scores[benefit] = score
        
        main_benefit = max(benefit_scores.items(), key=lambda x: x[1])[0] if benefit_scores else "incapacidade"
        print(f"🎯 Benefício detectado: {main_benefit}")
        
        # 3. VERIFICAR CFM COMPLIANCE
        cfm_validation = self.cfm_service.validate_telemedicine_scope(main_benefit, transcription)
        print(f"⚖️ CFM Compliant: {cfm_validation['compliant']}")
        
        # 4. CRIAR CONTEXTO HÍBRIDO
        hybrid_context = f"{detected_specialty}_{main_benefit}"
        
        # 5. CALCULAR CONFIANÇA
        total_matches = sum(benefit_scores.values()) + sum(specialty_scores.values())
        confidence = min(total_matches * 0.2, 1.0)
        
        return {
            'main_context': hybrid_context,
            'main_benefit': main_benefit,
            'detected_specialty': detected_specialty,
            'confidence': confidence,
            'matched_keywords': {
                'specialty': [kw for kw in self.specialty_keywords[detected_specialty] if kw in full_text],
                'benefit': [kw for kw in self.benefit_keywords[main_benefit] if kw in full_text]
            },
            'cfm_compliant': cfm_validation['compliant'],
            'cfm_warning': cfm_validation.get('warning'),
            'cfm_alternative': cfm_validation.get('alternative'),
            'cfm_recommendation': cfm_validation.get('recommendation')
        }
    
    def get_specialized_prompt(self, context_type: str, patient_info: str, transcription: str) -> Dict[str, str]:
        """Obter prompts especializados"""
        
        return {
            'anamnese_prompt': f"""
Gere ANAMNESE ESTRUTURADA para {context_type}:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

Use estrutura médica formal de 7 pontos obrigatórios.
""",
            'laudo_prompt': f"""
Gere LAUDO MÉDICO para {context_type}:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

Use estrutura médica formal de 6 pontos obrigatórios.
"""
        }

# GERADOR DE DOCUMENTOS COM CFM
class CFMIntegratedDocumentGenerator:
    """Gerador de documentos com CFM integrado"""
    
    def __init__(self):
        self.cfm_service = CFMComplianceService()
    
    def gerar_anamnese_completa(self, dados: Dict[str, Any]) -> str:
        """Gerar anamnese com verificação CFM"""
        
        # Verificar CFM
        cfm_check = self.cfm_service.validate_telemedicine_scope(
            dados.get('beneficio', 'clinica'),
            dados.get('transcription', '')
        )
        
        if not cfm_check['compliant']:
            # Modificar para versão CFM compliant
            dados_modificados = dados.copy()
            dados_modificados['beneficio'] = 'incapacidade'  # Muda auxilio_acidente para incapacidade
            
            anamnese_base = self._gerar_anamnese_basica(dados_modificados)
            
            cfm_header = f"""
⚠️ ATENÇÃO CFM - RESTRIÇÃO DE TELEMEDICINA

{cfm_check.get('warning', 'Restrição detectada')}

ALTERNATIVA: {cfm_check.get('alternative', 'Avaliação clínica geral')}

═══════════════════════════════════════════════════════════════

"""
            
            cfm_footer = f"""

═══════════════════════════════════════════════════════════════

IMPORTANTE: Esta avaliação não estabelece nexo causal trabalhista conforme CFM 2.314/2022.
Para nexo causal, é necessária reavaliação presencial.

RECOMENDAÇÃO: {cfm_check.get('recommendation', 'Reavaliação presencial')}
"""
            
            return cfm_header + anamnese_base + cfm_footer
        
        else:
            # Caso permitido - gerar normalmente
            return self._gerar_anamnese_basica(dados)
    
    def gerar_laudo_completo(self, dados: Dict[str, Any]) -> str:
        """Gerar laudo com verificação CFM"""
        
        # Verificar CFM
        cfm_check = self.cfm_service.validate_telemedicine_scope(
            dados.get('beneficio', 'clinica'),
            dados.get('transcription', '')
        )
        
        if not cfm_check['compliant']:
            # Modificar para versão CFM compliant
            dados_modificados = dados.copy()
            dados_modificados['beneficio'] = 'incapacidade'
            
            laudo_base = self._gerar_laudo_basico(dados_modificados)
            
            cfm_header = f"""
⚠️ ATENÇÃO CFM - RESTRIÇÃO DE TELEMEDICINA

{cfm_check.get('warning', 'Restrição detectada')}

═══════════════════════════════════════════════════════════════

"""
            
            cfm_footer = f"""

═══════════════════════════════════════════════════════════════

CONCLUSÃO MODIFICADA PARA COMPLIANCE CFM:

AVALIAÇÃO DE LIMITAÇÕES FUNCIONAIS (SEM NEXO CAUSAL):
O paciente apresenta limitações funcionais que reduzem sua capacidade laboral.

IMPORTANTE: O nexo causal trabalhista NÃO pode ser estabelecido por telemedicina (CFM 2.314/2022).

PARECER: Limitações funcionais descritas sem estabelecimento de nexo causal trabalhista.

RECOMENDAÇÃO: {cfm_check.get('recommendation', 'Reavaliação presencial para nexo causal')}
"""
            
            return cfm_header + laudo_base + cfm_footer
        
        else:
            # Caso permitido - gerar normalmente
            return self._gerar_laudo_basico(dados)
    
    def _gerar_anamnese_basica(self, dados: Dict[str, Any]) -> str:
        """Gerar anamnese básica estruturada"""
        
        from datetime import datetime
        
        especialidade = dados.get('especialidade', 'clinica_geral')
        beneficio = dados.get('beneficio', 'clinica')
        patient_info = dados.get('patient_info', '')
        transcription = dados.get('transcription', '')
        
        return f"""
ANAMNESE PARA {beneficio.upper()} - MODALIDADE: TELEMEDICINA

1. IDENTIFICAÇÃO DO PACIENTE
Conforme informações fornecidas: {patient_info}

2. QUEIXA PRINCIPAL
Solicitação de avaliação médica para {beneficio}

3. HISTÓRIA DA DOENÇA ATUAL (HDA)
Baseada no relato: {transcription}

4. ANTECEDENTES PESSOAIS E FAMILIARES
Conforme relatado durante teleconsulta

5. DOCUMENTAÇÃO APRESENTADA
Não foram apresentados documentos durante a teleconsulta

6. EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)
Avaliação visual por vídeo e relato do paciente

7. AVALIAÇÃO MÉDICA
Hipótese diagnóstica baseada no relato
Especialidade: {especialidade.title()}

MODALIDADE: Teleconsulta
DATA: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
"""
    
    def _gerar_laudo_basico(self, dados: Dict[str, Any]) -> str:
        """Gerar laudo básico estruturado"""
        
        from datetime import datetime
        
        especialidade = dados.get('especialidade', 'clinica_geral')
        beneficio = dados.get('beneficio', 'clinica')
        patient_info = dados.get('patient_info', '')
        transcription = dados.get('transcription', '')
        
        return f"""
LAUDO MÉDICO PARA {beneficio.upper()}

IDENTIFICAÇÃO
Paciente: {patient_info}
Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
Modalidade: Teleconsulta {especialidade.title()}

1. HISTÓRIA CLÍNICA
Baseada no relato fornecido durante teleconsulta

2. LIMITAÇÃO FUNCIONAL
Conforme descrito pelo paciente: {transcription}

3. EXAMES
Não foram apresentados exames durante a teleconsulta

4. TRATAMENTO
Conforme relatado pelo paciente

5. PROGNÓSTICO
Baseado na avaliação clínica por telemedicina

6. CONCLUSÃO
Avaliação médica realizada por telemedicina para {beneficio}

Médico Responsável: ________________________
CRM: ________________________
Especialidade: {especialidade.title()}
Data: {datetime.now().strftime('%d/%m/%Y')}
"""

# MULTIMODAL AI SERVICE CORRIGIDO
class MultimodalAIService:
    """Serviço IA Multimodal CORRIGIDO com CFM Compliance"""
    
    def __init__(self):
        print("🏥 Inicializando MultimodalAIService com CFM integrado...")
        
        try:
            self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            print("✅ OpenAI configurado")
        except Exception as e:
            print(f"⚠️ Erro OpenAI: {e}")
            self.openai_client = None
        
        # Inicializar serviços integrados
        self.context_classifier = IntegratedContextClassifier()
        self.document_generator = CFMIntegratedDocumentGenerator()
        
        print("✅ MultimodalAIService com CFM inicializado")
    
    async def analyze_multimodal(self, patient_info: str, audio_bytes: bytes = None, image_bytes: bytes = None) -> Dict[str, Any]:
        """Análise multimodal com CFM Compliance integrado"""
        
        try:
            print("🧠 Análise multimodal com CFM iniciada")
            
            # 1. TRANSCRIÇÃO COM WHISPER
            transcription = ""
            if audio_bytes:
                transcription = await self._transcribe_audio_real(audio_bytes)
                print(f"🎤 Whisper transcreveu: {len(transcription)} caracteres")
            else:
                transcription = "Consulta baseada apenas em informações textuais fornecidas"
            
            # 2. ANÁLISE DE DOCUMENTOS
            document_analysis = ""
            if image_bytes:
                document_analysis = f"Documento processado: {len(image_bytes)} bytes"
                print(f"📄 Documento analisado")
            
            # 3. CLASSIFICAÇÃO DE CONTEXTO COM CFM
            print("🔍 Classificando contexto com CFM...")
            classification = self.context_classifier.classify_context(
                patient_info, transcription, document_analysis
            )
            
            print(f"🎯 Contexto: {classification['main_context']}")
            print(f"⚖️ CFM Compliant: {classification['cfm_compliant']}")
            
            # 4. GERAR DOCUMENTOS COM CFM
            print("📝 Gerando documentos com CFM...")
            dados = {
                'especialidade': classification['detected_specialty'],
                'beneficio': classification['main_benefit'],
                'patient_info': patient_info,
                'transcription': transcription
            }
            
            anamnese = self.document_generator.gerar_anamnese_completa(dados)
            laudo = self.document_generator.gerar_laudo_completo(dados)
            
            # 5. DETERMINAR STATUS CFM
            cfm_status = "✅ Permitido" if classification['cfm_compliant'] else "⚠️ Limitações"
            cfm_message = classification.get('cfm_warning') or "✅ Conforme CFM 2.314/2022"
            
            return {
                "success": True,
                "transcription": transcription,
                "anamnese": anamnese,
                "laudo_medico": laudo,
                "document_analysis": document_analysis,
                "context_analysis": classification,
                "specialized_type": classification['main_benefit'],
                "cfm_compliant": classification['cfm_compliant'],
                "cfm_status": cfm_status,
                "cfm_message": cfm_message,
                "modalities_used": {
                    "text": bool(patient_info),
                    "audio": bool(audio_bytes),
                    "image": bool(image_bytes)
                },
                "model": "Sistema Médico Completo v3.0 + CFM Compliance",
                "confidence": classification['confidence'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erro na análise: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "error": str(e),
                "transcription": transcription if 'transcription' in locals() else "Erro na transcrição",
                "anamnese": f"Erro na geração: {str(e)}",
                "laudo_medico": f"Erro na geração: {str(e)}",
                "cfm_status": "❌ Erro",
                "cfm_message": f"Erro técnico: {str(e)}"
            }
    
    async def _transcribe_audio_real(self, audio_bytes: bytes) -> str:
        """Transcrição REAL com Whisper-1"""
        
        if not self.openai_client:
            return f"[Erro OpenAI não configurado] Áudio de {len(audio_bytes)} bytes recebido"
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name
            
            print(f"🎤 Enviando para Whisper: {len(audio_bytes)} bytes")
            
            with open(temp_audio_path, "rb") as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"
                )
            
            os.unlink(temp_audio_path)
            return transcript.text
            
        except Exception as e:
            print(f"⚠️ Erro Whisper: {str(e)}")
            return f"[Erro Whisper] {str(e)}"
    
    # MÉTODOS DE COMPATIBILIDADE
    async def analyze_consultation_intelligent(self, audio_file, patient_info: str):
        """Método de compatibilidade com versão anterior"""
        if hasattr(audio_file, 'read'):
            audio_file.seek(0)
            audio_bytes = audio_file.read()
            return await self.analyze_multimodal(patient_info, audio_bytes, None)
        else:
            return await self.analyze_multimodal(patient_info, audio_file, None)

# Instância global
multimodal_ai_service = MultimodalAIService()

print("✅ Sistema Médico Completo v3.0 carregado com CFM Compliance integrado!")
print("🏥 Funcionalidades: Classificação + CFM + Documentos + Whisper")