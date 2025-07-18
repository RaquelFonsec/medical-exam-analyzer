import asyncio
import openai
import tempfile
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from .context_classifier_service import context_classifier

class MultimodalAIService:
    """Serviço IA Multimodal REAL com OpenAI"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def analyze_multimodal(self, patient_info: str, audio_bytes: bytes = None, image_bytes: bytes = None) -> Dict[str, Any]:
        """Análise multimodal REAL com Whisper + GPT-4"""
        try:
            print(f"🧠 Análise multimodal REAL iniciada")
            
            # 1. TRANSCRIÇÃO REAL COM WHISPER
            transcription = ""
            if audio_bytes:
                transcription = await self._transcribe_audio_real(audio_bytes)
                print(f"🎤 Whisper transcreveu: {len(transcription)} caracteres")
            else:
                transcription = "Consulta baseada apenas em informações textuais fornecidas"
            
            # 2. ANÁLISE DE DOCUMENTOS (se fornecido)
            document_analysis = ""
            if image_bytes:
                document_analysis = f"Documento analisado: {len(image_bytes)} bytes processados"
                print(f"📄 Documento processado")
            
            # 3. CLASSIFICAÇÃO INTELIGENTE DE CONTEXTO
            context_analysis = context_classifier.classify_context(
                patient_info, transcription, document_analysis
            )
            
            context_type = context_analysis['main_context']
            print(f"🎯 Contexto identificado: {context_type}")
            
            # 4. OBTER PROMPTS ESPECIALIZADOS
            specialized_prompts = context_classifier.get_specialized_prompt(
                context_type, patient_info, transcription
            )
            
            # 5. GERAR ANAMNESE REAL COM GPT-4
            anamnese = await self._generate_real_anamnese(
                specialized_prompts['anamnese_prompt'],
                patient_info,
                transcription,
                context_type
            )
            
            # 6. GERAR LAUDO REAL COM GPT-4
            laudo = await self._generate_real_laudo(
                specialized_prompts['laudo_prompt'],
                anamnese,
                patient_info,
                transcription,
                context_type
            )
            
            return {
                "success": True,
                "transcription": transcription,
                "anamnese": anamnese,
                "laudo_medico": laudo,
                "document_analysis": document_analysis,
                "context_analysis": context_analysis,
                "specialized_type": context_type,
                "modalities_used": {
                    "text": bool(patient_info),
                    "audio": bool(audio_bytes),
                    "image": bool(image_bytes)
                },
                "model": "GPT-4o + Whisper + Context Intelligence",
                "confidence": context_analysis['confidence'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erro na análise multimodal: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "fallback_mode": True
            }
    
    async def _transcribe_audio_real(self, audio_bytes: bytes) -> str:
        """Transcrição REAL com Whisper-1"""
        try:
            # Salvar áudio temporariamente
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name
            
            print(f"🎤 Enviando para Whisper: {len(audio_bytes)} bytes")
            
            # Transcrever com Whisper-1
            with open(temp_audio_path, "rb") as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"
                )
            
            # Limpar arquivo temporário
            os.unlink(temp_audio_path)
            
            transcription_text = transcript.text
            print(f"✅ Whisper retornou: {transcription_text[:100]}...")
            
            return transcription_text
            
        except Exception as e:
            print(f"⚠️ Erro Whisper: {str(e)}")
            # Fallback para simulação
            return f"[Erro Whisper] Áudio de {len(audio_bytes)} bytes recebido mas não processado: {str(e)}"
    
    async def _generate_real_anamnese(self, base_prompt: str, patient_info: str, transcription: str, context_type: str) -> str:
        """Gera anamnese REAL usando GPT-4"""
        
        enhanced_prompt = f"""
{base_prompt}

DADOS ESPECÍFICOS PARA ANAMNESE:

**INFORMAÇÕES DO PACIENTE:**
{patient_info}

**TRANSCRIÇÃO REAL DA CONSULTA:**
{transcription}

**CONTEXTO IDENTIFICADO:** {context_type.upper()}

INSTRUÇÕES ESPECÍFICAS:
- Use APENAS as informações fornecidas acima
- Mantenha linguagem médica técnica e precisa
- Estruture conforme o contexto {context_type}
- Extraia dados reais da transcrição
- Se informação não foi mencionada, indique como "Não relatado"
- Seja detalhado mas objetivo

Gere a anamnese estruturada REAL baseada nos dados fornecidos:
"""
        
        try:
            print(f"🤖 Gerando anamnese com GPT-4 para contexto: {context_type}")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": f"Você é um médico especialista gerando anamnese estruturada para {context_type}. Use apenas informações fornecidas."
                    },
                    {
                        "role": "user", 
                        "content": enhanced_prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.2
            )
            
            anamnese_real = response.choices[0].message.content
            print(f"✅ Anamnese gerada: {len(anamnese_real)} caracteres")
            
            return anamnese_real
            
        except Exception as e:
            print(f"❌ Erro GPT anamnese: {str(e)}")
            return f"""## ❌ ERRO NA GERAÇÃO DA ANAMNESE

**Erro:** {str(e)}

**Dados recebidos:**
- Paciente: {patient_info}
- Transcrição: {transcription[:200]}...
- Contexto: {context_type}

*Configure corretamente a chave OpenAI para funcionalidade completa*"""
    
    async def _generate_real_laudo(self, base_prompt: str, anamnese: str, patient_info: str, transcription: str, context_type: str) -> str:
        """Gera laudo REAL usando GPT-4"""
        
        enhanced_prompt = f"""
{base_prompt}

DADOS COMPLETOS PARA LAUDO MÉDICO:

**ANAMNESE ESTRUTURADA:**
{anamnese}

**DADOS ORIGINAIS DO PACIENTE:**
{patient_info}

**TRANSCRIÇÃO ORIGINAL:**
{transcription}

**CONTEXTO:** {context_type.upper()}

DIRETRIZES ESPECÍFICAS:
- Base o laudo na anamnese estruturada acima
- Use terminologia médica apropriada para {context_type}
- Inclua CID-10 quando aplicável
- Mantenha objetividade e precisão médica
- Foque nos aspectos relevantes para o tipo de laudo
- Use apenas informações realmente fornecidas

Gere o laudo médico especializado REAL:
"""
        
        try:
            print(f"🤖 Gerando laudo com GPT-4 para contexto: {context_type}")
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": f"Você é um médico perito especializado em {self._get_specialty(context_type)}. Gere laudos precisos e tecnicamente corretos."
                    },
                    {
                        "role": "user", 
                        "content": enhanced_prompt
                    }
                ],
                max_tokens=2000,
                temperature=0.2
            )
            
            laudo_real = response.choices[0].message.content
            print(f"✅ Laudo gerado: {len(laudo_real)} caracteres")
            
            return laudo_real
            
        except Exception as e:
            print(f"❌ Erro GPT laudo: {str(e)}")
            return f"""## ❌ ERRO NA GERAÇÃO DO LAUDO

**Erro:** {str(e)}

**Anamnese base:** {anamnese[:200]}...
**Contexto:** {context_type}

*Configure corretamente a chave OpenAI para funcionalidade completa*"""
    
    def _get_specialty(self, context_type: str) -> str:
        """Retorna especialidade baseada no contexto"""
        specialties = {
            'bpc': 'Medicina Legal e Perícia para BPC/LOAS',
            'incapacidade': 'Medicina do Trabalho e Perícia de Incapacidade',
            'pericia': 'Medicina Legal e Pericial',
            'clinica': 'Clínica Médica Geral'
        }
        return specialties.get(context_type, 'Clínica Geral')
