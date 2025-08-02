
"""
Serviço de Análise Médica Inteligente
Integra com os serviços existentes do sistema
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Importar serviços existentes
try:
    from .exam_processor import ExamProcessor
    from .aws_textract_service import AWSTextractService
    from .pydantic_ai_medical_service import PydanticAIMedicalService
    SERVICES_AVAILABLE = True
except ImportError as e:
    SERVICES_AVAILABLE = False
    logging.warning(f"Serviços não encontrados: {e}")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalAIService:
    """
    Serviço de IA médica que integra todos os componentes existentes
    """
    
    def __init__(self):
        self.services_available = SERVICES_AVAILABLE
        self.openai_available = self._check_openai()
        
        # Inicializar serviços se disponíveis
        if self.services_available:
            try:
                self.exam_processor = ExamProcessor()
                self.textract_service = AWSTextractService()
                self.pydantic_ai = PydanticAIMedicalService()
                logger.info("✅ Todos os serviços carregados com sucesso")
            except Exception as e:
                logger.error(f"Erro inicializando serviços: {e}")
                self.services_available = False
        
        self.medical_patterns = self._load_medical_patterns()
        logger.info(f"MedicalAIService iniciado - Serviços: {self.services_available}, OpenAI: {self.openai_available}")
    
    def _check_openai(self) -> bool:
        """Verificar se OpenAI está disponível"""
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            return api_key is not None
        except ImportError:
            return False
    
    def _load_medical_patterns(self) -> Dict[str, Any]:
        """Carregar padrões médicos para análise"""
        return {
            'exam_types': {
                'hemograma': ['hemograma', 'hemoglobina', 'hematócrito', 'leucócitos', 'plaquetas'],
                'glicemia': ['glicose', 'glicemia', 'diabetes'],
                'lipidograma': ['colesterol', 'hdl', 'ldl', 'triglicerídeos'],
                'urina': ['urina', 'eas', 'sedimento'],
                'receita': ['receita', 'medicamento', 'prescri']
            },
            'urgency_keywords': [
                'urgente', 'emergência', 'grave', 'crítico', 'imediato'
            ],
            'normal_ranges': {
                'hemoglobina_m': (13.5, 17.5),
                'hemoglobina_f': (12.0, 15.5),
                'glicose': (70, 99),
                'colesterol': (0, 200)
            }
        }
    
    async def analyze_medical_document(self, 
                                     extracted_text: str, 
                                     document_type: str = "auto",
                                     patient_info: Dict = None) -> Dict[str, Any]:
        """
        Análise médica inteligente completa
        """
        logger.info(f"Iniciando análise médica - Tipo: {document_type}")
        
        try:
            # Estrutura de resposta padrão
            result = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'document_type': document_type,
                'ai_service': 'MedicalAI Integrated',
                'analysis': {},
                'confidence': 0.0
            }
            
            # 1. Detectar tipo de documento se auto
            if document_type == "auto":
                document_type = self._detect_document_type(extracted_text)
                result['document_type'] = document_type
            
            # 2. Análise básica (sempre disponível)
            basic_analysis = await self._basic_analysis(extracted_text, document_type)
            result['analysis']['basic'] = basic_analysis
            
            # 3. Análise avançada se serviços disponíveis
            if self.services_available:
                try:
                    advanced_analysis = await self._advanced_analysis(extracted_text, document_type, patient_info)
                    result['analysis']['advanced'] = advanced_analysis
                    result['ai_service'] = 'MedicalAI Advanced'
                except Exception as e:
                    logger.warning(f"Análise avançada falhou: {e}")
                    result['analysis']['advanced'] = {'error': str(e)}
            
            # 4. Análise com IA externa se disponível
            if self.openai_available:
                try:
                    ai_analysis = await self._ai_analysis(extracted_text, document_type)
                    result['analysis']['ai_interpretation'] = ai_analysis
                    result['ai_service'] += ' + OpenAI'
                except Exception as e:
                    logger.warning(f"Análise IA externa falhou: {e}")
            
            # 5. Calcular confiança geral
            result['confidence'] = self._calculate_overall_confidence(result['analysis'])
            
            # 6. Gerar interpretação final
            result['interpretation'] = self._generate_interpretation(result['analysis'], document_type)
            
            # 7. Recomendações
            result['recommendations'] = self._generate_recommendations(result['analysis'], document_type)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro na análise médica: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'ai_service': 'MedicalAI Error Handler'
            }
    
    def _detect_document_type(self, text: str) -> str:
        """Detectar tipo de documento baseado no conteúdo"""
        text_lower = text.lower()
        
        for exam_type, keywords in self.medical_patterns['exam_types'].items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score >= 2:  # Pelo menos 2 palavras-chave
                return exam_type
        
        return 'documento_medico'
    
    async def _basic_analysis(self, text: str, document_type: str) -> Dict[str, Any]:
        """Análise básica sem dependências externas"""
        analysis = {
            'text_length': len(text),
            'word_count': len(text.split()),
            'document_type': document_type,
            'extracted_values': self._extract_numeric_values(text),
            'medical_terms': self._find_medical_terms(text),
            'urgency_indicators': self._check_urgency(text),
            'patient_data': self._extract_basic_patient_data(text)
        }
        
        return analysis
    
    def _extract_numeric_values(self, text: str) -> List[Dict[str, Any]]:
        """Extrair valores numéricos com unidades"""
        import re
        
        # Padrões para valores médicos
        patterns = [
            r'(\w+)[\s:]*(\d+[.,]?\d*)\s*([a-zA-Z/]+)',  # Nome: valor unidade
            r'(\w+)[\s:]*(\d+[.,]?\d*)',                 # Nome: valor
        ]
        
        values = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2 and len(match[0]) >= 3:
                    try:
                        value = float(match[1].replace(',', '.'))
                        unit = match[2] if len(match) > 2 else ''
                        
                        values.append({
                            'parameter': match[0].lower(),
                            'value': value,
                            'unit': unit,
                            'normal_status': self._check_normal_range(match[0].lower(), value)
                        })
                    except ValueError:
                        continue
        
        return values[:10]  # Limitar a 10 valores
    
    def _check_normal_range(self, parameter: str, value: float) -> str:
        """Verificar se valor está dentro do normal"""
        ranges = self.medical_patterns['normal_ranges']
        
        for range_key, (min_val, max_val) in ranges.items():
            if parameter in range_key:
                if value < min_val:
                    return 'baixo'
                elif value > max_val:
                    return 'alto'
                else:
                    return 'normal'
        
        return 'desconhecido'
    
    def _find_medical_terms(self, text: str) -> List[str]:
        """Encontrar termos médicos relevantes"""
        medical_terms = [
            'diagnóstico', 'sintoma', 'tratamento', 'medicamento',
            'exame', 'análise', 'resultado', 'normal', 'alterado',
            'hemoglobina', 'glicose', 'colesterol', 'pressão'
        ]
        
        text_lower = text.lower()
        found_terms = [term for term in medical_terms if term in text_lower]
        
        return found_terms
    
    def _check_urgency(self, text: str) -> Dict[str, Any]:
        """Verificar indicadores de urgência"""
        text_lower = text.lower()
        urgency_found = [keyword for keyword in self.medical_patterns['urgency_keywords'] if keyword in text_lower]
        
        return {
            'has_urgency_indicators': len(urgency_found) > 0,
            'urgency_keywords': urgency_found,
            'urgency_level': 'alta' if len(urgency_found) >= 2 else 'baixa' if len(urgency_found) == 1 else 'normal'
        }
    
    def _extract_basic_patient_data(self, text: str) -> Dict[str, Any]:
        """Extrair dados básicos do paciente"""
        import re
        
        patient_data = {}
        
        # Buscar idade
        idade_match = re.search(r'(\d{1,3})\s*anos?', text, re.IGNORECASE)
        if idade_match:
            patient_data['idade'] = int(idade_match.group(1))
        
        # Buscar sexo
        if any(word in text.lower() for word in ['masculino', 'homem']):
            patient_data['sexo'] = 'masculino'
        elif any(word in text.lower() for word in ['feminino', 'mulher']):
            patient_data['sexo'] = 'feminino'
        
        # Buscar CID
        cid_match = re.search(r'([A-Z]\d{2}(?:\.\d)?)', text)
        if cid_match:
            patient_data['cid'] = cid_match.group(1)
        
        return patient_data
    
    async def _advanced_analysis(self, text: str, document_type: str, patient_info: Dict = None) -> Dict[str, Any]:
        """Análise avançada usando serviços existentes"""
        if not self.services_available:
            return {'error': 'Serviços avançados não disponíveis'}
        
        try:
            # Usar o PydanticAI se disponível
            if hasattr(self, 'pydantic_ai'):
                pydantic_result = await self.pydantic_ai.analyze_medical_document(text, document_type)
                return {
                    'pydantic_ai_analysis': pydantic_result,
                    'service_used': 'PydanticAI'
                }
        except Exception as e:
            logger.warning(f"PydanticAI analysis failed: {e}")
        
        # Análise básica estruturada como fallback
        return {
            'structured_analysis': {
                'document_type': document_type,
                'content_summary': text[:200] + "..." if len(text) > 200 else text,
                'analysis_method': 'basic_structured'
            }
        }
    
    async def _ai_analysis(self, text: str, document_type: str) -> Dict[str, Any]:
        """Análise usando IA externa (OpenAI)"""
        if not self.openai_available:
            return {'error': 'OpenAI não disponível'}
        
        try:
            import openai
            
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            prompt = f"""
Analise este documento médico do tipo {document_type}:

