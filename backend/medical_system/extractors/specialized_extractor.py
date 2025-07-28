"""
Extrator Especializado por Domínio Médico
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from ..models.pydantic_models import Specialty

class SpecializedExtractor:
    """Extrator especializado por área médica"""
    
    def __init__(self, client, rag_service):
        self.client = client
        self.rag_service = rag_service
        
        # Especialidades e seus indicadores
        self.specialty_indicators = {
            Specialty.PSIQUIATRIA: {
                "keywords": ["depressão", "ansiedade", "bipolar", "esquizofrenia", "transtorno", "psiquiátrico", "mental"],
                "treatments": ["antidepressivo", "ansiolítico", "psicoterapia", "psiquiatra"],
                "limitations": ["concentração", "memória", "humor", "relacionamento"]
            },
            Specialty.CARDIOLOGIA: {
                "keywords": ["coração", "cardíaco", "pressão", "infarto", "arritmia", "valvular"],
                "treatments": ["marca-passo", "cateterismo", "cirurgia cardíaca", "cardiologista"],
                "limitations": ["esforço físico", "fadiga", "dispneia"]
            },
            Specialty.NEUROLOGIA: {
                "keywords": ["neurológico", "epilepsia", "avc", "parkinson", "alzheimer", "demência"],
                "treatments": ["neurologista", "anticonvulsivante", "fisioterapia neurológica"],
                "limitations": ["motora", "cognitiva", "fala", "deglutição"]
            },
            Specialty.OFTALMOLOGIA: {
                "keywords": ["visão", "cegueira", "glaucoma", "catarata", "retina", "olho"],
                "treatments": ["oftalmologista", "cirurgia ocular", "óculos"],
                "limitations": ["visual", "leitura", "locomoção"]
            }
        }
    
    def extract_by_specialty(self, text: str) -> Tuple[Specialty, Dict[str, Any]]:
        """Extrai dados baseado na especialidade principal detectada"""
        
        # Detectar especialidade principal
        primary_specialty = self._detect_primary_specialty(text)
        
        # Extrair dados específicos da especialidade
        specialty_data = self._extract_specialty_specific_data(text, primary_specialty)
        
        return primary_specialty, specialty_data
    
    def _detect_primary_specialty(self, text: str) -> Specialty:
        """Detecta especialidade principal baseada no texto"""
        
        text_lower = text.lower()
        specialty_scores = {}
        
        for specialty, indicators in self.specialty_indicators.items():
            score = 0
            
            # Score por keywords
            for keyword in indicators["keywords"]:
                if keyword in text_lower:
                    score += 2
            
            # Score por tratamentos
            for treatment in indicators["treatments"]:
                if treatment in text_lower:
                    score += 3
            
            # Score por limitações
            for limitation in indicators["limitations"]:
                if limitation in text_lower:
                    score += 1
            
            specialty_scores[specialty] = score
        
        # Retornar especialidade com maior score
        if specialty_scores:
            return max(specialty_scores, key=specialty_scores.get)
        
        return Specialty.CLINICA_GERAL
    
    def _extract_specialty_specific_data(self, text: str, specialty: Specialty) -> Dict[str, Any]:
        """Extrai dados específicos da especialidade"""
        
        prompt = f"""
Extraia dados específicos para {specialty.value} do texto médico.

TEXTO: {text}

ESPECIALIDADE: {specialty.value}

Extraia JSON com campos específicos:
{{
    "sintomas_especificos": ["lista de sintomas da especialidade"],
    "tratamentos_especificos": ["medicações e terapias específicas"],
    "limitacoes_funcionais": ["limitações específicas da área"],
    "prognostico_especialidade": "prognóstico específico",
    "necessita_acompanhamento": true/false,
    "cids_sugeridos": ["CIDs relacionados à especialidade"]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"Especialista em {specialty.value}. Extraia dados específicos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=400
            )
            
            result_text = response.choices[0].message.content.strip()
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            try:
                return json.loads(result_text)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ JSON especialidade inválido: {e}")
                return {
                    "sintomas_especificos": ["dor", "limitação"],
                    "tratamentos_especificos": ["medicação", "repouso"],
                    "limitacoes_funcionais": ["mobilidade reduzida"],
                    "prognostico_especialidade": "reservado",
                    "necessita_acompanhamento": True,
                    "cids_sugeridos": ["M54.5"]
                }
                
        except Exception as e:
            logging.error(f"Erro na extração por especialidade: {e}")
            return {}
