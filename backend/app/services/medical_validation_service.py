from typing import Dict, List, Any
import re

class MedicalValidationService:
    def __init__(self):
        print("🔍 Inicializando MedicalValidationService...")
        # Dicionários médicos controlados
        self.valid_symptoms = self._load_symptom_dictionary()
        self.valid_procedures = self._load_procedure_dictionary()
        self.cid10_codes = self._load_cid10_dictionary()
        print("✅ MedicalValidationService inicializado")
    
    def _load_symptom_dictionary(self) -> List[str]:
        """Carrega dicionário de sintomas válidos"""
        return [
            # Sintomas neurológicos
            'dor de cabeça', 'cefaleia', 'enxaqueca', 'tontura', 'vertigem',
            'formigamento', 'dormência', 'fraqueza', 'paralisia', 'tremor',
            
            # Sintomas musculoesqueléticos
            'dor nas costas', 'dor no ombro', 'dor no joelho', 'dor no punho',
            'dor muscular', 'dor articular', 'rigidez', 'limitação de movimento',
            'perda de força', 'inchaço', 'edema',
            
            # Sintomas gerais
            'fadiga', 'cansaço', 'falta de ar', 'dispneia', 'palpitação',
            'insônia', 'perda de apetite', 'náusea', 'vômito', 'febre',
            
            # Sintomas psiquiátricos
            'ansiedade', 'depressão', 'estresse', 'irritabilidade',
            'perda de memória', 'confusão mental', 'dificuldade de concentração'
        ]
    
    def _load_procedure_dictionary(self) -> List[str]:
        """Carrega dicionário de procedimentos válidos"""
        return [
            'fisioterapia', 'terapia ocupacional', 'acupuntura',
            'cirurgia', 'operação', 'procedimento cirúrgico',
            'exame de sangue', 'raio-x', 'ressonância magnética', 'tomografia',
            'ultrassom', 'eletrocardiograma', 'eletroencefalograma',
            'biópsia', 'endoscopia', 'colonoscopia'
        ]
    
    def _load_cid10_dictionary(self) -> Dict[str, str]:
        """Carrega códigos CID-10 básicos"""
        return {
            # Lesões musculoesqueléticas
            'M75': 'Lesões do ombro',
            'M75.1': 'Síndrome do manguito rotador',
            'M54': 'Dorsalgia',
            'M54.5': 'Dor lombar baixa',
            'M17': 'Gonartrose',
            'M23': 'Transtornos internos do joelho',
            
            # Lesões traumáticas
            'S43': 'Luxação e entorse do ombro',
            'S72': 'Fratura do fêmur',
            'S82': 'Fratura da perna',
            'T14': 'Traumatismo de região não especificada',
            
            # Doenças neurológicas
            'I63': 'Infarto cerebral (AVC)',
            'G93.1': 'Lesão cerebral anóxica',
            'G80': 'Paralisia cerebral',
            'F32': 'Episódios depressivos',
            
            # Doenças ocupacionais
            'M65': 'Sinovite e tenossinovite',
            'M70': 'Transtornos dos tecidos moles relacionados com uso',
            'Z57': 'Exposição ocupacional a fatores de risco'
        }
    
    def validate_extracted_data(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida dados extraídos contra dicionários médicos"""
        
        validated_data = {
            'validated_symptoms': self._validate_symptoms(structured_data.get('sintomas_relatados', [])),
            'validated_limitations': self._validate_limitations(structured_data.get('limitacoes_funcionais', [])),
            'validated_personal_data': self._validate_personal_data(structured_data.get('dados_pessoais', {})),
            'confidence_score': self._calculate_confidence(structured_data),
            'missing_critical_info': self._check_missing_info(structured_data),
            'data_quality_flags': self._assess_data_quality(structured_data)
        }
        
        return {**structured_data, **validated_data}
    
    def _validate_symptoms(self, symptoms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valida sintomas contra dicionário médico"""
        valid_symptoms = []
        
        for symptom in symptoms:
            if isinstance(symptom, dict) and 'sintoma' in symptom:
                symptom_text = symptom['sintoma'].lower()
                
                # Verificar se é um sintoma médico válido
                if self._is_valid_medical_symptom(symptom_text):
                    # Adicionar flag de validação
                    validated_symptom = symptom.copy()
                    validated_symptom['validated'] = True
                    validated_symptom['confidence'] = self._calculate_symptom_confidence(symptom_text)
                    valid_symptoms.append(validated_symptom)
                else:
                    # Manter sintoma mas marcar como não validado
                    unvalidated_symptom = symptom.copy()
                    unvalidated_symptom['validated'] = False
                    unvalidated_symptom['confidence'] = 0.3
                    valid_symptoms.append(unvalidated_symptom)
        
        return valid_symptoms
    
    def _validate_limitations(self, limitations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valida limitações funcionais"""
        valid_limitations = []
        
        functional_activities = [
            'caminhar', 'correr', 'subir escadas', 'carregar peso', 'levantar',
            'agachar', 'vestir', 'tomar banho', 'comer', 'escrever',
            'trabalhar', 'dirigir', 'dormir', 'sentar', 'ficar em pé'
        ]
        
        for limitation in limitations:
            if isinstance(limitation, dict) and 'atividade_limitada' in limitation:
                activity = limitation['atividade_limitada'].lower()
                
                # Verificar se é uma atividade funcional reconhecida
                is_valid = any(act in activity for act in functional_activities)
                
                validated_limitation = limitation.copy()
                validated_limitation['validated'] = is_valid
                validated_limitation['functional_category'] = self._categorize_limitation(activity)
                valid_limitations.append(validated_limitation)
        
        return valid_limitations
    
    def _validate_personal_data(self, personal_data: Dict[str, str]) -> Dict[str, Any]:
        """Valida dados pessoais"""
        validated = personal_data.copy()
        validation_flags = {}
        
        # Validar idade
        if 'idade' in validated:
            age = validated['idade']
            if age and age.isdigit():
                age_int = int(age)
                if 0 <= age_int <= 120:
                    validation_flags['idade_valid'] = True
                else:
                    validation_flags['idade_valid'] = False
                    validation_flags['idade_error'] = 'Idade fora do intervalo válido'
            else:
                validation_flags['idade_valid'] = False
                validation_flags['idade_error'] = 'Formato de idade inválido'
        
        # Validar profissão
        if 'profissao' in validated:
            profession = validated['profissao'].lower()
            known_professions = [
                'pedreiro', 'auxiliar', 'operador', 'secretária', 'enfermeira',
                'professor', 'vendedor', 'cozinheira', 'faxineira', 'motorista',
                'técnico', 'operário', 'servente', 'soldador', 'pintor'
            ]
            
            is_known = any(prof in profession for prof in known_professions)
            validation_flags['profissao_recognized'] = is_known
        
        # Validar nome
        if 'nome_completo' in validated:
            name = validated['nome_completo']
            if name and len(name.split()) >= 2:
                validation_flags['nome_complete'] = True
            else:
                validation_flags['nome_complete'] = False
        
        validated['validation_flags'] = validation_flags
        return validated
    
    def _is_valid_medical_symptom(self, symptom_text: str) -> bool:
        """Verifica se o sintoma é médicamente válido"""
        # Verificar contra dicionário de sintomas
        for valid_symptom in self.valid_symptoms:
            if valid_symptom.lower() in symptom_text or symptom_text in valid_symptom.lower():
                return True
        
        # Verificar padrões de sintomas médicos
        medical_patterns = [
            r'dor.*(?:cabeça|ombro|joelho|costas|punho|pescoço)',
            r'(?:perda|falta).*(?:força|movimento|sensibilidade)',
            r'(?:dificuldade|problema).*(?:respirar|engolir|falar)',
            r'(?:formigamento|dormência|fraqueza)',
            r'(?:tontura|vertigem|náusea|vômito)'
        ]
        
        return any(re.search(pattern, symptom_text, re.IGNORECASE) for pattern in medical_patterns)
    
    def _calculate_symptom_confidence(self, symptom_text: str) -> float:
        """Calcula confiança de um sintoma específico"""
        # Sintomas com termos médicos específicos têm maior confiança
        if any(term in symptom_text for term in ['dor', 'fraqueza', 'formigamento', 'dormência']):
            return 0.9
        elif any(term in symptom_text for term in ['dificuldade', 'problema', 'limitação']):
            return 0.7
        else:
            return 0.5
    
    def _categorize_limitation(self, activity: str) -> str:
        """Categoriza limitação funcional"""
        if any(term in activity for term in ['trabalho', 'trabalhar', 'função']):
            return 'laboral'
        elif any(term in activity for term in ['vestir', 'banho', 'comer', 'higiene']):
            return 'atividades_basicas_vida_diaria'
        elif any(term in activity for term in ['caminhar', 'subir', 'carregar', 'levantar']):
            return 'mobilidade_fisica'
        elif any(term in activity for term in ['dirigir', 'compras', 'telefone']):
            return 'atividades_instrumentais'
        else:
            return 'outras'
    
    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """Calcula score de confiança dos dados extraídos"""
        critical_fields = ['dados_pessoais', 'sintomas_relatados', 'limitacoes_funcionais']
        
        filled_critical = 0
        total_score = 0
        
        for field in critical_fields:
            if field in data and data[field]:
                if isinstance(data[field], (list, dict)) and len(data[field]) > 0:
                    filled_critical += 1
                    # Bonus por qualidade dos dados
                    if field == 'sintomas_relatados':
                        valid_symptoms = sum(1 for s in data[field] 
                                           if isinstance(s, dict) and self._is_valid_medical_symptom(s.get('sintoma', '')))
                        total_score += valid_symptoms / max(len(data[field]), 1) * 0.4
                    else:
                        total_score += 0.3
        
        base_score = filled_critical / len(critical_fields) * 0.6
        return min(1.0, base_score + total_score)
    
    def _check_missing_info(self, data: Dict[str, Any]) -> List[str]:
        """Verifica informações críticas ausentes"""
        missing = []
        
        # Verificar dados pessoais essenciais
        personal_data = data.get('dados_pessoais', {})
        if not personal_data.get('idade'):
            missing.append('idade')
        if not personal_data.get('profissao'):
            missing.append('profissao')
        
        # Verificar sintomas
        if not data.get('sintomas_relatados'):
            missing.append('sintomas')
        
        # Verificar limitações
        if not data.get('limitacoes_funcionais'):
            missing.append('limitacoes_funcionais')
        
        # Verificar timeline
        if not data.get('historico_temporal'):
            missing.append('historico_temporal')
        
        return missing
    
    def _assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Avalia qualidade geral dos dados"""
        quality_flags = {
            'has_timeline': bool(data.get('historico_temporal')),
            'has_treatment_info': bool(data.get('tratamentos_menciona')),
            'has_work_context': bool(data.get('contexto_trabalho')),
            'has_care_dependency': bool(data.get('dependencia_cuidados')),
            'sufficient_symptoms': len(data.get('sintomas_relatados', [])) >= 2,
            'sufficient_limitations': len(data.get('limitacoes_funcionais', [])) >= 1
        }
        
        # Calcular score de qualidade geral
        quality_score = sum(quality_flags.values()) / len(quality_flags)
        quality_flags['overall_quality_score'] = quality_score
        
        # Classificar qualidade
        if quality_score >= 0.8:
            quality_flags['quality_level'] = 'alta'
        elif quality_score >= 0.6:
            quality_flags['quality_level'] = 'media'
        else:
            quality_flags['quality_level'] = 'baixa'
        
        return quality_flags

# Instância global
medical_validator = MedicalValidationService()
