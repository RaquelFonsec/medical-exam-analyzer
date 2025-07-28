"""
Utilitários de Validação para o Sistema Médico
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from ..models.pydantic_models import CompleteMedicalRecord, BenefitType, Specialty

class MedicalDataValidator:
    """Validador principal para dados médicos"""
    
    # Padrões de validação
    CPF_PATTERN = re.compile(r'^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{11}$')
    RG_PATTERN = re.compile(r'^[\dX]{1,2}\.?\d{3}\.?\d{3}-?[\dX]$', re.IGNORECASE)
    CID_PATTERN = re.compile(r'^[A-Z]\d{2}(\.\d)?$')
    PHONE_PATTERN = re.compile(r'^\(?(\d{2})\)?\s?9?\d{4}-?\d{4}$')
    
    # CIDs de doenças graves para isenção IR
    SERIOUS_DISEASE_CIDS = {
        'C00-C97': 'Neoplasias (tumores)',
        'E10-E14': 'Diabetes mellitus',
        'G20': 'Doença de Parkinson',
        'G35': 'Esclerose múltipla',
        'I21-I22': 'Infarto agudo do miocárdio',
        'M05-M06': 'Artrite reumatoide',
        'N18': 'Doença renal crônica',
        'F20-F29': 'Esquizofrenia'
    }
    
    @staticmethod
    def validate_medical_analysis_result(result: Dict[str, Any]) -> Dict[str, Any]:
        """Valida resultado completo da análise médica"""
        
        validation_errors = []
        validation_warnings = []
        
        # Validações obrigatórias
        required_fields = ['status', 'beneficio_classificado', 'laudo_medico']
        for field in required_fields:
            if field not in result:
                validation_errors.append(f"Campo obrigatório ausente: {field}")
        
        # Validação do status
        if result.get('status') not in ['success', 'error']:
            validation_errors.append("Status deve ser 'success' ou 'error'")
        
        # Validação do benefício
        valid_benefits = [
            "AUXÍLIO-DOENÇA", "APOSENTADORIA POR INVALIDEZ", 
            "BPC/LOAS", "AUXÍLIO-ACIDENTE", "ISENÇÃO IMPOSTO DE RENDA",
            "MAJORAÇÃO 25%", "NÃO_CLASSIFICADO", "ERRO_PROCESSAMENTO"
        ]
        
        if result.get('beneficio_classificado') not in valid_benefits:
            validation_errors.append(f"Benefício classificado inválido: {result.get('beneficio_classificado')}")
        
        # Validação da especialidade
        if not result.get('analise_medica', {}).get('especialidade_principal'):
            validation_warnings.append("Especialidade médica não identificada")
        
        # Validação do CID
        cid_principal = result.get('analise_medica', {}).get('cid_principal', '')
        if cid_principal and not MedicalDataValidator.validate_cid_format(cid_principal):
            validation_warnings.append(f"Formato de CID inválido: {cid_principal}")
        
        # Validação da idade do paciente
        idade = result.get('paciente', {}).get('idade_anos')
        if idade is not None:
            age_validation = MedicalDataValidator.validate_patient_age(idade, result.get('beneficio_classificado'))
            if not age_validation['valid']:
                validation_warnings.extend(age_validation['warnings'])
        
        # Validação do laudo médico
        laudo = result.get('laudo_medico', '')
        if laudo:
            laudo_validation = MedicalDataValidator.validate_medical_report(laudo)
            validation_warnings.extend(laudo_validation['warnings'])
        
        # Validação de consistência entre benefício e nexo ocupacional
        nexo_validation = MedicalDataValidator.validate_occupational_nexus_consistency(result)
        validation_warnings.extend(nexo_validation['warnings'])
        
        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": validation_warnings,
            "score": MedicalDataValidator._calculate_quality_score(result, validation_errors, validation_warnings)
        }
    
    @staticmethod
    def validate_patient_data(patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida dados específicos do paciente"""
        
        validation_errors = []
        warnings = []
        
        # Validar idade
        idade = patient_data.get('idade')
        if idade is not None:
            if not isinstance(idade, int) or idade < 0 or idade > 120:
                validation_errors.append("Idade deve ser um número entre 0 e 120 anos")
            elif idade < 16:
                warnings.append("Paciente menor de 16 anos - considerar BPC/LOAS")
            elif idade >= 65:
                warnings.append("Paciente idoso - pode ter direito a BPC por idade")
        
        # Validar sexo
        sexo = patient_data.get('sexo', '').upper()
        if sexo and sexo not in ['M', 'F', 'MASCULINO', 'FEMININO']:
            warnings.append("Sexo não especificado corretamente")
        
        # Validar profissão
        profissao = patient_data.get('profissao', '').lower()
        if not profissao or profissao in ['não informada', 'não informado', '']:
            warnings.append("Profissão não informada - pode afetar classificação do benefício")
        
        # Validar documentos
        cpf = patient_data.get('documento_cpf')
        if cpf and not MedicalDataValidator.validate_cpf_format(cpf):
            validation_errors.append("Formato de CPF inválido")
        
        rg = patient_data.get('documento_rg')
        if rg and not MedicalDataValidator.validate_rg_format(rg):
            validation_errors.append("Formato de RG inválido")
        
        return {
            "valid": len(validation_errors) == 0,
            "errors": validation_errors,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_cid_format(cid: str) -> bool:
        """Valida formato do CID-10"""
        if not cid:
            return False
        return bool(MedicalDataValidator.CID_PATTERN.match(cid.upper()))
    
    @staticmethod
    def validate_cpf_format(cpf: str) -> bool:
        """Valida formato do CPF"""
        if not cpf:
            return False
        return bool(MedicalDataValidator.CPF_PATTERN.match(cpf))
    
    @staticmethod
    def validate_rg_format(rg: str) -> bool:
        """Valida formato do RG"""
        if not rg:
            return False
        return bool(MedicalDataValidator.RG_PATTERN.match(rg))
    
    @staticmethod
    def validate_patient_age(idade: int, beneficio_tipo: str) -> Dict[str, Any]:
        """Valida consistência entre idade e tipo de benefício"""
        
        warnings = []
        
        if idade < 16:
            if beneficio_tipo not in ["BPC/LOAS", "NÃO_CLASSIFICADO"]:
                warnings.append(f"Menor de 16 anos não pode receber {beneficio_tipo} - deve ser BPC/LOAS")
        
        if idade >= 65:
            if beneficio_tipo == "AUXÍLIO-DOENÇA":
                warnings.append("Paciente com 65+ anos - considerar aposentadoria por idade ao invés de auxílio-doença")
        
        return {
            "valid": len(warnings) == 0,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_medical_report(laudo: str) -> Dict[str, Any]:
        """Valida estrutura e conteúdo do laudo médico"""
        
        warnings = []
        
        if not laudo or len(laudo.strip()) < 50:
            warnings.append("Laudo médico muito curto ou vazio")
            return {"warnings": warnings}
        
        # Verificar seções obrigatórias
        required_sections = [
            "HISTÓRIA CLÍNICA",
            "LIMITAÇÃO FUNCIONAL", 
            "TRATAMENTO",
            "PROGNÓSTICO",
            "CONCLUSÃO",
            "CID-10"
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in laudo.upper():
                missing_sections.append(section)
        
        if missing_sections:
            warnings.append(f"Seções ausentes no laudo: {', '.join(missing_sections)}")
        
        # Verificar se tem CID mencionado
        cid_matches = re.findall(r'[A-Z]\d{2}(?:\.\d)?', laudo)
        if not cid_matches:
            warnings.append("Nenhum CID identificado no laudo")
        
        # Verificar tamanho adequado
        if len(laudo) > 5000:
            warnings.append("Laudo muito extenso - considerar resumir")
        
        return {"warnings": warnings}
    
    @staticmethod
    def validate_occupational_nexus_consistency(result: Dict[str, Any]) -> Dict[str, Any]:
        """Valida consistência do nexo ocupacional"""
        
        warnings = []
        
        nexo_info = result.get('nexo_ocupacional', {})
        beneficio = result.get('beneficio_classificado')
        profissao = result.get('paciente', {}).get('profissao', '').lower()
        
        # Se é auxílio-acidente mas não tem nexo ocupacional
        if beneficio == "AUXÍLIO-ACIDENTE" and not nexo_info.get('identificado'):
            warnings.append("Auxílio-acidente requer nexo ocupacional, mas não foi identificado")
        
        # Se tem profissão mas recebe BPC
        if (profissao and profissao not in ['não informada', 'desempregado', 'aposentado'] 
            and beneficio == "BPC/LOAS"):
            warnings.append("Trabalhador ativo não deveria receber BPC/LOAS")
        
        # Verificar limitação sobre telemedicina
        if nexo_info.get('observacao') and 'telemedicina' in nexo_info['observacao'].lower():
            if beneficio in ["AUXÍLIO-ACIDENTE"]:
                warnings.append("Benefício com nexo ocupacional não pode ser concedido por telemedicina")
        
        return {"warnings": warnings}
    
    @staticmethod
    def validate_benefit_eligibility(patient_data: Dict[str, Any], medical_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida elegibilidade para diferentes tipos de benefício"""
        
        recommendations = []
        warnings = []
        
        idade = patient_data.get('idade')
        profissao = patient_data.get('profissao', '').lower()
        cid_principal = medical_data.get('cid_principal', '')
        
        # Validações por idade
        if idade is not None:
            if idade < 16:
                recommendations.append("BPC/LOAS - Menor de 16 anos")
            elif idade >= 65:
                recommendations.append("BPC/LOAS por idade ou Aposentadoria por idade")
        
        # Validações por CID (doenças graves)
        if MedicalDataValidator._is_serious_disease(cid_principal):
            recommendations.append("ISENÇÃO IMPOSTO DE RENDA - Doença grave")
            recommendations.append("Possível APOSENTADORIA POR INVALIDEZ")
        
        # Validações por situação trabalhista
        if profissao in ['não informada', 'desempregado', 'nunca trabalhou']:
            recommendations.append("BPC/LOAS - Sem vínculo trabalhista")
        elif profissao not in ['aposentado']:
            recommendations.append("AUXÍLIO-DOENÇA ou APOSENTADORIA POR INVALIDEZ - Com vínculo")
        
        return {
            "recommendations": recommendations,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_documentation_completeness(docs_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida completude da documentação médica"""
        
        warnings = []
        missing_docs = []
        
        # Documentos essenciais
        essential_docs = [
            "exames_complementares",
            "relatorios_medicos", 
            "cids_mencionados"
        ]
        
        for doc_type in essential_docs:
            if not docs_data.get(doc_type) or len(docs_data[doc_type]) == 0:
                missing_docs.append(doc_type.replace('_', ' ').title())
        
        if missing_docs:
            warnings.append(f"Documentação incompleta: {', '.join(missing_docs)}")
        
        # Verificar se documentação é suficiente
        if not docs_data.get('documentos_suficientes', False):
            warnings.append("Documentação insuficiente para análise completa")
        
        return {
            "complete": len(missing_docs) == 0,
            "missing_documents": missing_docs,
            "warnings": warnings
        }
    
    @staticmethod
    def _is_serious_disease(cid: str) -> bool:
        """Verifica se o CID corresponde a uma doença grave"""
        if not cid:
            return False
        
        cid_upper = cid.upper()
        
        # Verificar CIDs específicos
        for cid_range, _ in MedicalDataValidator.SERIOUS_DISEASE_CIDS.items():
            if '-' in cid_range:
                start, end = cid_range.split('-')
                if start <= cid_upper <= end:
                    return True
            else:
                if cid_upper.startswith(cid_range):
                    return True
        
        return False
    
    @staticmethod
    def _calculate_quality_score(result: Dict[str, Any], errors: List[str], warnings: List[str]) -> float:
        """Calcula score de qualidade da análise (0-100)"""
        
        base_score = 100.0
        
        # Penalizar erros críticos
        base_score -= len(errors) * 20
        
        # Penalizar warnings
        base_score -= len(warnings) * 5
        
        # Bonificar completude dos dados
        paciente = result.get('paciente', {})
        if paciente.get('idade_anos'):
            base_score += 5
        if paciente.get('profissao') and paciente['profissao'] != 'não informada':
            base_score += 5
        
        # Bonificar presença de CID
        if result.get('analise_medica', {}).get('cid_principal'):
            base_score += 10
        
        # Bonificar laudo completo
        laudo = result.get('laudo_medico', '')
        if laudo and len(laudo) > 200:
            base_score += 10
        
        return max(0.0, min(100.0, base_score))

class BenefitValidator:
    """Validador específico para regras de benefícios previdenciários"""
    
    # Regras de benefícios
    BENEFIT_RULES = {
        "BPC/LOAS": {
            "min_age": None, 
            "max_age": None,
            "requires_contribution": False,
            "allows_work": False,
            "income_limit": True
        },
        "AUXÍLIO-DOENÇA": {
            "min_age": 16,
            "max_age": None, 
            "requires_contribution": True,
            "allows_work": False,
            "temporary": True
        },
        "APOSENTADORIA POR INVALIDEZ": {
            "min_age": 16,
            "max_age": None,
            "requires_contribution": True, 
            "allows_work": False,
            "permanent": True
        },
        "AUXÍLIO-ACIDENTE": {
            "min_age": 16,
            "max_age": None,
            "requires_contribution": True,
            "allows_work": True,
            "requires_nexus": True
        }
    }
    
    @staticmethod
    def validate_benefit_classification(patient_data: Dict[str, Any], 
                                      medical_data: Dict[str, Any],
                                      classified_benefit: str) -> Dict[str, Any]:
        """Valida se a classificação do benefício está correta"""
        
        errors = []
        warnings = []
        suggestions = []
        
        idade = patient_data.get('idade')
        profissao = patient_data.get('profissao', '').lower()
        nexo_ocupacional = medical_data.get('nexo_ocupacional', False)
        
        if classified_benefit not in BenefitValidator.BENEFIT_RULES:
            return {"valid": True, "errors": [], "warnings": [], "suggestions": []}
        
        rules = BenefitValidator.BENEFIT_RULES[classified_benefit]
        
        # Validar idade mínima
        if rules.get("min_age") and idade and idade < rules["min_age"]:
            errors.append(f"{classified_benefit} requer idade mínima de {rules['min_age']} anos")
        
        # Validar contribuição
        if rules.get("requires_contribution") and profissao in ['não informada', 'nunca trabalhou']:
            warnings.append(f"{classified_benefit} requer histórico contributivo")
        
        # Validar nexo ocupacional
        if rules.get("requires_nexus") and not nexo_ocupacional:
            errors.append(f"{classified_benefit} requer nexo ocupacional estabelecido")
        
        # Sugestões baseadas no perfil
        if idade and idade < 16:
            suggestions.append("Considerar BPC/LOAS para menor de 16 anos")
        
        if profissao in ['não informada', 'desempregado'] and classified_benefit != "BPC/LOAS":
            suggestions.append("Sem vínculo trabalhista - considerar BPC/LOAS")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings, 
            "suggestions": suggestions
        }

# Funções de conveniência para validação rápida
def validate_medical_analysis_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Função de conveniência para validação completa"""
    return MedicalDataValidator.validate_medical_analysis_result(result)

def validate_patient_data(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """Função de conveniência para validação de dados do paciente"""
    return MedicalDataValidator.validate_patient_data(patient_data)

def validate_cid_format(cid: str) -> bool:
    """Função de conveniência para validação de CID"""
    return MedicalDataValidator.validate_cid_format(cid)

def calculate_analysis_quality_score(result: Dict[str, Any]) -> float:
    """Calcula score de qualidade da análise"""
    validation = validate_medical_analysis_result(result)
    return validation.get('score', 0.0)