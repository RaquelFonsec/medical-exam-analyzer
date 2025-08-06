# ============================================================================
# AGENTE MÉDICO INTELIGENTE COM LLM (GPT) INTEGRADO
# ============================================================================

import re
import json
import logging
import openai
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ExamFinding:
    """Representa um achado em exame"""
    parameter: str
    value: str
    reference_range: str
    status: str  # normal, alto, baixo, alterado
    severity: str  # leve, moderado, grave
    clinical_significance: str
    recommendation: str

@dataclass
class ExamSummary:
    """Resumo completo do exame"""
    exam_type: str
    patient_info: Dict
    exam_date: str
    findings: List[ExamFinding]
    overall_status: str
    key_alterations: List[str]
    clinical_summary: str
    recommendations: List[str]
    follow_up_needed: bool
    llm_analysis: str  # Análise gerada por LLM
    risk_assessment: str  # Avaliação de risco por LLM

class LLMEnhancedMedicalAgent:
    """Agente médico com análise por LLM integrada"""
    
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
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
                    'basófilos', 'plaquetas', 'rdw'
                ]
            },
            'bioquimica': {
                'keywords': ['glicose', 'colesterol', 'triglicérides', 'creatinina', 'ureia', 'transaminases'],
                'parameters': [
                    'glicose', 'colesterol total', 'hdl', 'ldl', 'vldl', 'triglicérides',
                    'creatinina', 'ureia', 'ácido úrico', 'tgo', 'tgp', 'gama gt',
                    'bilirrubina', 'fosfatase alcalina', 'albumina', 'proteínas totais'
                ]
            },
            'urina': {
                'keywords': ['urina', 'eas', 'sedimento', 'proteinúria', 'microalbuminuria'],
                'parameters': [
                    'cor', 'aspecto', 'densidade', 'ph', 'proteínas', 'glicose',
                    'hemácias', 'leucócitos', 'cristais', 'cilindros', 'bactérias',
                    'cetona', 'nitrito', 'urobilinogênio'
                ]
            },
            'hormonal': {
                'keywords': ['tsh', 't4', 't3', 'cortisol', 'testosterona', 'hormônio'],
                'parameters': [
                    'tsh', 't4 livre', 't3', 'cortisol', 'testosterona',
                    'estradiol', 'progesterona', 'prolactina', 'fsh', 'lh',
                    'insulina', 'hba1c', 'vitamina d'
                ]
            },
            'cardiologico': {
                'keywords': ['troponina', 'ck-mb', 'bnp', 'nt-probnp', 'mioglobina'],
                'parameters': ['troponina', 'ck-mb', 'bnp', 'nt-probnp', 'mioglobina', 'ldh']
            }
        }
    
    def _load_reference_values(self) -> Dict:
        """Valores de referência expandidos"""
        return {
            # Hemograma
            'hemácias_homem': (4.5, 5.9, 'milhões/mm³'),
            'hemácias_mulher': (4.0, 5.2, 'milhões/mm³'),
            'hemoglobina_homem': (13.5, 17.5, 'g/dL'),
            'hemoglobina_mulher': (12.0, 16.0, 'g/dL'),
            'hematócrito_homem': (41, 53, '%'),
            'hematócrito_mulher': (36, 46, '%'),
            'leucócitos': (4000, 11000, '/mm³'),
            'neutrófilos': (45, 70, '%'),
            'linfócitos': (18, 40, '%'),
            'plaquetas': (150000, 450000, '/mm³'),
            'vcm': (80, 100, 'fL'),
            
            # Bioquímica
            'glicose_jejum': (70, 99, 'mg/dL'),
            'colesterol_total': (0, 200, 'mg/dL'),
            'hdl_homem': (40, 999, 'mg/dL'),
            'hdl_mulher': (50, 999, 'mg/dL'),
            'ldl': (0, 130, 'mg/dL'),
            'triglicérides': (0, 150, 'mg/dL'),
            'creatinina_homem': (0.7, 1.3, 'mg/dL'),
            'creatinina_mulher': (0.6, 1.1, 'mg/dL'),
            'ureia': (15, 45, 'mg/dL'),
            'tgo': (0, 40, 'U/L'),
            'tgp': (0, 41, 'U/L'),
            
            # Hormônios
            'tsh': (0.4, 4.0, 'mUI/L'),
            't4_livre': (0.8, 1.8, 'ng/dL'),
            'hba1c': (0, 5.6, '%'),
            
            # Cardiológicos
            'troponina': (0, 0.04, 'ng/mL'),
            'ck_mb': (0, 3.6, 'ng/mL'),
        }

    async def analyze_text_with_llm(self, text: str, patient_age: int = None, patient_gender: str = None) -> ExamSummary:
        """Análise completa com LLM integrado"""
        logger.info("🤖 Iniciando análise com LLM...")
        
        # 1. Análise básica (extração de dados)
        exam_type = self._identify_exam_type(text)
        patient_info = self._extract_patient_info(text)
        exam_date = self._extract_exam_date(text)
        findings = self._extract_findings(text, exam_type)
        analyzed_findings = self._analyze_findings(findings, patient_info.get('gender'))
        
        # 2. Preparar contexto para LLM
        context = self._prepare_llm_context(text, exam_type, analyzed_findings, patient_info)
        
        # 3. Gerar análise clínica com LLM
        llm_analysis = await self._generate_llm_clinical_analysis(context)
        
        # 4. Gerar avaliação de risco com LLM
        risk_assessment = await self._generate_llm_risk_assessment(context, analyzed_findings)
        
        # 5. Gerar resumo clínico inteligente com LLM
        clinical_summary = await self._generate_llm_summary(context, analyzed_findings)
        
        # 6. Gerar recomendações personalizadas com LLM
        recommendations = await self._generate_llm_recommendations(context, analyzed_findings, patient_info)
        
        # 7. Análise tradicional para backup
        key_alterations = self._identify_key_alterations(analyzed_findings)
        follow_up_needed = self._assess_follow_up_need(analyzed_findings)
        overall_status = self._determine_overall_status(analyzed_findings)
        
        return ExamSummary(
            exam_type=exam_type,
            patient_info=patient_info,
            exam_date=exam_date,
            findings=analyzed_findings,
            overall_status=overall_status,
            key_alterations=key_alterations,
            clinical_summary=clinical_summary,
            recommendations=recommendations,
            follow_up_needed=follow_up_needed,
            llm_analysis=llm_analysis,
            risk_assessment=risk_assessment
        )
    
    def _prepare_llm_context(self, text: str, exam_type: str, findings: List[ExamFinding], patient_info: Dict) -> str:
        """Prepara contexto estruturado para LLM"""
        context = f"""
CONTEXTO DO EXAME MÉDICO:
Tipo de Exame: {exam_type}
Data: {self._extract_exam_date(text)}
Paciente: {patient_info.get('name', 'Não informado')} - {patient_info.get('age', 'N/A')} anos - Sexo: {patient_info.get('gender', 'N/A')}

TEXTO ORIGINAL DO EXAME:
{text[:1000]}...

ACHADOS ESTRUTURADOS:
"""
        
        for finding in findings:
            if finding.status != 'normal':
                context += f"- {finding.parameter}: {finding.value} ({finding.status} - {finding.severity})\n"
        
        context += f"\nTOTAL DE PARÂMETROS: {len(findings)}"
        context += f"\nPARÂMETROS ALTERADOS: {len([f for f in findings if f.status != 'normal'])}"
        
        return context
    
    async def _generate_llm_clinical_analysis(self, context: str) -> str:
        """Gera análise clínica detalhada com LLM"""
        try:
            prompt = f"""
Você é um médico especialista em análise de exames laboratoriais. 
Analise os resultados abaixo e forneça uma interpretação clínica detalhada e profissional.

{context}

INSTRUÇÕES:
1. Identifique os principais achados clínicos
2. Correlacione os resultados alterados
3. Sugira possíveis diagnósticos diferenciais
4. Avalie a gravidade dos achados
5. Use linguagem médica precisa mas acessível

FORMATO DE RESPOSTA:
- Máximo 300 palavras
- Foque nos aspectos mais relevantes clinicamente
- Seja objetivo e direto
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um médico especialista em medicina laboratorial com 20 anos de experiência."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ Erro na análise LLM: {e}")
            return "Análise automática não disponível. Consulte um médico para interpretação completa."
    
    async def _generate_llm_risk_assessment(self, context: str, findings: List[ExamFinding]) -> str:
        """Gera avaliação de risco personalizada"""
        try:
            altered_findings = [f for f in findings if f.status != 'normal']
            severe_findings = [f for f in findings if f.severity == 'grave']
            
            prompt = f"""
