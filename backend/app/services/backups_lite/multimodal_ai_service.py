from .transcription_service import TranscriptionService
from .context_classifier_service import ContextClassifierService
from typing import Dict, Any
import json
from datetime import datetime

class MultimodalAIService:
    def __init__(self):
        print("🧠 Inicializando MultimodalAIService ORIGINAL...")
        self.transcription_service = TranscriptionService()
        try:
            self.context_classifier = ContextClassifierService()
        except:
            self.context_classifier = None
        print("✅ MultimodalAIService ORIGINAL inicializado")
    
    async def analyze_multimodal(self, audio_file, patient_info: str):
        """Método original de análise"""
        return await self.analyze_consultation_intelligent(audio_file, patient_info)
    
    async def analyze_consultation_intelligent(self, audio_file, patient_info: str):
        """Análise usando sistema original (sem BERT/RAG pesados)"""
        
        try:
            # 1. Transcrição usando Whisper
            print("🎤 Transcrevendo áudio com Whisper...")
            transcription = await self.transcription_service.transcribe_audio(audio_file)
            
            # 2. Classificação de contexto básica
            context_type = self._classify_context_simple(patient_info, transcription)
            
            # 3. Análise simples baseada em palavras-chave
            analysis = self._analyze_content_keywords(transcription, patient_info)
            
            # 4. Gerar anamnese usando template
            anamnese = self._generate_anamnese_template(analysis, context_type)
            
            # 5. Gerar laudo usando template
            laudo = self._generate_laudo_template(analysis, context_type)
            
            return {
                "success": True,
                "transcription": transcription,
                "patient_info": patient_info,
                "context_analysis": {"main_context": context_type},
                "anamnese": anamnese,
                "laudo_medico": laudo,
                "model": "Sistema Original - Whisper + Templates",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Erro na análise: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcription": "Erro na transcrição",
                "anamnese": "Erro na geração de anamnese",
                "laudo_medico": "Erro na geração de laudo"
            }
    
    def _classify_context_simple(self, patient_info: str, transcription: str) -> str:
        """Classificação simples de contexto"""
        combined_text = (patient_info + " " + transcription).lower()
        
        if any(word in combined_text for word in ['bpc', 'loas', 'vida independente', 'cuidador']):
            return 'bpc'
        elif any(word in combined_text for word in ['incapacidade', 'trabalho', 'profissao']):
            return 'incapacidade'
        elif any(word in combined_text for word in ['acidente', 'auxilio']):
            return 'auxilio_acidente'
        elif any(word in combined_text for word in ['cancer', 'tumor', 'isencao']):
            return 'isencao_ir'
        else:
            return 'incapacidade'
    
    def _analyze_content_keywords(self, transcription: str, patient_info: str) -> Dict:
        """Análise básica por palavras-chave"""
        import re
        
        combined_text = transcription + " " + patient_info
        
        # Extrair informações básicas
        analysis = {
            'sintomas': [],
            'limitacoes': [],
            'profissao': '',
            'idade': '',
            'nome': ''
        }
        
        # Nome
        nome_match = re.search(r'(?:nome|chamo|sou)\s+(?:é\s+)?(\w+(?:\s+\w+)*)', combined_text, re.IGNORECASE)
        if nome_match:
            analysis['nome'] = nome_match.group(1)
        
        # Idade
        idade_match = re.search(r'(\d{1,3})\s*anos?', combined_text, re.IGNORECASE)
        if idade_match:
            analysis['idade'] = idade_match.group(1)
        
        # Profissão
        prof_match = re.search(r'(?:trabalho como|sou|profissão)\s+(\w+(?:\s+\w+)*)', combined_text, re.IGNORECASE)
        if prof_match:
            analysis['profissao'] = prof_match.group(1)
        
        # Sintomas básicos
        sintoma_patterns = ['dor', 'tontura', 'fraqueza', 'formigamento', 'dormência']
        for pattern in sintoma_patterns:
            if pattern in combined_text.lower():
                analysis['sintomas'].append(pattern)
        
        # Limitações básicas
        if 'não consigo' in combined_text.lower():
            analysis['limitacoes'].append('limitação funcional relatada')
        
        return analysis
    
    def _generate_anamnese_template(self, analysis: Dict, context_type: str) -> str:
        """Gera anamnese usando template simples"""
        
        nome = analysis.get('nome', '[Nome não identificado]')
        idade = analysis.get('idade', '[Idade não informada]')
        profissao = analysis.get('profissao', '[Profissão não informada]')
        
        sintomas_text = ', '.join(analysis.get('sintomas', ['sintomas relatados']))
        limitacoes_text = ', '.join(analysis.get('limitacoes', ['limitações relatadas']))
        
        return f"""
## 📋 1. IDENTIFICAÇÃO DO PACIENTE
- Nome: {nome}
- Idade: {idade} anos
- Profissão: {profissao}
- Data da consulta: {datetime.now().strftime('%d/%m/%Y')}

## 🗣️ 2. QUEIXA PRINCIPAL
Paciente relata {sintomas_text} e {limitacoes_text}.

## 📖 3. HISTÓRIA DA DOENÇA ATUAL (HDA)
Baseado no relato da consulta de telemedicina.

## 🏥 4. ANTECEDENTES PESSOAIS E FAMILIARES RELEVANTES
[Não relatado na consulta]

## 📄 5. DOCUMENTAÇÃO APRESENTADA
[Conforme documentos apresentados]

## 🎥 6. EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)
Consulta realizada por telemedicina.

## ⚕️ 7. AVALIAÇÃO MÉDICA (ASSESSMENT)
Avaliação baseada no contexto de {context_type}.

**MODALIDADE:** Telemedicina
**DATA:** {datetime.now().strftime('%d/%m/%Y')}
"""
    
    def _generate_laudo_template(self, analysis: Dict, context_type: str) -> str:
        """Gera laudo usando template simples"""
        
        nome = analysis.get('nome', '[Nome não identificado]')
        
        return f"""
## 🏥 LAUDO MÉDICO - {context_type.upper()}

### 📋 IDENTIFICAÇÃO
- Paciente: {nome}
- Data: {datetime.now().strftime('%d/%m/%Y')}
- Modalidade: Telemedicina

### 1. 📖 HISTÓRIA CLÍNICA
Baseado no relato da consulta.

### 2. 🚫 LIMITAÇÃO FUNCIONAL
Conforme relatado na consulta.

### 3. 🔬 EXAMES (Quando Houver)
Conforme documentação apresentada.

### 4. 💊 TRATAMENTO
Conforme relatado.

### 5. 🔮 PROGNÓSTICO
A ser avaliado conforme evolução.

### 6. ⚖️ CONCLUSÃO
Laudo elaborado baseado em consulta de telemedicina.

**OBSERVAÇÃO:** Documento gerado por sistema original
"""

# Instância global
multimodal_ai_service = MultimodalAIService()