{text[:1000]}...

Forneça uma análise estruturada incluindo:
1. Tipo de documento identificado
2. Principais achados
3. Valores alterados (se houver)
4. Recomendações gerais
5. Nível de urgência (baixo/médio/alto)

Responda em formato JSON.
"""
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content
            
            # Tentar parsear como JSON
            try:
                ai_json = json.loads(ai_response)
                return ai_json
            except json.JSONDecodeError:
                return {
                    'ai_text_response': ai_response,
                    'note': 'Resposta não estruturada'
                }
            
        except Exception as e:
            return {'error': f'Erro na análise IA: {str(e)}'}
    
    def _calculate_overall_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calcular confiança geral da análise"""
        confidence_factors = []
        
        # Fator 1: Análise básica
        basic = analysis.get('basic', {})
        if basic.get('extracted_values'):
            confidence_factors.append(0.8)
        if basic.get('medical_terms'):
            confidence_factors.append(0.7)
        
        # Fator 2: Análise avançada
        advanced = analysis.get('advanced', {})
        if 'error' not in advanced:
            confidence_factors.append(0.9)
        
        # Fator 3: Análise IA
        ai_analysis = analysis.get('ai_interpretation', {})
        if 'error' not in ai_analysis:
            confidence_factors.append(0.95)
        
        # Média ponderada
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5  # Confiança média se nenhum fator
    
    def _generate_interpretation(self, analysis: Dict[str, Any], document_type: str) -> str:
        """Gerar interpretação textual da análise"""
        interpretation_parts = []
        
        interpretation_parts.append(f"📋 INTERPRETAÇÃO MÉDICA - {document_type.upper()}")
        interpretation_parts.append("=" * 50)
        
        # Análise básica
        basic = analysis.get('basic', {})
        
        # Valores encontrados
        values = basic.get('extracted_values', [])
        if values:
            interpretation_parts.append(f"\n📊 VALORES IDENTIFICADOS ({len(values)}):")
            for value in values:
                status_icon = {'normal': '✅', 'alto': '🔴', 'baixo': '🔵', 'desconhecido': '⚪'}
                icon = status_icon.get(value['normal_status'], '⚪')
                interpretation_parts.append(
                    f"{icon} {value['parameter'].title()}: {value['value']} {value['unit']} ({value['normal_status']})"
                )
        
        # Indicadores de urgência
        urgency = basic.get('urgency_indicators', {})
        if urgency.get('has_urgency_indicators'):
            interpretation_parts.append(f"\n⚠️ INDICADORES DE URGÊNCIA:")
            interpretation_parts.append(f"Nível: {urgency['urgency_level'].upper()}")
            interpretation_parts.append(f"Palavras-chave: {', '.join(urgency['urgency_keywords'])}")
        
        # Análise avançada se disponível
        advanced = analysis.get('advanced', {})
        if 'error' not in advanced and 'pydantic_ai_analysis' in advanced:
            interpretation_parts.append(f"\n🤖 ANÁLISE AVANÇADA:")
            interpretation_parts.append("Análise estruturada com IA médica especializada realizada.")
        
        # Conclusão
        interpretation_parts.append(f"\n💡 OBSERVAÇÕES:")
        interpretation_parts.append("• Esta análise é automatizada e complementar")
        interpretation_parts.append("• Sempre consulte um profissional médico")
        interpretation_parts.append("• Em caso de urgência, procure atendimento imediato")
        
        return '\n'.join(interpretation_parts)
    
    def _generate_recommendations(self, analysis: Dict[str, Any], document_type: str) -> List[str]:
        """Gerar recomendações baseadas na análise"""
        recommendations = []
        
        # Recomendações básicas por tipo
        type_recommendations = {
            'hemograma': [
                "Acompanhar valores alterados com médico hematologista",
                "Repetir exame conforme orientação médica"
            ],
            'glicemia': [
                "Monitorar glicemia regularmente",
                "Manter dieta adequada e exercícios"
            ],
            'receita': [
                "Seguir prescrição médica rigorosamente",
                "Não interromper medicação sem orientação"
            ]
        }
        
        recommendations.extend(type_recommendations.get(document_type, [
            "Seguir orientações médicas",
            "Manter acompanhamento regular"
        ]))
        
        # Recomendações baseadas em urgência
        basic = analysis.get('basic', {})
        urgency = basic.get('urgency_indicators', {})
        
        if urgency.get('urgency_level') == 'alta':
            recommendations.insert(0, "🚨 BUSCAR ATENDIMENTO MÉDICO URGENTE")
        
        # Recomendações baseadas em valores alterados
        values = basic.get('extracted_values', [])
        altered_values = [v for v in values if v['normal_status'] in ['alto', 'baixo']]
        
        if altered_values:
            recommendations.append(f"Discutir {len(altered_values)} valor(es) alterado(s) com médico")
        
        return recommendations

# Instância global
medical_ai_service = MedicalAIService()

# Função de conveniência
async def analyze_medical_document(extracted_text: str, document_type: str = "auto", patient_info: Dict = None) -> Dict[str, Any]:
    """Função de conveniência para análise médica"""
    return await medical_ai_service.analyze_medical_document(extracted_text, document_type, patient_info)