Como médico especialista, avalie o RISCO CLÍNICO dos seguintes resultados:

{context}

ACHADOS GRAVES: {len(severe_findings)}
ALTERAÇÕES TOTAIS: {len(altered_findings)}

Classifique o risco em:
- BAIXO: Alterações leves, não requer ação imediata
- MODERADO: Alterações que necessitam acompanhamento
- ALTO: Alterações que requerem atenção médica urgente
- CRÍTICO: Alterações que requerem intervenção imediata

Forneça:
1. Classificação do risco (BAIXO/MODERADO/ALTO/CRÍTICO)
2. Justificativa em 2-3 frases
3. Prazo recomendado para avaliação médica
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um médico especialista em avaliação de risco clínico."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.2
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ Erro na avaliação de risco: {e}")
            return "MODERADO: Consulte um médico para avaliação detalhada dos resultados."
    
    async def _generate_llm_summary(self, context: str, findings: List[ExamFinding]) -> str:
        """Gera resumo clínico inteligente"""
        try:
            prompt = f"""
Crie um resumo clínico CONCISO e OBJETIVO dos resultados:

{context}

INSTRUÇÕES:
- Máximo 150 palavras
- Linguagem clara e acessível
- Destaque os pontos mais importantes
- Evite jargões médicos complexos
- Foque no que o paciente precisa saber
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um médico que explica resultados de exames de forma clara para pacientes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.4
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ Erro no resumo LLM: {e}")
            return "Resumo automático não disponível."
    
    async def _generate_llm_recommendations(self, context: str, findings: List[ExamFinding], patient_info: Dict) -> List[str]:
        """Gera recomendações personalizadas com LLM"""
        try:
            age = patient_info.get('age', 'N/A')
            gender = patient_info.get('gender', 'N/A')
            
            prompt = f"""
