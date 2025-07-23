from typing import Dict, List, Any
import re

class MedicalNERService:
    def __init__(self):
        print("🧠 Inicializando MedicalNERService LITE (sem BERT)...")
        # SEM BioBERT pesado - só regex
        self.medical_patterns = self._load_medical_patterns()
        print("✅ MedicalNERService LITE inicializado")
        
    def setup_models(self):
        """Versão lite - sem modelos pesados"""
        print("⚡ Modo LITE: usando apenas extração baseada em regras")
        self.nlp = None
        self.bio_ner = None
            
    def _load_medical_patterns(self):
        """Carrega padrões médicos para extração"""
        return {
            'symptom_keywords': [
                'dor', 'tontura', 'fraqueza', 'formigamento', 'dormência',
                'cansaço', 'falta de ar', 'perda de força', 'dificuldade',
                'limitação', 'incapacidade', 'sequela', 'lesão'
            ],
            'limitation_indicators': [
                'não consigo', 'dificuldade para', 'impossível',
                'preciso de ajuda', 'dependo de', 'incapaz de'
            ],
            'professions': [
                'pedreiro', 'auxiliar', 'operador', 'secretária', 'enfermeira',
                'professor', 'vendedor', 'cozinheira', 'faxineira', 'motorista'
            ]
        }
    
    def extract_medical_entities(self, transcription: str) -> Dict[str, Any]:
        """Extração LITE apenas com regex - RÁPIDA"""
        
        # Pré-processamento do texto
        cleaned_text = self._preprocess_text(transcription)
        
        # Extração por regex apenas (RÁPIDO)
        entities = {
            'dados_pessoais': self._extract_personal_data(cleaned_text),
            'sintomas_relatados': self._extract_symptoms_lite(cleaned_text),
            'limitacoes_funcionais': self._extract_functional_limitations_lite(cleaned_text),
            'historico_temporal': self._extract_timeline(cleaned_text),
            'tratamentos_menciona': self._extract_treatments_lite(cleaned_text),
            'atividades_comprometidas': self._extract_affected_activities_lite(cleaned_text),
            'contexto_trabalho': self._extract_work_context_lite(cleaned_text),
            'dependencia_cuidados': self._extract_care_dependency_lite(cleaned_text)
        }
        
        # Score simplificado
        confidence_score = self._calculate_extraction_confidence_lite(entities)
        
        return {
            **entities,
            'confidence_score': confidence_score,
            'extraction_metadata': {
                'original_text_length': len(transcription),
                'mode': 'LITE',
                'validation_passed': confidence_score > 0.5
            }
        }
    
    def _preprocess_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_personal_data(self, text: str) -> Dict[str, str]:
        patterns = {
            'nome_completo': [
                r'meu nome é (\w+(?:\s+\w+)*)',
                r'me chamo (\w+(?:\s+\w+)*)'
            ],
            'idade': [
                r'tenho (\d{1,3})\s*anos?',
                r'(\d{1,3})\s*anos? de idade'
            ],
            'profissao': [
                r'trabalho como (\w+(?:\s+\w+)*)',
                r'sou (\w+(?:\s+\w+)*)'
            ]
        }
        
        extracted = {}
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and field not in extracted:
                    extracted[field] = match.group(1).strip()
                    break
        
        return extracted
    
    def _extract_symptoms_lite(self, text: str) -> List[Dict[str, str]]:
        patterns = [
            r'(?:sinto|tenho) (\w+(?:\s+\w+)*)',
            r'dor (?:no|na) (\w+(?:\s+\w+)*)',
            r'n[ãa]o consigo (\w+(?:\s+\w+)*)'
        ]
        
        symptoms = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                symptoms.append({
                    'sintoma': match.group(1).lower().strip(),
                    'contexto': 'extraído por regex',
                    'posicao_texto': match.start()
                })
        
        return symptoms
    
    def _extract_functional_limitations_lite(self, text: str) -> List[Dict[str, str]]:
        patterns = [
            r'n[ãa]o consigo (\w+(?:\s+\w+)*)',
            r'dificuldade para (\w+(?:\s+\w+)*)',
            r'preciso de ajuda para (\w+(?:\s+\w+)*)'
        ]
        
        limitations = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                limitations.append({
                    'atividade_limitada': match.group(1).strip(),
                    'tipo_limitacao': 'parcial',
                    'contexto': 'extraído por regex'
                })
        
        return limitations
    
    def _extract_timeline(self, text: str) -> Dict[str, str]:
        patterns = {
            'inicio_sintomas': [
                r'há (\d+\s*(?:anos?|meses?))',
                r'fazem? (\d+\s*(?:anos?|meses?))'
            ]
        }
        
        timeline = {}
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    timeline[category] = match.group(1)
                    break
        
        return timeline
    
    def _extract_treatments_lite(self, text: str) -> List[Dict[str, str]]:
        patterns = [
            r'(?:fisioterapia|cirurgia|medicamento)',
            r'tomo (\w+(?:\s+\w+)*)'
        ]
        
        treatments = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                treatments.append({
                    'tratamento': match.group(0),
                    'tipo': 'outros',
                    'contexto': 'regex'
                })
        
        return treatments
    
    def _extract_affected_activities_lite(self, text: str) -> List[str]:
        activities = ['trabalhar', 'caminhar', 'carregar', 'vestir', 'banho']
        found = []
        for activity in activities:
            if activity in text.lower():
                found.append(activity)
        return found
    
    def _extract_work_context_lite(self, text: str) -> Dict[str, Any]:
        work_patterns = {
            'impossibilidade_trabalho': [
                r'n[ãa]o consigo trabalhar',
                r'impossível trabalhar'
            ]
        }
        
        work_context = {}
        for category, pattern_list in work_patterns.items():
            matches = []
            for pattern in pattern_list:
                if re.search(pattern, text, re.IGNORECASE):
                    matches.append(pattern)
            if matches:
                work_context[category] = matches
        
        return work_context
    
    def _extract_care_dependency_lite(self, text: str) -> Dict[str, Any]:
        if re.search(r'preciso de ajuda|cuidador|sozinha?', text, re.IGNORECASE):
            return {'necessita_cuidador': ['detectado por regex']}
        return {}
    
    def _calculate_extraction_confidence_lite(self, entities: Dict[str, Any]) -> float:
        filled_count = sum(1 for v in entities.values() if v)
        return min(1.0, filled_count / 6)

# Instância global
medical_ner = MedicalNERService()
