# ============================================================================
# EXAM ANALYSIS SERVICE - LLM ROBUSTO PARA ANÁLISE MÉDICA
# services/exam_analysis_service.py
# ============================================================================

import asyncio
import time
import re
import openai
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

from .textract_service import TextractService
from config.settings import settings

logger = logging.getLogger(__name__)

# ============================================================================
# MODELS DE DADOS
# ============================================================================

@dataclass
class ExamFinding:
    """Achado individual do exame"""
    parameter: str
    value: str
    reference_range: str
    status: str  # normal, alto, baixo, alterado
    severity: str  # leve, moderado, grave
    clinical_significance: str
    recommendation: str

@dataclass
class ExamSummary:
    """Resumo completo da análise do exame"""
    exam_type: str
    patient_info: Dict
    exam_date: str
    findings: List[ExamFinding]
    overall_status: str
    key_alterations: List[str]
    clinical_summary: str
    recommendations: List[str]
    follow_up_needed: bool
    llm_analysis: str
    risk_assessment: str
    processing_strategy: str

# ============================================================================
# CIRCUIT BREAKER PARA PROTEÇÃO LLM
# ============================================================================

class LLMCircuitBreaker:
    """Circuit breaker para proteger contra falhas consecutivas do LLM"""
    
    def __init__(self, failure_threshold: int = 3, timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
    
    def can_execute(self) -> bool:
        if self.state == 'closed':
            return True
        elif self.state == 'open':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'half-open'
                logger.info("Circuit breaker em modo HALF-OPEN")
                return True
            return False
        elif self.state == 'half-open':
            return True
        return False
    
    def record_success(self):
        self.failure_count = 0
        if self.state != 'closed':
            self.state = 'closed'
            logger.info("Circuit breaker FECHADO - LLM funcionando")
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(f"Circuit breaker ABERTO - LLM bloqueado por {self.timeout/60:.1f} min")

# ============================================================================
# MONITOR DE PERFORMANCE LLM
# ============================================================================

class LLMPerformanceMonitor:
    """Monitor para acompanhar performance do LLM"""
    
    def __init__(self):
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'timeout_calls': 0,
            'avg_response_time': 0,
            'last_errors': []
        }
    
    def record_call(self, success: bool, response_time: float, error: str = None):
        self.stats['total_calls'] += 1
        
        if success:
            self.stats['successful_calls'] += 1
        else:
            self.stats['failed_calls'] += 1
            if error and 'timeout' in str(error).lower():
                self.stats['timeout_calls'] += 1
            
            if error:
                self.stats['last_errors'].append({
                    'error': str(error)[:200],
                    'timestamp': datetime.now().isoformat()
                })
                self.stats['last_errors'] = self.stats['last_errors'][-5:]
        
        # Calcular média
        current_avg = self.stats['avg_response_time']
        total_calls = self.stats['total_calls']
        self.stats['avg_response_time'] = (current_avg * (total_calls - 1) + response_time) / total_calls
    
    def get_health_status(self) -> Dict:
        total = self.stats['total_calls']
        if total == 0:
            return {'status': 'no_data', 'health': 'unknown'}
        
        success_rate = self.stats['successful_calls'] / total
        
        if success_rate > 0.9:
            health = 'excellent'
        elif success_rate > 0.7:
            health = 'good' 
        elif success_rate > 0.5:
            health = 'fair'
        else:
            health = 'poor'
        
        return {
            'status': health,
            'success_rate': f"{success_rate:.2%}",
            'avg_response_time': f"{self.stats['avg_response_time']:.2f}s",
            'total_calls': total
        }

# ============================================================================
# AGENTE LLM ROBUSTO
# ============================================================================

