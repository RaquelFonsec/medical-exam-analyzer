import re
from typing import Dict, List, Any
import openai
import os

class OutputValidatorService:
    """Validador de saída médica - Detecta alucinações com precisão cirúrgica"""
    
    def __init__(self):
        print("🛡️ Inicializando OutputValidatorService - Detector de Alucinações Médicas")
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.medical_terms_database = self._load_medical_terms_database()
        
    def _load_medical_terms_database(self):
        """Base de termos médicos que NÃO podem ser inventados"""
        return {
            'doencas_especificas': [
                'hipertensão', 'diabetes', 'cardiopatia', 'nefropatia', 'hepatopatia',
                'artrite', 'artrose', 'fibromialgia', 'lúpus', 'esclerose',
                'parkinson', 'alzheimer', 'epilepsia', 'enxaqueca', 'sinusite',
                'pneumonia', 'bronquite', 'asma', 'rinite', 'gastrite',
                'úlcera', 'refluxo', 'hérnia', 'catarata', 'glaucoma'
            ],
            'medicamentos_especificos': [
                'captopril', 'losartana', 'metformina', 'insulina', 'sinvastatina',
                'omeprazol', 'diclofenaco', 'ibuprofeno', 'paracetamol', 'dipirona',
                'amoxicilina', 'azitromicina', 'prednisona', 'dexametasona'
            ],
            'exames_especificos': [
                'ressonância magnética', 'tomografia computadorizada', 'ultrassonografia',
                'eletrocardiograma', 'eletroencefalograma', 'raio-x', 'radiografia',
                'colonoscopia', 'endoscopia', 'ecocardiograma', 'holter'
            ],
            'procedimentos_especificos': [
                'angioplastia', 'cateterismo', 'artroscopia', 'biópsia',
                'cirurgia bariátrica', 'transplante', 'hemodiálise'
            ]
        }
    
    async def validate_against_source_comprehensive(self, generated_text: str, original_facts: Dict, transcription: str) -> Dict[str, Any]:
        """Validação abrangente contra fonte original"""
        
        validation_result = {
            'has_hallucinations': False,
            'hallucination_flags': [],
            'safety_level': 'SAFE',
            'specific_issues': [],
            'text_modifications_needed': [],
            'validation_score': 1.0
        }
        
        # 1. VALIDAÇÃO DE TERMOS MÉDICOS NÃO MENCIONADOS
        medical_hallucinations = self._check_medical_term_hallucinations(
            generated_text, transcription
        )
        
        # 2. VALIDAÇÃO DE DADOS PESSOAIS INVENTADOS
        personal_data_hallucinations = self._check_personal_data_hallucinations(
            generated_text, original_facts
        )
        
        # 3. VALIDAÇÃO COM IA VERIFICADORA
        ai_validation = await self._ai_cross_validation(generated_text, transcription)
        
        # 4. VALIDAÇÃO DE CONSISTÊNCIA TEMPORAL
        temporal_hallucinations = self._check_temporal_consistency(
            generated_text, original_facts
        )
        
        # 5. COMPILAR RESULTADOS
        all_flags = (
            medical_hallucinations + 
            personal_data_hallucinations + 
            ai_validation.get('flags', []) +
            temporal_hallucinations
        )
        
        if all_flags:
            validation_result.update({
                'has_hallucinations': True,
                'hallucination_flags': all_flags,
                'safety_level': 'UNSAFE',
                'validation_score': max(0.0, 1.0 - (len(all_flags) * 0.2))
            })
        
        # 6. GERAR CORREÇÕES ESPECÍFICAS
        validation_result['corrections'] = self._generate_corrections(all_flags, generated_text)
        
        return validation_result
    
    def _check_medical_term_hallucinations(self, generated_text: str, transcription: str) -> List[Dict]:
        """Detecta termos médicos inventados"""
        flags = []
        generated_lower = generated_text.lower()
        transcription_lower = transcription.lower()
        
        for category, terms in self.medical_terms_database.items():
            for term in terms:
                if term in generated_lower and term not in transcription_lower:
                    flags.append({
                        'type': 'medical_term_hallucination',
                        'category': category,
                        'invented_term': term,
                        'severity': 'HIGH',
                        'action': 'REMOVE_OR_REPLACE'
                    })
        
        return flags
    
    def _check_personal_data_hallucinations(self, generated_text: str, original_facts: Dict) -> List[Dict]:
        """Detecta dados pessoais inventados"""
        flags = []
        
        # Verificar se IA inventou dados não fornecidos
        personal_data_patterns = {
            'idade_inventada': r'(\d{2,3})\s*anos?',
            'nome_inventado': r'(?:paciente|nome)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            'profissao_inventada': r'(?:profissão|trabalha como)\s+([a-zà-ÿ]+(?:\s+[a-zà-ÿ]+)*)'
        }
        
        confirmed_data = original_facts.get('dados_pessoais_confirmados', {})
        
        for data_type, pattern in personal_data_patterns.items():
            matches = re.findall(pattern, generated_text, re.IGNORECASE)
            for match in matches:
                corresponding_field = data_type.replace('_inventada', '_exato').replace('_inventado', '_exato')
                
                if corresponding_field not in confirmed_data:
                    flags.append({
                        'type': 'personal_data_hallucination',
                        'field': data_type,
                        'invented_value': match,
                        'severity': 'MEDIUM',
                        'action': 'REPLACE_WITH_NAO_INFORMADO'
                    })
        
        return flags
    
    async def _ai_cross_validation(self, generated_text: str, transcription: str) -> Dict:
        """Usa IA para detectar inconsistências"""
        
        validation_prompt = f"""
Você é um AUDITOR MÉDICO especializado em detectar informações inventadas.

TEXTO ORIGINAL (Fonte verdadeira):
{transcription}

TEXTO GERADO (Para verificar):
{generated_text}

INSTRUÇÕES CRÍTICAS:
1. Compare linha por linha
2. Identifique QUALQUER informação no texto gerado que NÃO está no texto original
3. Seja EXTREMAMENTE rigoroso
4. Foque em: sintomas, diagnósticos, medicamentos, exames, dados pessoais

RESPONDA APENAS no formato:
PROBLEMA: [descrição] | TIPO: [sintoma/medicamento/exame/dados] | SEVERIDADE: [ALTA/MEDIA/BAIXA]

Se não há problemas, responda: "VALIDACAO_OK"
"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": "Você é um auditor médico ultra-rigoroso que detecta qualquer informação inventada."
                }, {
                    "role": "user", 
                    "content": validation_prompt
                }],
                temperature=0.1,
                max_tokens=500
            )
            
            validation_response = response.choices[0].message.content
            
            if "VALIDACAO_OK" in validation_response:
                return {'flags': []}
            else:
                return self._parse_ai_validation_response(validation_response)
                
        except Exception as e:
            print(f"⚠️ Erro na validação por IA: {e}")
            return {'flags': []}
    
    def _parse_ai_validation_response(self, response: str) -> Dict:
        """Processa resposta da validação por IA"""
        flags = []
        
        lines = response.split('\n')
        for line in lines:
            if 'PROBLEMA:' in line:
                parts = line.split('|')
                if len(parts) >= 3:
                    problema = parts[0].replace('PROBLEMA:', '').strip()
                    tipo = parts[1].replace('TIPO:', '').strip()
                    severidade = parts[2].replace('SEVERIDADE:', '').strip()
                    
                    flags.append({
                        'type': 'ai_detected_hallucination',
                        'problem': problema,
                        'category': tipo,
                        'severity': severidade,
                        'action': 'REVIEW_AND_CORRECT'
                    })
        
        return {'flags': flags}
    
    def _check_temporal_consistency(self, generated_text: str, original_facts: Dict) -> List[Dict]:
        """Verifica consistência temporal"""
        flags = []
        
        timeline_original = original_facts.get('timeline_especificada', {})
        
        # Buscar menções temporais no texto gerado
        time_mentions = re.findall(r'(?:há|fazem?)\s+(\d+\s*(?:anos?|meses?|semanas?|dias?))', generated_text, re.IGNORECASE)
        
        for mention in time_mentions:
            # Verificar se essa informação temporal foi realmente fornecida
            found_in_original = False
            for time_info in timeline_original.values():
                if mention.lower() in time_info.get('periodo', '').lower():
                    found_in_original = True
                    break
            
            if not found_in_original:
                flags.append({
                    'type': 'temporal_hallucination',
                    'invented_timeframe': mention,
                    'severity': 'MEDIUM',
                    'action': 'REPLACE_WITH_NAO_ESPECIFICADO'
                })
        
        return flags
    
    def _generate_corrections(self, flags: List[Dict], generated_text: str) -> Dict:
        """Gera correções específicas para os problemas detectados"""
        corrections = {
            'corrected_text': generated_text,
            'modifications_made': [],
            'safety_improvements': []
        }
        
        corrected_text = generated_text
        
        for flag in flags:
            if flag['type'] == 'medical_term_hallucination':
                # Remover termo médico inventado
                term = flag['invented_term']
                corrected_text = re.sub(
                    rf'\b{re.escape(term)}\b', 
                    '[Não relatado na consulta]', 
                    corrected_text, 
                    flags=re.IGNORECASE
                )
                corrections['modifications_made'].append(f"Removido termo médico não mencionado: {term}")
            
            elif flag['type'] == 'personal_data_hallucination':
                # Substituir dado pessoal inventado
                value = flag['invented_value']
                corrected_text = corrected_text.replace(value, '[Não informado]')
                corrections['modifications_made'].append(f"Substituído dado não fornecido: {value}")
            
            elif flag['type'] == 'temporal_hallucination':
                # Substituir informação temporal inventada
                timeframe = flag['invented_timeframe']
                corrected_text = corrected_text.replace(timeframe, '[Tempo não especificado]')
                corrections['modifications_made'].append(f"Corrigida informação temporal: {timeframe}")
        
        corrections['corrected_text'] = corrected_text
        corrections['safety_improvements'] = [
            "Removidas informações não fornecidas pelo paciente",
            "Substituídos termos médicos não mencionados",
            "Corrigidas inconsistências temporais"
        ]
        
        return corrections

# Instância global
output_validator = OutputValidatorService()