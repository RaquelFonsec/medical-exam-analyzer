import re
from typing import Dict, List, Any
from datetime import datetime

class FactExtractorService:
    """Extração de fatos MAIS SENSÍVEL para gerar conteúdo detalhado"""
    
    def __init__(self):
        print("🔍 Inicializando FactExtractorService - Versão SENSÍVEL")
        self.medical_patterns = self._load_medical_extraction_patterns()
        
    def _load_medical_extraction_patterns(self):
        """Padrões médicos MAIS ABRANGENTES"""
        return {
            'dados_pessoais_exatos': {
                'nome_completo': [
                    r'(?:meu nome é|me chamo|sou|eu sou)\s+([A-ZÀ-Ÿa-zà-ÿ\s]+)',
                    r'(?:nome|paciente)[\s:]*([A-ZÀ-Ÿa-zà-ÿ\s]+)'
                ],
                'idade_exata': [
                    r'(?:tenho|idade|com)\s*(\d{1,3})\s*anos?',
                    r'(\d{1,3})\s*anos?\s*(?:de idade|anos)'
                ],
                'profissao_exata': [
                    r'(?:trabalho|trabalhar|sou|profiss[ãa]o|atuo)(?:\s+como|\s+de|\s+é)?\s+([\w\s]+?)(?:\s+(?:há|por|faz|desde)|[.,]|$)',
                    r'(?:com|na)\s+(TI|tecnologia|informática|computador|sistema)',
                    r'(pedreiro|auxiliar|operador|secretária|enfermeira|professor|vendedor|técnico|analista)'
                ]
            },
            
            'sintomas_explicitos': {
                'dor_especifica': [
                    r'(?:sinto|tenho|dor|dói|doendo|dores?)[\s\w]*?(?:no|na|nos|nas)\s+([\w\s]+?)(?:\s|,|\.)',
                    r'(dor[\s\w]*?)(?:\s|,|\.)',
                    r'(enxaqueca|cefaleia|dor de cabeça)'
                ],
                'sintomas_neurologicos': [
                    r'(formigamento|dormência|fraqueza|paralisia|tontura|vertigem)',
                    r'(?:sinto|tenho|apresento)\s+([\w\s]+?)(?:\s|,|\.)',
                    r'(perda\s+de\s+[\w\s]+)'
                ],
                'limitacoes_funcionais': [
                    r'(não consigo[\s\w]*?)(?:\s|,|\.)',
                    r'(dificuldade para[\s\w]*?)(?:\s|,|\.)',
                    r'(impossível[\s\w]*?)(?:\s|,|\.)',
                    r'(preciso de ajuda[\s\w]*?)(?:\s|,|\.)',
                    r'(não\s+(?:posso|consigo)[\s\w]*?)(?:\s|,|\.)'
                ]
            },
            
            'timeline_exata': {
                'inicio_sintomas': [
                    r'(?:há|fazem?|desde)\s*(\d+\s*(?:anos?|meses?|semanas?|dias?))',
                    r'(?:começou|iniciou|surgiu)(?:\s+há)?\s*(\d+\s*(?:anos?|meses?))',
                    r'(\d+\s*(?:anos?|meses?|semanas?|dias?))\s*(?:atrás|que)'
                ],
                'data_evento': [
                    r'(?:em|foi em|desde)\s+(\w+\s+de\s+\d{4})',
                    r'(\d{1,2}\/\d{1,2}\/\d{4})'
                ]
            },
            
            'tratamentos_mencionados': {
                'medicamentos': [
                    r'(?:tomo|uso|faço uso de|medicamento|remédio)\s*([\w\s]+?)(?:\s|,|\.)',
                    r'(analgésico|anti-inflamatório|antibiótico)'
                ],
                'procedimentos': [
                    r'(fisioterapia|cirurgia|operação|procedimento|tratamento|terapia)',
                    r'(?:fiz|faço|fazia)\s+([\w\s]+?)(?:\s|,|\.)'
                ]
            }
        }
    
    def extract_explicit_facts_only(self, transcription: str, patient_info: str) -> Dict[str, Any]:
        """Extrai fatos com MAIS SENSIBILIDADE"""
        
        combined_text = f"{patient_info} {transcription}"
        
        extracted_facts = {
            'dados_pessoais_confirmados': {},
            'sintomas_textualmente_relatados': [],
            'limitacoes_explicitamente_mencionadas': [],
            'timeline_especificada': {},
            'tratamentos_citados': [],
            'informacoes_ausentes': [],
            'texto_original_completo': combined_text,
            'confiabilidade_extracao': 'ALTA'
        }
        
        # 1. DADOS PESSOAIS - MAIS SENSÍVEL
        for field, patterns in self.medical_patterns['dados_pessoais_exatos'].items():
            for pattern in patterns:
                matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                for match in matches:
                    if field not in extracted_facts['dados_pessoais_confirmados']:
                        valor = match.group(1).strip()
                        # Limpar capturas muito genéricas
                        if len(valor) > 2 and valor.lower() not in ['com', 'por', 'que', 'para']:
                            extracted_facts['dados_pessoais_confirmados'][field] = {
                                'valor': valor,
                                'frase_original': match.group(0),
                                'posicao_texto': match.start()
                            }
                        break
        
        # 2. SINTOMAS - MAIS ABRANGENTE
        for category, patterns in self.medical_patterns['sintomas_explicitos'].items():
            for pattern in patterns:
                matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                for match in matches:
                    sintoma_texto = match.group(1) if match.lastindex else match.group(0)
                    if len(sintoma_texto.strip()) > 2:
                        extracted_facts['sintomas_textualmente_relatados'].append({
                            'categoria': category,
                            'sintoma_exato': sintoma_texto.strip(),
                            'frase_completa_original': match.group(0),
                            'posicao_no_texto': match.start(),
                            'contexto_ao_redor': self._get_context_window(combined_text, match.start(), match.end())
                        })
        
        # 3. TIMELINE - MAIS FLEXÍVEL
        for time_type, patterns in self.medical_patterns['timeline_exata'].items():
            for pattern in patterns:
                match = re.search(pattern, combined_text, re.IGNORECASE)
                if match:
                    extracted_facts['timeline_especificada'][time_type] = {
                        'periodo': match.group(1),
                        'frase_original': match.group(0)
                    }
                    break
        
        # 4. TRATAMENTOS
        for treatment_type, patterns in self.medical_patterns['tratamentos_mencionados'].items():
            for pattern in patterns:
                matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                for match in matches:
                    tratamento_texto = match.group(1) if match.lastindex else match.group(0)
                    if len(tratamento_texto.strip()) > 2:
                        extracted_facts['tratamentos_citados'].append({
                            'tipo': treatment_type,
                            'tratamento': tratamento_texto.strip(),
                            'frase_original': match.group(0)
                        })
        
        # 5. CALCULAR COMPLETUDE - MAIS GENEROSO
        extracted_facts['completude_dados'] = self._calculate_data_completeness_generous(extracted_facts)
        
        # 6. IDENTIFICAR INFORMAÇÕES AUSENTES
        extracted_facts['informacoes_ausentes'] = self._identify_missing_critical_info(extracted_facts)
        
        return extracted_facts
    
    def _get_context_window(self, text: str, start: int, end: int, window: int = 30) -> str:
        """Obtém contexto ao redor do match"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()
    
    def _calculate_data_completeness_generous(self, facts: Dict) -> Dict[str, Any]:
        """Calcula completude de forma MAIS GENEROSA"""
        
        score = 0.0
        
        # Dados pessoais (peso 30%)
        if facts['dados_pessoais_confirmados']:
            personal_score = len(facts['dados_pessoais_confirmados']) / 3  # máximo 3 campos
            score += min(0.3, personal_score * 0.3)
        
        # Sintomas (peso 40%)
        if facts['sintomas_textualmente_relatados']:
            symptom_score = min(1.0, len(facts['sintomas_textualmente_relatados']) / 2)
            score += symptom_score * 0.4
        
        # Timeline (peso 20%)
        if facts['timeline_especificada']:
            score += 0.2
        
        # Tratamentos (peso 10%)
        if facts['tratamentos_citados']:
            score += 0.1
        
        # Determinar nível MAIS GENEROSO
        if score >= 0.5:  # Reduzido de 0.8
            level = 'ALTA'
        elif score >= 0.3:  # Reduzido de 0.6
            level = 'MEDIA'
        else:
            level = 'BAIXA'
        
        return {
            'score': score,
            'level': level,
            'pode_usar_ia': score >= 0.3,  # Reduzido de 0.6
            'campos_identificados': {
                'dados_pessoais': len(facts['dados_pessoais_confirmados']),
                'sintomas': len(facts['sintomas_textualmente_relatados']),
                'timeline': len(facts['timeline_especificada']),
                'tratamentos': len(facts['tratamentos_citados'])
            }
        }
    
    def _identify_missing_critical_info(self, facts: Dict) -> List[str]:
        """Identifica informações ausentes"""
        missing = []
        
        if not facts['dados_pessoais_confirmados'].get('nome_exato'):
            missing.append('nome_nao_especificado')
        if not facts['dados_pessoais_confirmados'].get('idade_exata'):
            missing.append('idade_nao_especificado')
        if not facts['dados_pessoais_confirmados'].get('profissao_exata'):
            missing.append('profissao_nao_especificado')
        if not facts['sintomas_textualmente_relatados']:
            missing.append('sintomas_nao_relatados')
        if not facts['timeline_especificada']:
            missing.append('timeline_nao_especificado')
        
        return missing

# Instância global
fact_extractor = FactExtractorService()