class RobustLLMAgent:
    """Agente LLM robusto para análise médica"""
    
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.OpenAI(
            api_key=openai_api_key,
            timeout=30.0,
            max_retries=2
        )
        self.circuit_breaker = LLMCircuitBreaker()
        self.monitor = LLMPerformanceMonitor()
        self.exam_patterns = self._load_exam_patterns()
        self.reference_values = self._load_reference_values()
    
    def _load_exam_patterns(self) -> Dict:
        """Padrões para identificar tipos de exames"""
        return {
            'hemograma': {
                'keywords': ['hemograma', 'hemácias', 'leucócitos', 'plaquetas', 'hematócrito', 'hemoglobina'],
                'parameters': [
                    'hemácias', 'hematócrito', 'hemoglobina', 'vcm', 'hcm', 'chcm',
                    'leucócitos', 'neutrófilos', 'linfócitos', 'monócitos', 'eosinófilos',
                    'plaquetas', 'rdw'
                ]
            },
            'bioquimica': {
                'keywords': ['glicose', 'colesterol', 'triglicérides', 'creatinina', 'ureia'],
                'parameters': [
                    'glicose', 'colesterol total', 'hdl', 'ldl', 'triglicérides',
                    'creatinina', 'ureia', 'ácido úrico', 'tgo', 'tgp',
                    'bilirrubina', 'fosfatase alcalina'
                ]
            },
            'urina': {
                'keywords': ['urina', 'eas', 'sedimento', 'proteinúria'],
                'parameters': [
                    'cor', 'aspecto', 'densidade', 'ph', 'proteínas', 'glicose',
                    'hemácias', 'leucócitos', 'cristais', 'cilindros'
                ]
            },
            'hormonal': {
                'keywords': ['tsh', 't4', 't3', 'cortisol', 'testosterona', 'hormônio'],
                'parameters': ['tsh', 't4 livre', 't3', 'cortisol', 'testosterona']
            }
        }
    
    def _load_reference_values(self) -> Dict:
        """Valores de referência básicos"""
        return {
            'hemácias_homem': (4.5, 5.9, 'milhões/mm³'),
            'hemácias_mulher': (4.0, 5.2, 'milhões/mm³'),
            'hemoglobina_homem': (13.5, 17.5, 'g/dL'),
            'hemoglobina_mulher': (12.0, 16.0, 'g/dL'),
            'leucócitos': (4000, 11000, '/mm³'),
            'plaquetas': (150000, 450000, '/mm³'),
            'glicose_jejum': (70, 99, 'mg/dL'),
            'colesterol_total': (0, 200, 'mg/dL'),
            'triglicérides': (0, 150, 'mg/dL'),
            'creatinina_homem': (0.7, 1.3, 'mg/dL'),
            'creatinina_mulher': (0.6, 1.1, 'mg/dL'),
            'tsh': (0.4, 4.0, 'mUI/L')
        }

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError))
    )
    async def _robust_llm_call(self, messages: List[Dict], max_tokens: int = 300, task_name: str = "analysis") -> str:
        """Chamada LLM robusta com proteções"""
        
        start_time = time.time()
        
        try:
            # Verificar circuit breaker
            if not self.circuit_breaker.can_execute():
                raise Exception("Circuit breaker OPEN - LLM temporariamente indisponível")
            
            # Configuração por task
            config = self._get_task_config(task_name)
            
            # Chamada com timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    model=config['model'],
                    messages=messages,
                    max_tokens=min(max_tokens, config['max_tokens']),
                    temperature=config['temperature'],
                    stream=False
                ),
                timeout=25.0
            )
            
            content = response.choices[0].message.content
            
            if not content or len(content.strip()) < 20:
                raise ValueError(f"Resposta muito curta: {len(content) if content else 0} chars")
            
            content = content.strip()
            
            # Registrar sucesso
            response_time = time.time() - start_time
            self.circuit_breaker.record_success()
            self.monitor.record_call(True, response_time)
            
            logger.info(f"LLM {task_name}: {response_time:.2f}s, {len(content)} chars")
            return content
            
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            error_msg = f"Timeout na chamada LLM ({response_time:.2f}s)"
            logger.error(error_msg)
            
            self.circuit_breaker.record_failure()
            self.monitor.record_call(False, response_time, error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"Erro LLM {task_name}: {str(e)}"
            logger.error(error_msg)
            
            self.circuit_breaker.record_failure()
            self.monitor.record_call(False, response_time, error_msg)
            raise Exception(error_msg)

    def _get_task_config(self, task_name: str) -> Dict:
        """Configurações otimizadas por tarefa"""
        configs = {
            'clinical_analysis': {
                'model': 'gpt-3.5-turbo-1106',
                'max_tokens': 250,
                'temperature': 0.2
            },
            'risk_assessment': {
                'model': 'gpt-3.5-turbo-1106',
                'max_tokens': 150,
                'temperature': 0.1
            },
            'summary': {
                'model': 'gpt-3.5-turbo-1106',
                'max_tokens': 200,
                'temperature': 0.3
            },
            'recommendations': {
                'model': 'gpt-3.5-turbo-1106',
                'max_tokens': 300,
                'temperature': 0.4
            }
        }
        return configs.get(task_name, configs['clinical_analysis'])

    async def analyze_exam(self, extracted_text: str, patient_info: Dict = None) -> ExamSummary:
        """Análise completa do exame com estratégias robustas"""
        
        logger.info("Iniciando análise robusta do exame")
        
        # 1. Análise tradicional (sempre funciona)
        exam_type = self._identify_exam_type(extracted_text)
        patient_data = self._extract_patient_info(extracted_text, patient_info)
        findings = self._extract_findings(extracted_text, exam_type)
        analyzed_findings = self._analyze_findings(findings, patient_data.get('gender'))
        
        # 2. Tentar análise LLM com estratégia escalonada
        llm_results = await self._escalated_llm_strategy(extracted_text, exam_type, analyzed_findings, patient_data)
        
        # 3. Montar resultado final
        return self._build_final_summary({
            'exam_type': exam_type,
            'patient_info': patient_data,
            'findings': analyzed_findings
        }, llm_results)
    
    async def _escalated_llm_strategy(self, text: str, exam_type: str, findings: List[ExamFinding], patient_info: Dict) -> Dict:
        """Estratégia escalonada para análise LLM"""
        
        context = self._prepare_context(exam_type, findings, patient_info)
        
        llm_results = {
            'clinical_analysis': None,
            'risk_assessment': None,
            'summary': None,
            'recommendations': None,
            'strategy_used': 'none'
        }
        
        try:
            # ESTRATÉGIA 1: Análise paralela completa
            logger.info("Tentando análise paralela completa")
            llm_results = await self._parallel_llm_analysis(context, findings, patient_info)
            llm_results['strategy_used'] = 'parallel_complete'
            return llm_results
            
        except Exception as e1:
            logger.warning(f"Análise paralela falhou: {e1}")
            
            try:
                # ESTRATÉGIA 2: Análise sequencial
                logger.info("Tentando análise sequencial")
                llm_results = await self._sequential_llm_analysis(context, findings, patient_info)
                llm_results['strategy_used'] = 'sequential_complete'
                return llm_results
                
            except Exception as e2:
                logger.warning(f"Análise sequencial falhou: {e2}")
                
                try:
                    # ESTRATÉGIA 3: Análise mínima
                    logger.info("Tentando análise mínima")
                    llm_results = await self._minimal_llm_analysis(context, findings)
                    llm_results['strategy_used'] = 'minimal'
                    return llm_results
                    
                except Exception as e3:
                    logger.error(f"Todas estratégias LLM falharam: {e3}")
                    llm_results['strategy_used'] = 'fallback_only'
                    return llm_results

    async def _parallel_llm_analysis(self, context: str, findings: List[ExamFinding], patient_info: Dict) -> Dict:
        """Análise paralela completa"""
        
        tasks = [
            self._generate_clinical_analysis(context),
            self._generate_risk_assessment(context, findings),
            self._generate_summary(context),
            self._generate_recommendations(context, patient_info)
        ]
        
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=60.0
        )
        
        clinical_analysis, risk_assessment, summary, recommendations = results
        
        # Verificar falhas
        failed_tasks = [r for r in results if isinstance(r, Exception)]
        if len(failed_tasks) > 2:
            raise Exception(f"Muitas tasks falharam: {len(failed_tasks)}/4")
        
        return {
            'clinical_analysis': clinical_analysis if not isinstance(clinical_analysis, Exception) else "Análise detalhada indisponível",
            'risk_assessment': risk_assessment if not isinstance(risk_assessment, Exception) else "MODERADO: Consulte médico",
            'summary': summary if not isinstance(summary, Exception) else "Exame processado",
            'recommendations': recommendations if not isinstance(recommendations, Exception) else ["Consulte médico"]
        }

    async def _sequential_llm_analysis(self, context: str, findings: List[ExamFinding], patient_info: Dict) -> Dict:
        """Análise sequencial"""
        
        results = {}
        
        try:
            results['clinical_analysis'] = await self._generate_clinical_analysis(context)
        except Exception:
            results['clinical_analysis'] = "Análise clínica indisponível"
        
        try:
            results['risk_assessment'] = await self._generate_risk_assessment(context, findings)
        except Exception:
            severe_count = len([f for f in findings if f.severity == 'grave'])
            results['risk_assessment'] = "ALTO: Atenção médica necessária" if severe_count > 0 else "MODERADO: Acompanhamento recomendado"
        
        try:
            results['summary'] = await self._generate_summary(context)
        except Exception:
            results['summary'] = "Exame processado - consulte médico para interpretação"
        
        try:
            results['recommendations'] = await self._generate_recommendations(context, patient_info)
        except Exception:
            results['recommendations'] = ["Consulte médico para orientações específicas"]
        
        return results

    async def _minimal_llm_analysis(self, context: str, findings: List[ExamFinding]) -> Dict:
        """Análise mínima - só o essencial"""
        
        try:
            risk_assessment = await self._generate_risk_assessment(context, findings)
        except Exception:
            severe_count = len([f for f in findings if f.severity == 'grave'])
            moderate_count = len([f for f in findings if f.severity == 'moderado'])
            
            if severe_count > 0:
                risk_assessment = "ALTO: Alterações graves detectadas - procure médico urgente"
            elif moderate_count > 2:
                risk_assessment = "MODERADO: Múltiplas alterações - acompanhamento necessário"
            else:
                risk_assessment = "BAIXO a MODERADO: Consulte médico para avaliação"
        
        return {
            'clinical_analysis': "Análise simplificada - consulte médico para interpretação detalhada",
            'risk_assessment': risk_assessment,
            'summary': f"Processamento básico - {len([f for f in findings if f.status != 'normal'])} alterações detectadas",
            'recommendations': ["Levar resultados para avaliação médica"]
        }

    def _prepare_context(self, exam_type: str, findings: List[ExamFinding], patient_info: Dict) -> str:
        """Prepara contexto otimizado para LLM"""
        
        altered_findings = [f for f in findings if f.status != 'normal'][:8]
        
        context = f"EXAME: {exam_type}\n"
        context += f"PACIENTE: {patient_info.get('age', 'N/A')}a, {patient_info.get('gender', 'N/A')}\n"
        context += f"ALTERAÇÕES ({len(altered_findings)}):\n"
        
        for finding in altered_findings:
            context += f"• {finding.parameter}: {finding.value} ({finding.status})\n"
        
        return context[:800]

    async def _generate_clinical_analysis(self, context: str) -> str:
        """Gera análise clínica"""
        prompt = f"""Analise como médico especialista:

{context}

Forneça interpretação clínica em até 200 palavras:
- Principais achados
- Correlações relevantes  
- Significado clínico

Seja direto e preciso."""
        
        messages = [
            {"role": "system", "content": "Você é médico especialista. Seja objetivo e claro."},
            {"role": "user", "content": prompt}
        ]
        
        return await self._robust_llm_call(messages, max_tokens=250, task_name="clinical_analysis")
    
    async def _generate_risk_assessment(self, context: str, findings: List[ExamFinding]) -> str:
        """Gera avaliação de risco"""
        severe_count = len([f for f in findings if f.severity == 'grave'])
        moderate_count = len([f for f in findings if f.severity == 'moderado'])
        
        prompt = f"""Classifique o RISCO MÉDICO:

{context}

Alterações graves: {severe_count}
Alterações moderadas: {moderate_count}

Responda APENAS:
1. RISCO: BAIXO/MODERADO/ALTO/CRÍTICO
2. Uma frase de justificativa
3. Prazo para consulta médica

Máximo 50 palavras."""
        
        messages = [
            {"role": "system", "content": "Você classifica risco médico de forma objetiva."},
            {"role": "user", "content": prompt}
        ]
        
        return await self._robust_llm_call(messages, max_tokens=100, task_name="risk_assessment")
    
    async def _generate_summary(self, context: str) -> str:
        """Gera resumo"""
        prompt = f"""Resuma para o paciente em linguagem simples:

{context}

Máximo 100 palavras, linguagem clara."""
        
        messages = [
            {"role": "system", "content": "Explique resultados médicos de forma clara para pacientes."},
            {"role": "user", "content": prompt}
        ]
        
        return await self._robust_llm_call(messages, max_tokens=150, task_name="summary")
    
    async def _generate_recommendations(self, context: str, patient_info: Dict) -> List[str]:
        """Gera recomendações"""
        age = patient_info.get('age', 'N/A')
        gender = patient_info.get('gender', 'N/A')
        
        prompt = f"""5 recomendações práticas:

{context}

Paciente: {age} anos, {gender}

Liste 5 ações específicas e práticas."""
        
        messages = [
            {"role": "system", "content": "Forneça recomendações médicas práticas."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = await self._robust_llm_call(messages, max_tokens=200, task_name="recommendations")
            
            recommendations = []
            for line in response.split('\n'):
                if line.strip() and any(line.strip().startswith(prefix) for prefix in ['1', '2', '3', '4', '5', '-', '•']):
                    clean_line = re.sub(r'^[\d\-\.\)•]\s*', '', line.strip())
                    if clean_line and len(clean_line) > 10:
                        recommendations.append(clean_line)
            
            return recommendations[:5] if recommendations else ["Consulte médico para orientações específicas"]
            
        except Exception:
            return ["Consulte médico para orientações específicas"]

    # Métodos de análise tradicional (fallbacks)
    def _identify_exam_type(self, text: str) -> str:
        text_lower = text.lower()
        for exam_type, patterns in self.exam_patterns.items():
            keywords = patterns.get('keywords', [])
            if any(keyword in text_lower for keyword in keywords):
                return exam_type
        return 'geral'
    
    def _extract_patient_info(self, text: str, provided_info: Dict = None) -> Dict:
        info = provided_info or {}
        
        patterns = {
            'name': r'(?:nome|paciente)[:\s]+([A-ZÀ-Ÿ][a-zà-ÿ\s]+)',
            'age': r'(?:idade)[:\s]+(\d+)',
            'gender': r'(?:sexo)[:\s]+(masculino|feminino|m|f)',
        }
        
        for key, pattern in patterns.items():
            if key not in info:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    info[key] = match.group(1).strip()
        
        return info
    
    def _extract_findings(self, text: str, exam_type: str) -> List[Dict]:
        findings = []
        patterns = [
            r'([A-ZÀ-Ÿ][a-zà-ÿ\s\-\/]+)[:\s]+([0-9,\.]+)\s*([a-zA-Z\/³%μ]*)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                parameter = match.group(1).strip()
                value = match.group(2).strip()
                
                if self._is_valid_parameter(parameter, exam_type):
                    findings.append({
                        'parameter': parameter,
                        'value': value,
                        'reference_range': ''
                    })
        
        return findings
    
    def _is_valid_parameter(self, parameter: str, exam_type: str) -> bool:
        if len(parameter) < 3 or len(parameter) > 50:
            return False
        
        invalid_words = ['data', 'nome', 'idade', 'sexo', 'médico']
        if any(word in parameter.lower() for word in invalid_words):
            return False
        
        return True
    
    def _analyze_findings(self, findings: List[Dict], gender: str = None) -> List[ExamFinding]:
        analyzed_findings = []
        
        for finding in findings:
            param = finding['parameter'].lower()
            value_str = finding['value']
            
            try:
                value = float(value_str.replace(',', '.'))
                status, severity = self._evaluate_parameter(param, value, gender)
                
                analyzed_findings.append(ExamFinding(
                    parameter=finding['parameter'],
                    value=value_str,
                    reference_range=self._get_reference_range_text(param, gender),
                    status=status,
                    severity=severity,
                    clinical_significance=f'{finding["parameter"]} - {status}',
                    recommendation=f"Acompanhamento médico recomendado" if status != 'normal' else "Manter hábitos saudáveis"
                ))
                
            except ValueError:
                analyzed_findings.append(ExamFinding(
                    parameter=finding['parameter'],
                    value=value_str,
                    reference_range='',
                    status='qualitativo',
                    severity='não aplicável',
                    clinical_significance=f'{finding["parameter"]} - valor qualitativo',
                    recommendation='Interpretação médica necessária'
                ))
        
        return analyzed_findings
    
    def _evaluate_parameter(self, param: str, value: float, gender: str) -> Tuple[str, str]:
        ref_key = param.replace(' ', '_').replace('-', '_')
        
        gender_key = None
        if gender and gender.lower().startswith('m'):
            gender_key = f"{ref_key}_homem"
        elif gender and gender.lower().startswith('f'):
            gender_key = f"{ref_key}_mulher"
        
        ref_range = None
        if gender_key and gender_key in self.reference_values:
            ref_range = self.reference_values[gender_key]
        elif ref_key in self.reference_values:
            ref_range = self.reference_values[ref_key]
        
        if ref_range:
            min_val, max_val, unit = ref_range
            
            if value < min_val:
                if value < min_val * 0.6:
                    return 'baixo', 'grave'
                elif value < min_val * 0.8:
                    return 'baixo', 'moderado'
                else:
                    return 'baixo', 'leve'
            elif value > max_val:
                if value > max_val * 2.5:
                    return 'alto', 'grave'
                elif value > max_val * 1.8:
                    return 'alto', 'moderado'
                else:
                    return 'alto', 'leve'
            else:
                return 'normal', 'não aplicável'
        
        return 'indeterminado', 'não aplicável'
    
    def _get_reference_range_text(self, param: str, gender: str) -> str:
        ref_key = param.replace(' ', '_').replace('-', '_')
        
        if gender and gender.lower().startswith('m'):
            gender_key = f"{ref_key}_homem"
        elif gender and gender.lower().startswith('f'):
            gender_key = f"{ref_key}_mulher"
        else:
            gender_key = None
        
        if gender_key and gender_key in self.reference_values:
            min_val, max_val, unit = self.reference_values[gender_key]
            return f"{min_val} - {max_val} {unit}"
        elif ref_key in self.reference_values:
            min_val, max_val, unit = self.reference_values[ref_key]
            return f"{min_val} - {max_val} {unit}"
        
        return "Consultar valores de referência"
    
    def _build_final_summary(self, fallback_data: Dict, llm_results: Dict) -> ExamSummary:
        """Monta resultado final combinando análise tradicional + LLM"""
        
        exam_type = fallback_data['exam_type']
        patient_info = fallback_data['patient_info']
        findings = fallback_data['findings']
        
        # Análise tradicional como base sólida
        key_alterations = self._identify_key_alterations(findings)
        follow_up_needed = self._assess_follow_up_need(findings)
        overall_status = self._determine_overall_status(findings)
        
        # Usar resultados LLM se disponíveis, senão usar fallbacks
        clinical_summary = llm_results.get('summary') or self._generate_fallback_summary(exam_type, findings)
        llm_analysis = llm_results.get('clinical_analysis') or "Análise detalhada não disponível - consulte médico"
        risk_assessment = llm_results.get('risk_assessment') or self._generate_fallback_risk(findings)
        recommendations = llm_results.get('recommendations') or self._generate_fallback_recommendations(findings)
        
        # Garantir que recommendations é lista
        if not isinstance(recommendations, list):
            recommendations = [str(recommendations)]
        
        strategy_used = llm_results.get('strategy_used', 'fallback_only')
        logger.info(f"Análise concluída com estratégia: {strategy_used}")
        
        return ExamSummary(
            exam_type=exam_type,
            patient_info=patient_info,
            exam_date=datetime.now().strftime('%d/%m/%Y'),
            findings=findings,
            overall_status=overall_status,
            key_alterations=key_alterations,
            clinical_summary=clinical_summary,
            recommendations=recommendations,
            follow_up_needed=follow_up_needed,
            llm_analysis=llm_analysis,
            risk_assessment=risk_assessment,
            processing_strategy=strategy_used
        )
    
    def _identify_key_alterations(self, findings: List[ExamFinding]) -> List[str]:
        """Identifica alterações principais"""
        alterations = []
        for severity in ['grave', 'moderado', 'leve']:
            for finding in findings:
                if finding.severity == severity and finding.status in ['alto', 'baixo']:
                    alt_text = f"{finding.parameter}: {finding.value} ({finding.status})"
                    alterations.append(alt_text)
                    if len(alterations) >= 5:
                        return alterations
        return alterations
    
    def _assess_follow_up_need(self, findings: List[ExamFinding]) -> bool:
        """Avalia necessidade de seguimento"""
        return any(finding.severity in ['grave', 'moderado'] for finding in findings)
    
    def _determine_overall_status(self, findings: List[ExamFinding]) -> str:
        """Determina status geral"""
        severe_count = sum(1 for f in findings if f.severity == 'grave')
        moderate_count = sum(1 for f in findings if f.severity == 'moderado')
        mild_count = sum(1 for f in findings if f.severity == 'leve')
        
        if severe_count > 0:
            return f'CRÍTICO - {severe_count} alteração(ões) grave(s) - Atenção médica imediata'
        elif moderate_count > 3:
            return f'ALTERADO - {moderate_count} alterações moderadas - Acompanhamento urgente'
        elif moderate_count > 0:
            return f'ALTERADO - {moderate_count} alteração(ões) moderada(s) - Consulta recomendada'
        elif mild_count > 2:
            return f'LEVE ALTERAÇÃO - {mild_count} alterações leves - Monitoramento'
        else:
            return 'NORMAL - Resultados dentro dos parâmetros esperados'
    
    # Fallbacks quando LLM não disponível
    def _generate_fallback_summary(self, exam_type: str, findings: List[ExamFinding]) -> str:
        """Resumo fallback"""
        altered_count = len([f for f in findings if f.status != 'normal'])
        severe_count = len([f for f in findings if f.severity == 'grave'])
        
        if severe_count > 0:
            return f"Exame {exam_type} apresenta {severe_count} alteração(ões) significativa(s) que requer(em) atenção médica prioritária."
        elif altered_count > 0:
            return f"Exame {exam_type} mostra {altered_count} parâmetro(s) alterado(s), necessitando avaliação médica."
        else:
            return f"Exame {exam_type} com resultados dentro da normalidade."
    
    def _generate_fallback_risk(self, findings: List[ExamFinding]) -> str:
        """Avaliação de risco fallback"""
        severe_count = len([f for f in findings if f.severity == 'grave'])
        moderate_count = len([f for f in findings if f.severity == 'moderado'])
        
        if severe_count > 0:
            return "ALTO: Alterações significativas detectadas - consulta médica urgente recomendada"
        elif moderate_count > 2:
            return "MODERADO: Múltiplas alterações - acompanhamento médico necessário em 30 dias"
        elif moderate_count > 0:
            return "BAIXO a MODERADO: Algumas alterações - consulta médica recomendada"
        else:
            return "BAIXO: Resultados dentro da normalidade - manter acompanhamento de rotina"
    
    def _generate_fallback_recommendations(self, findings: List[ExamFinding]) -> List[str]:
        """Recomendações fallback"""
        severe_count = len([f for f in findings if f.severity == 'grave'])
        moderate_count = len([f for f in findings if f.severity == 'moderado'])
        
        if severe_count > 0:
            return [
                "Procurar atendimento médico com urgência",
                "Levar este resultado completo ao médico", 
                "Não adiar a consulta médica",
                "Evitar automedicação"
            ]
        elif moderate_count > 0:
            return [
                "Agendar consulta médica para avaliação",
                "Manter hábitos de vida saudáveis",
                "Repetir exames conforme orientação médica",
                "Monitorar sintomas relacionados"
            ]
        else:
            return [
                "Manter hábitos de vida saudáveis",
                "Seguir cronograma de exames preventivos",
                "Praticar atividade física regular"
            ]

# ============================================================================
# EXAM ANALYSIS SERVICE PRINCIPAL
# ============================================================================

class ExamAnalysisService:
    """Serviço principal para análise de exames médicos"""
    
    def __init__(self):
        self.textract_service = TextractService()
        self.llm_agent = None
        
        if settings.OPENAI_API_KEY:
            self.llm_agent = RobustLLMAgent(settings.OPENAI_API_KEY)
            logger.info("ExamAnalysisService inicializado com LLM robusto")
        else:
            logger.warning("LLM não disponível - OPENAI_API_KEY não configurada")
    
    async def analyze_exam_complete(self, file_bytes: bytes, filename: str, patient_info: Dict = None) -> Dict[str, Any]:
        """
        Análise completa de exame: Textract + LLM Robusto
        
        Este é o método principal que coordena:
        1. Extração de texto com Textract
        2. Análise inteligente com LLM robusto
        3. Fallback para análise básica se necessário
        """
        
        processing_start = time.time()
        
        try:
            logger.info(f"Iniciando análise completa de: {filename}")
            
            # 1. EXTRAÇÃO DE TEXTO COM TEXTRACT
            logger.info("Fase 1: Extraindo texto com Textract")
            extraction_result = await self.textract_service.extract_text(file_bytes, filename)
            
            if not extraction_result.get('success'):
                return {
                    'success': False,
                    'error': extraction_result.get('error', 'Falha na extração de texto'),
                    'phase': 'text_extraction'
                }
            
            extracted_text = extraction_result.get('extracted_text', '')
            
            if not extracted_text or len(extracted_text.strip()) < 50:
                return {
                    'success': False,
                    'error': 'Texto extraído insuficiente para análise médica',
                    'extracted_length': len(extracted_text) if extracted_text else 0,
                    'phase': 'text_validation'
                }
            
            # 2. ANÁLISE INTELIGENTE COM LLM (se disponível)
            analysis_start = time.time()
            
            if self.llm_agent:
                try:
                    logger.info("Fase 2: Análise inteligente com LLM robusto")
                    exam_summary = await self.llm_agent.analyze_exam(extracted_text, patient_info)
                    
                    analysis_time = time.time() - analysis_start
                    total_time = time.time() - processing_start
                    
                    # Resultado completo com LLM
                    return {
                        'success': True,
                        'filename': filename,
                        'analysis_type': 'robust_llm',
                        'processing_times': {
                            'extraction': f"{analysis_start - processing_start:.2f}s",
                            'llm_analysis': f"{analysis_time:.2f}s",
                            'total': f"{total_time:.2f}s"
                        },
                        'exam_analysis': asdict(exam_summary),
                        'system_health': {
                            'llm_circuit_breaker': self.llm_agent.circuit_breaker.state,
                            'llm_performance': self.llm_agent.monitor.get_health_status(),
                            'processing_strategy': exam_summary.processing_strategy
                        },
                        'extracted_text_preview': extracted_text[:300] + "..." if len(extracted_text) > 300 else extracted_text,
                        'textract_details': {
                            'confidence': extraction_result.get('avg_confidence', 0),
                            'pages_processed': extraction_result.get('pages_processed', 1)
                        },
                        'timestamp': datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    logger.error(f"Erro na análise LLM, usando fallback básico: {e}")
                    # Fallback para análise básica
                    return self._create_basic_analysis_result(extracted_text, filename, extraction_result, processing_start)
            else:
                logger.info("Fase 2: LLM não disponível, usando análise básica")
                return self._create_basic_analysis_result(extracted_text, filename, extraction_result, processing_start)
                
        except Exception as e:
            total_time = time.time() - processing_start
            logger.error(f"Erro crítico na análise completa: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'filename': filename,
                'processing_time': f"{total_time:.2f}s",
                'phase': 'critical_error',
                'timestamp': datetime.now().isoformat()
            }
    
    def _create_basic_analysis_result(self, extracted_text: str, filename: str, extraction_result: Dict, processing_start: float) -> Dict:
        """Cria resultado com análise básica quando LLM não disponível"""
        
        total_time = time.time() - processing_start
        
        # Análise básica sem LLM
        basic_findings = self._extract_basic_findings(extracted_text)
        exam_type = self._identify_basic_exam_type(extracted_text)
        
        return {
            'success': True,
            'filename': filename,
            'analysis_type': 'basic_fallback',
            'processing_times': {
                'total': f"{total_time:.2f}s"
            },
            'basic_analysis': {
                'exam_type': exam_type,
                'key_findings': basic_findings,
                'overall_status': 'REQUER INTERPRETAÇÃO MÉDICA',
                'clinical_summary': 'Análise básica realizada. Consulte médico para interpretação completa dos resultados.',
                'recommendations': [
                    'Consulte médico para interpretação detalhada',
                    'Leve este resultado para avaliação profissional',
                    'Não ignore valores alterados se houver'
                ],
                'risk_assessment': 'Consulte médico para avaliação de risco adequada'
            },
            'extracted_text_preview': extracted_text[:300] + "..." if len(extracted_text) > 300 else extracted_text,
            'textract_details': {
                'confidence': extraction_result.get('avg_confidence', 0),
                'pages_processed': extraction_result.get('pages_processed', 1),
                'text_length': len(extracted_text)
            },
            'system_health': {
                'llm_available': False,
                'textract_working': True,
                'fallback_analysis': True
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _extract_basic_findings(self, text: str) -> List[str]:
        """Extrai achados básicos usando regex"""
        findings = []
        
        # Padrões simples para detectar valores
        patterns = [
            r'([A-ZÀ-Ÿ][a-zà-ÿ\s\-\/]+)[:\s]+([0-9,\.]+)\s*([a-zA-Z\/³%μ]*)',
            r'(alto|baixo|elevado|diminuído|aumentado)[:\s]*([A-ZÀ-Ÿ][a-zà-ÿ\s\-\/]+)'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                finding = match.group(0).strip()
                if len(finding) > 5 and finding not in findings:
                    findings.append(finding)
        
        return findings[:8]  # Máximo 8 achados
    
    def _identify_basic_exam_type(self, text: str) -> str:
        """Identifica tipo básico de exame"""
        text_lower = text.lower()
        
        exam_types = {
            'hemograma': ['hemograma', 'hemácias', 'leucócitos', 'plaquetas'],
            'bioquimica': ['glicose', 'colesterol', 'creatinina', 'ureia'],
            'hormonal': ['tsh', 't4', 't3', 'cortisol'],
            'urina': ['urina', 'eas', 'sedimento']
        }
        
        for exam_type, keywords in exam_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return exam_type
        
        return 'geral'
    
    def get_health_status(self) -> Dict:
        """Status de saúde do serviço"""
        return {
            'service': 'ExamAnalysisService',
            'version': '3.0 - Robust LLM',
            'llm_available': self.llm_agent is not None,
            'llm_status': self.llm_agent.monitor.get_health_status() if self.llm_agent else 'Not available',
            'llm_circuit_breaker': self.llm_agent.circuit_breaker.state if self.llm_agent else 'N/A',
            'textract_status': self.textract_service.get_health_status(),
            'capabilities': [
                'Text extraction with AWS Textract',
                'Robust LLM analysis with circuit breaker protection',
                'Automatic fallback to basic analysis',
                'Multi-strategy processing (parallel -> sequential -> minimal)',
                'Real-time performance monitoring',
                'Clinical interpretation with risk assessment',
                'Personalized recommendations'
            ]
        }
    
    def get_status(self) -> str:
        """Status simples do serviço"""
        if self.llm_agent:
            circuit_state = self.llm_agent.circuit_breaker.state
            return f"Ready with LLM ({circuit_state})"
        else:
            return "Basic analysis only (no LLM)"