Com base nos resultados do exame, forneça recomendações ESPECÍFICAS e PERSONALIZADAS:

{context}

PERFIL DO PACIENTE:
- Idade: {age}
- Sexo: {gender}

INSTRUÇÕES:
- Forneça 3-5 recomendações práticas
- Personalize para idade e sexo do paciente
- Inclua mudanças de estilo de vida se apropriado
- Sugira quando repetir exames
- Seja específico e acionável

FORMATO: Lista numerada, cada recomendação em uma linha
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um médico especialista em medicina preventiva."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            recommendations_text = response.choices[0].message.content.strip()
            
            # Converter em lista
            recommendations = []
            for line in recommendations_text.split('\n'):
                if line.strip() and (line.strip().startswith('-') or line.strip()[0].isdigit()):
                    clean_line = re.sub(r'^[\d\-\.\)]\s*', '', line.strip())
                    if clean_line:
                        recommendations.append(clean_line)
            
            return recommendations[:5]  # Máximo 5 recomendações
            
        except Exception as e:
            logger.error(f"❌ Erro nas recomendações LLM: {e}")
            return ["Consulte um médico para orientações específicas sobre seus resultados."]

    # ========================================================================
    # MÉTODOS DE ANÁLISE TRADICIONAL (BACKUP)
    # ========================================================================
    
    def _identify_exam_type(self, text: str) -> str:
        """Identifica tipo de exame"""
        text_lower = text.lower()
        for exam_type, patterns in self.exam_patterns.items():
            keywords = patterns.get('keywords', [])
            if any(keyword in text_lower for keyword in keywords):
                return exam_type
        return 'geral'
    
    def _extract_patient_info(self, text: str) -> Dict:
        """Extrai informações do paciente"""
        info = {}
        patterns = {
            'name': r'(?:nome|paciente)[:\s]+([A-ZÀ-Ÿ][a-zà-ÿ\s]+)',
            'age': r'(?:idade)[:\s]+(\d+)',
            'gender': r'(?:sexo)[:\s]+(masculino|feminino|m|f)',
            'birth_date': r'(?:nascimento|nasc)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info[key] = match.group(1).strip()
        
        return info
    
    def _extract_exam_date(self, text: str) -> str:
        """Extrai data do exame"""
        date_patterns = [
            r'(?:data|realizado em)[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return datetime.now().strftime('%d/%m/%Y')
    
    def _extract_findings(self, text: str, exam_type: str) -> List[Dict]:
        """Extrai achados do exame"""
        findings = []
        
        # Múltiplos padrões para capturar diferentes formatos
        patterns = [
            r'([A-ZÀ-Ÿ][a-zà-ÿ\s\-\/]+)[:\s]+([0-9,\.]+)\s*([a-zA-Z\/³%μ]*)\s*(?:\([^)]*\))?',
            r'([A-ZÀ-Ÿ][a-zà-ÿ\s\-\/]+)[:\s]+([0-9,\.]+)\s*(?:mg\/dL|g\/dL|mm³|%|mUI\/L|ng\/dL|U\/L)',
            r'([A-ZÀ-Ÿ][a-zà-ÿ\s\-\/]+)[:\s]+([0-9,\.]+)(?:\s*[-–]\s*([0-9,\.]+))?'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                parameter = match.group(1).strip()
                value = match.group(2).strip()
                
                if self._is_valid_parameter(parameter, exam_type) and len(value) > 0:
                    findings.append({
                        'parameter': parameter,
                        'value': value,
                        'reference_range': ''
                    })
        
        return findings
    
    def _is_valid_parameter(self, parameter: str, exam_type: str) -> bool:
        """Verifica se parâmetro é válido"""
        if len(parameter) < 3 or len(parameter) > 50:
            return False
        
        if exam_type in self.exam_patterns:
            valid_params = self.exam_patterns[exam_type].get('parameters', [])
            return any(param.lower() in parameter.lower() for param in valid_params)
        
        return True
    
    def _analyze_findings(self, findings: List[Dict], gender: str = None) -> List[ExamFinding]:
        """Analisa achados com valores de referência"""
        analyzed_findings = []
        
        for finding in findings:
            param = finding['parameter'].lower()
            value_str = finding['value']
            
            try:
                value = float(value_str.replace(',', '.'))
                status, severity = self._evaluate_parameter(param, value, gender)
                clinical_significance = self._get_basic_significance(param, status)
                recommendation = self._get_basic_recommendation(param, status, severity)
                
                analyzed_findings.append(ExamFinding(
                    parameter=finding['parameter'],
                    value=value_str,
                    reference_range=finding['reference_range'],
                    status=status,
                    severity=severity,
                    clinical_significance=clinical_significance,
                    recommendation=recommendation
                ))
                
            except ValueError:
                analyzed_findings.append(ExamFinding(
                    parameter=finding['parameter'],
                    value=value_str,
                    reference_range=finding['reference_range'],
                    status='qualitativo',
                    severity='não aplicável',
                    clinical_significance='Avaliação qualitativa',
                    recommendation='Interpretação médica necessária'
                ))
        
        return analyzed_findings
    
    def _evaluate_parameter(self, param: str, value: float, gender: str) -> Tuple[str, str]:
        """Avalia parâmetro contra valores de referência"""
        ref_key = param.replace(' ', '_').replace('-', '_')
        
        # Buscar por gênero específico primeiro
        if gender and gender.lower().startswith('m'):
            gender_key = f"{ref_key}_homem"
        elif gender and gender.lower().startswith('f'):
            gender_key = f"{ref_key}_mulher"
        else:
            gender_key = None
        
        ref_range = None
        if gender_key and gender_key in self.reference_values:
            ref_range = self.reference_values[gender_key]
        elif ref_key in self.reference_values:
            ref_range = self.reference_values[ref_key]
        
        if ref_range:
            min_val, max_val, unit = ref_range
            
            if value < min_val:
                if value < min_val * 0.7:
                    return 'baixo', 'grave'
                elif value < min_val * 0.85:
                    return 'baixo', 'moderado'
                else:
                    return 'baixo', 'leve'
            elif value > max_val:
                if value > max_val * 2.0:
                    return 'alto', 'grave'
                elif value > max_val * 1.5:
                    return 'alto', 'moderado'
                else:
                    return 'alto', 'leve'
            else:
                return 'normal', 'não aplicável'
        
        return 'indeterminado', 'não aplicável'
    
    def _get_basic_significance(self, param: str, status: str) -> str:
        """Significado clínico básico"""
        if status == 'normal':
            return f'{param.title()} dentro da normalidade'
        elif status == 'alto':
            return f'{param.title()} acima do valor de referência'
        elif status == 'baixo':
            return f'{param.title()} abaixo do valor de referência'
        else:
            return f'{param.title()} requer avaliação médica'
    
    def _get_basic_recommendation(self, param: str, status: str, severity: str) -> str:
        """Recomendação básica"""
        if status == 'normal':
            return 'Manter hábitos saudáveis'
        elif severity == 'grave':
            return f"URGENTE: Procurar atendimento médico para {param}"
        else:
            return f"Acompanhamento médico recomendado para {param}"
    
    def _identify_key_alterations(self, findings: List[ExamFinding]) -> List[str]:
        """Identifica alterações principais"""
        alterations = []
        for finding in findings:
            if finding.status in ['alto', 'baixo'] and finding.severity in ['grave', 'moderado']:
                alterations.append(f"{finding.parameter} {finding.status} ({finding.value})")
        return alterations[:5]
    
    def _assess_follow_up_need(self, findings: List[ExamFinding]) -> bool:
        """Avalia necessidade de seguimento"""
        return any(finding.severity in ['grave', 'moderado'] for finding in findings)
    
    def _determine_overall_status(self, findings: List[ExamFinding]) -> str:
        """Determina status geral"""
        severe_count = sum(1 for f in findings if f.severity == 'grave')
        moderate_count = sum(1 for f in findings if f.severity == 'moderado')
        
        if severe_count > 0:
            return 'CRÍTICO - Requer atenção médica imediata'
        elif moderate_count > 2:
            return 'ALTERADO - Acompanhamento necessário'
        elif moderate_count > 0:
            return 'LEVE ALTERAÇÃO - Monitoramento recomendado'
        else:
            return 'NORMAL - Dentro dos parâmetros esperados'


# ============================================================================
# SERVIÇO TEXTRACT COM LLM INTEGRADO
# ============================================================================

class LLMEnhancedTextractService(TextractExamService):
    """Serviço Textract com análise por LLM"""
    
    def __init__(self, openai_api_key: str):
        super().__init__()
        self.llm_agent = LLMEnhancedMedicalAgent(openai_api_key)
    
    async def process_medical_exam_with_llm(self, file_bytes: bytes, filename: str) -> Dict:
        """Processa exame com análise LLM completa"""
        try:
            logger.info(f"🤖 Processando exame com LLM: {filename}")
            
            # 1. Extrair texto com Textract
            extraction_result = await self.extract_exam_text(file_bytes, filename)
            
            if not extraction_result.get('success'):
                return extraction_result
            
            extracted_text = extraction_result.get('extracted_text', '')
            
            if not extracted_text.strip():
                return {
                    'success': False,
                    'error': 'Nenhum texto foi extraído do documento'
                }
            
            # 2. Análise com LLM integrado
            logger.info("🧠 Iniciando análise com LLM...")
            exam_analysis = await self.llm_agent.analyze_text_with_llm(extracted_text)
            
            # 3. Resultado completo
            result = {
                'success': True,
                'filename': filename,
                'extracted_text': extracted_text,
                'textract_details': {
                    'text_length': extraction_result.get('text_length'),
                    'avg_confidence': extraction_result.get('avg_confidence'),
                    'pages_processed': extraction_result.get('pages_processed')
                },
                'llm_analysis': asdict(exam_analysis),
                'processing_time': datetime.now().isoformat(),
                'summary': {
                    'exam_type': exam_analysis.exam_type,
                    'overall_status': exam_analysis.overall_status,
                    'risk_assessment': exam_analysis.risk_assessment,
                    'findings_count': len(exam_analysis.findings),
                    'alterations_count': len(exam_analysis.key_alterations),
                    'follow_up_needed': exam_analysis.follow_up_needed,
                    'llm_summary': exam_analysis.llm_analysis[:200] + "..."
                }
            }
            
            logger.info(f"✅ Análise LLM concluída - {exam_analysis.exam_type}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento com LLM: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }

# ============================================================================
# ENDPOINT CORRIGIDO COM LLM
# ============================================================================

@app.post("/api/analyze-exam-with-llm")
async def analyze_medical_exam_with_llm(file: UploadFile = File(...)):
    """🤖 Análise de exame com LLM integrado"""
    
    try:
        # Verificar formato do arquivo
        supported_formats = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp']
        if not any(file.filename.lower().endswith(ext) for ext in supported_formats):
            return {
                'success': False,
                'error': f'Formato não suportado. Use: {", ".join(supported_formats)}'
            }
        
        # Verificar se OpenAI está configurado
        if not settings.OPENAI_API_KEY:
            return {
                'success': False,
                'error': 'OPENAI_API_KEY não configurada. LLM não disponível.'
            }
        
        # Ler arquivo
        file_bytes = await file.read()
        
        # Verificar tamanho
        if len(file_bytes) == 0:
            return {
                'success': False,
                'error': 'Arquivo vazio'
            }
        
        logger.info(f"📁 Processando {file.filename} ({len(file_bytes)} bytes)")
        
        # Processar com serviço LLM
        llm_service = LLMEnhancedTextractService(settings.OPENAI_API_KEY)
        result = await llm_service.process_medical_exam_with_llm(file_bytes, file.filename)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro na análise com LLM: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# ============================================================================
# ENDPOINT PARA COMPARAR ANÁLISES (COM E SEM LLM)
# ============================================================================

@app.post("/api/compare-analysis")
async def compare_traditional_vs_llm_analysis(file: UploadFile = File(...)):
    """🔬 Compara análise tradicional vs LLM"""
    
    try:
        file_bytes = await file.read()
        
        # Análise tradicional (sem LLM)
        traditional_service = EnhancedTextractService()
        traditional_result = traditional_service.process_medical_exam(file_bytes, file.filename)
        
        # Análise com LLM
        llm_service = LLMEnhancedTextractService(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        llm_result = None
        
        if llm_service:
            llm_result = await llm_service.process_medical_exam_with_llm(file_bytes, file.filename)
        
        return {
            'success': True,
            'filename': file.filename,
            'comparison': {
                'traditional_analysis': traditional_result,
                'llm_analysis': llm_result,
                'llm_available': llm_service is not None,
                'differences_summary': _compare_analyses(traditional_result, llm_result) if llm_result else None
            },
            'processing_time': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na comparação: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def _compare_analyses(traditional: Dict, llm: Dict) -> Dict:
    """Compara resultados das duas análises"""
    if not traditional.get('success') or not llm.get('success'):
        return {'comparison': 'Não foi possível comparar - uma das análises falhou'}
    
    traditional_analysis = traditional.get('analysis', {})
    llm_analysis = llm.get('llm_analysis', {})
    
    return {
        'findings_count_match': len(traditional_analysis.get('findings', [])) == len(llm_analysis.get('findings', [])),
        'overall_status_traditional': traditional_analysis.get('overall_status', 'N/A'),
        'overall_status_llm': llm_analysis.get('overall_status', 'N/A'),
        'llm_provides_additional_insights': bool(llm_analysis.get('llm_analysis')),
        'llm_risk_assessment': llm_analysis.get('risk_assessment', 'N/A'),
        'recommendation_count_traditional': len(traditional_analysis.get('recommendations', [])),
        'recommendation_count_llm': len(llm_analysis.get('recommendations', [])),
        'enhanced_features': [
            'Análise clínica contextual',
            'Avaliação de risco personalizada', 
            'Recomendações adaptadas ao paciente',
            'Linguagem mais clara e acessível'
        ]
    }

# ============================================================================
# ENDPOINT PARA RELATÓRIO DETALHADO EM HTML
# ============================================================================

@app.get("/api/exam-report/{exam_id}")
async def generate_exam_report_html(exam_id: str):
    """📄 Gera relatório HTML detalhado do exame"""
    
    # Aqui você buscaria os dados do banco de dados usando exam_id
    # Para demonstração, vou simular dados
    
    sample_report = {
        'exam_id': exam_id,
        'patient_name': 'João Silva Santos',
        'exam_date': '15/08/2024',
        'exam_type': 'Hemograma Completo',
        'overall_status': 'ALTERADO - Acompanhamento necessário',
        'llm_summary': 'Análise revela anemia leve com possível deficiência de ferro. Leucocitose discreta sugere processo inflamatório em resolução. Demais parâmetros dentro da normalidade.',
        'risk_assessment': 'MODERADO: Alterações requerem acompanhamento médico em 30 dias',
        'key_alterations': [
            'Hemoglobina baixa (11.8 g/dL)',
            'Leucócitos elevados (12.200/mm³)',
            'Ferritina baixa (12 ng/mL)'
        ],
        'recommendations': [
            'Consulta com hematologista em 15 dias',
            'Suplementação com ferro conforme orientação médica',
            'Dieta rica em ferro (carnes vermelhas, vegetais verde-escuros)',
            'Repetir hemograma em 30 dias',
            'Investigar possíveis causas de sangramento oculto'
        ]
    }
    
    html_report = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Relatório do Exame - {sample_report['exam_id']}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
                color: #333;
                background-color: #f9f9f9;
            }}
            
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 30px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            
            .patient-info {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            
            .status-badge {{
                display: inline-block;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
                margin: 10px 0;
            }}
            
            .status-moderate {{
                background: #fff3cd;
                color: #856404;
                border: 1px solid #ffeaa7;
            }}
            
            .section {{
                background: white;
                padding: 25px;
                margin-bottom: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }}
            
            .section h3 {{
                margin-top: 0;
                color: #2d3436;
                border-bottom: 2px solid #e1e5e9;
                padding-bottom: 10px;
            }}
            
            .llm-analysis {{
                background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
                border-left: 4px solid #2196F3;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                position: relative;
            }}
            
            .llm-analysis::before {{
                content: "🤖";
                position: absolute;
                top: 10px;
                right: 15px;
                font-size: 24px;
            }}
            
            .risk-assessment {{
                background: #fff8e1;
                border-left: 4px solid #ff9800;
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
            }}
            
            .alterations-list {{
                list-style: none;
                padding: 0;
            }}
            
            .alterations-list li {{
                background: #ffebee;
                margin: 8px 0;
                padding: 12px;
                border-left: 4px solid #e74c3c;
                border-radius: 5px;
            }}
            
            .recommendations-list {{
                list-style: none;
                padding: 0;
            }}
            
            .recommendations-list li {{
                background: #e8f5e8;
                margin: 8px 0;
                padding: 12px;
                border-left: 4px solid #27ae60;
                border-radius: 5px;
                position: relative;
            }}
            
            .recommendations-list li::before {{
                content: "✓";
                position: absolute;
                left: -15px;
                top: 12px;
                background: #27ae60;
                color: white;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                text-align: center;
                font-size: 12px;
                line-height: 20px;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                background: #2d3436;
                color: white;
                border-radius: 8px;
            }}
            
            .ai-badge {{
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                padding: 5px 12px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: bold;
                display: inline-block;
                margin-bottom: 10px;
            }}
            
            @media print {{
                body {{ background: white; }}
                .section, .patient-info {{ box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏥 Relatório de Exame Médico</h1>
            <div class="ai-badge">🤖 Análise Inteligente com IA</div>
            <p>Sistema de Análise Médica Automatizada</p>
        </div>
        
        <div class="patient-info">
            <h2>📋 Informações do Exame</h2>
            <p><strong>ID do Exame:</strong> {sample_report['exam_id']}</p>
            <p><strong>Paciente:</strong> {sample_report['patient_name']}</p>
            <p><strong>Data do Exame:</strong> {sample_report['exam_date']}</p>
            <p><strong>Tipo:</strong> {sample_report['exam_type']}</p>
            <div class="status-badge status-moderate">{sample_report['overall_status']}</div>
        </div>
        
        <div class="section">
            <h3>🤖 Análise Clínica Inteligente</h3>
            <div class="llm-analysis">
                <p><strong>Interpretação Automatizada:</strong></p>
                <p>{sample_report['llm_summary']}</p>
            </div>
        </div>
        
        <div class="section">
            <h3>⚠️ Avaliação de Risco</h3>
            <div class="risk-assessment">
                <p><strong>{sample_report['risk_assessment']}</strong></p>
            </div>
        </div>
        
        <div class="section">
            <h3>🔍 Principais Alterações</h3>
            <ul class="alterations-list">
    """
    
    for alteration in sample_report['key_alterations']:
        html_report += f"<li>{alteration}</li>"
    
    html_report += """
            </ul>
        </div>
        
        <div class="section">
            <h3>💡 Recomendações Personalizadas</h3>
            <ul class="recommendations-list">
    """
    
    for recommendation in sample_report['recommendations']:
        html_report += f"<li>{recommendation}</li>"
    
    html_report += f"""
            </ul>
        </div>
        
        <div class="footer">
            <p><strong>⚠️ IMPORTANTE:</strong> Este relatório é gerado automaticamente com auxílio de Inteligência Artificial.</p>
            <p>Sempre consulte um médico para interpretação completa e decisões clínicas.</p>
            <p>Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        </div>
    </body>
    </html>
    """
    
    return {"html_report": html_report, "exam_id": exam_id}

# ============================================================================
# CONFIGURAÇÃO DO SISTEMA COM LLM
# ============================================================================

# Inicializar serviços globais
if settings.OPENAI_API_KEY:
    llm_enhanced_service = LLMEnhancedTextractService(settings.OPENAI_API_KEY)
    logger.info("✅ Serviço LLM inicializado com sucesso")
else:
    llm_enhanced_service = None
    logger.warning("⚠️ OPENAI_API_KEY não configurada - LLM não disponível")

# ============================================================================
# ENDPOINT DE STATUS DO SISTEMA ATUALIZADO
# ============================================================================

@app.get("/api/system-status-enhanced")
async def enhanced_system_status():
    """📊 Status do sistema com informações sobre LLM"""
    
    return {
        'system': 'Enhanced Medical Analysis System with LLM',
        'version': '2.0 - LLM Integrated',
        'timestamp': datetime.now().isoformat(),
        'components': {
            'textract': {
                'service': 'AWS Textract',
                'status': '✅ Ready' if textract_service.client else '❌ Not configured',
                'features': ['PDF processing', 'Image OCR', 'Medical content detection']
            },
            'transcription': {
                'service': 'OpenAI Whisper',
                'status': '✅ Ready' if transcription_service.client else '❌ Not configured',
                'features': ['Audio transcription', 'Portuguese support', 'Medical context']
            },
            'llm_analysis': {
                'service': 'OpenAI GPT',
                'status': '✅ Ready' if settings.OPENAI_API_KEY else '❌ Not configured',
                'models': ['GPT-4 for analysis', 'GPT-3.5-turbo for summaries'],
                'features': [
                    '🧠 Contextual clinical analysis',
                    '⚠️ Personalized risk assessment',
                    '💡 Adaptive recommendations',
                    '📝 Clear, accessible summaries',
                    '🎯 Patient-specific insights'
                ]
            }
        },
        'new_endpoints': {
            'llm_analysis': 'POST /api/analyze-exam-with-llm',
            'comparison': 'POST /api/compare-analysis',
            'html_report': 'GET /api/exam-report/{exam_id}'
        },
        'configuration': {
            'openai_api_key': '✅ Configured' if settings.OPENAI_API_KEY else '❌ Missing',
            'aws_credentials': '✅ Configured' if settings.AWS_ACCESS_KEY_ID else '❌ Missing',
            'llm_enhanced': bool(settings.OPENAI_API_KEY)
        },
        'capabilities': {
            'traditional_analysis': True,
            'llm_enhanced_analysis': bool(settings.OPENAI_API_KEY),
            'comparison_mode': bool(settings.OPENAI_API_KEY),
            'html_reports': True,
            'risk_assessment': bool(settings.OPENAI_API_KEY),
            'personalized_recommendations': bool(settings.OPENAI_API_KEY)
        }
    }