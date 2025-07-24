import re
from typing import Dict, List, Tuple, Any
from datetime import datetime

class ContextClassifierService:
    
    def __init__(self):
        # PALAVRAS-CHAVE REFINADAS E EXPANDIDAS
        self.keywords = {
            'bpc': [
                'bpc', 'loas', 'beneficio de prestacao continuada',
                'deficiencia', 'deficiente', 'invalidez total',
                'cuidador', 'cuidar de mim', 'nao consigo me cuidar',
                'atividades basicas', 'vida independente', 'impedimento longo prazo',
                'renda familiar', 'salario minimo', 'baixa renda',
                
                # DEFICIÊNCIA VISUAL ESPECÍFICA
                'glaucoma', 'cegueira', 'cego', 'perda de visao', 'perdendo visao',
                'nao consigo ler', 'nao consigo escrever', 'precisa de orientacao',
                'deficiencia visual', 'baixa visao', 'catarata avancada',
                
                # DEFICIÊNCIA COGNITIVA
                'alzheimer', 'demencia', 'nao consigo lembrar', 'perda memoria',
                'nao consegue se cuidar', 'supervisao constante',
                
                # DEPENDÊNCIA PARA ATIVIDADES BÁSICAS
                'dependente para', 'ajuda para tomar banho', 'ajuda para comer',
                'nao consegue andar sozinho', 'cadeira de rodas',
                'impedimento longo prazo', 'deficiência permanente'
            ],
            
            'incapacidade': [
                # Termos diretos de incapacidade laboral
                'auxilio doenca', 'aposentadoria por invalidez', 'incapacidade laboral',
                'inss', 'beneficio por incapacidade', 'afastamento do trabalho',
                'seguro social', 'previdencia social', 'pericia inss',
                
                # Impossibilidade explícita para trabalhar
                'nao consigo mais trabalhar', 'nao consigo mais atender', 
                'nao consigo mais exercer', 'nao consigo mais segurar',
                'nao tenho mais precisao', 'nao aguento mais trabalhar',
                'impossivel trabalhar', 'incapaz de trabalhar',
                'limitacao para trabalhar', 'dificuldade para trabalhar',
                'nao posso mais', 'nao aguento esforco',
                
                # INCAPACIDADE PARA ATIVIDADE HABITUAL - FOCO PRINCIPAL
                'incapacidade para o trabalho habitual', 'incapacidade para trabalho habitual',
                'exercicio da profissao', 'exercer a profissao', 'exercer sua profissao',
                'atividade laboral habitual', 'funcao exercida', 'trabalho habitual',
                'profissao de pedreiro', 'trabalho como pedreiro', 'exercer como pedreiro',
                'limitacoes funcionais', 'limitacoes laborais', 'comprometem o exercicio',
                'impedem o exercicio', 'interferem nas atividades laborais',
                
                # Correlações profissão-limitação
                'profissao exige', 'trabalho requer', 'funcao demanda',
                'atividade profissional', 'capacidade de trabalho',
                'precisao manual', 'esforco fisico', 'concentracao',
                'atender pacientes', 'segurar instrumentos', 'dar aula',
                'dirigir veiculo', 'carregar peso', 'ficar em pe',
                'trabalhar sob pressao', 'tomar decisoes', 'plantao',
                'comunicacao telefonica', 'uso de headset', 'fones de ouvido',
                
                # ESPECÍFICOS PARA PEDREIRO E TRABALHO FÍSICO
                'levantamento de peso', 'trabalho em altura', 'esforco fisico intenso',
                'carregar sacos', 'carregar material', 'trabalhar com furadeira',
                'atividades que demandam', 'exigencias da funcao', 'demandas profissionais',
                'incompativeis com as exigencias', 'exercicio seguro das atividades',
                
                # Especiais para atendimento/telemarketing
                'atendimento ao cliente', 'call center', 'telemarketing',
                'nao consigo escutar cliente', 'nao consigo atender telefone',
                'custom service', 'headset machuca', 'fone de ouvido dói'
            ],
            
            'auxilio_acidente': [
                # TERMOS DIRETOS E ESPECÍFICOS
                'auxilio acidente', 'auxilio-acidente', 'reducao da capacidade', 
                'acidente de trabalho', 'acidente no trabalho',
                'sequela', 'sequelas de acidente', 'incapacidade parcial', 'capacidade reduzida',
                'acidente na fabrica', 'acidente na empresa', 'lesao no trabalho',
                'cat', 'comunicacao de acidente', 'nexo causal', 'doenca ocupacional',
                'ler dort', 'lesao por esforco repetitivo',
                
                # PADRÕES ESPECÍFICOS PARA ACIDENTE DE TRABALHO
                'sofri um acidente no trabalho', 'acidente de trabalho', 'cai', 'bati a coluna',
                'relacionado a acidente de trabalho', 'acidente com limitacoes funcionais',
                'evolucao com limitacoes funcionais', 'sequelas de acidente com limitacoes',
                'ha dois anos sofri', 'desde entao nao consigo', 'desde o acidente'
            ],
            
            'isencao_ir': [
                'isencao', 'imposto de renda', 'receita federal',
                'doenca grave', 'neoplasia', 'cancer', 'tumor',
                'quimioterapia', 'radioterapia', 'oncologico',
                'aids', 'hiv', 'parkinson', 'alzheimer', 'esclerose multipla',
                'cardiopatia grave', 'nefropatia grave', 'cegueira',
                'hanseníase', 'tuberculose ativa'
            ],
            
            'pericia': [
                'pericia medica', 'avaliacao pericial', 'junta medica',
                'processo judicial', 'advogado solicitou', 'acao trabalhista',
                'processo previdenciario', 'recurso inss', 'contestacao',
                'segunda opiniao', 'revisao medica'
            ],
            
            'clinica': [
                'consulta medica', 'acompanhamento', 'tratamento',
                'medicacao', 'exame de rotina', 'check up',
                'orientacao medica', 'prescricao', 'receita medica'
            ]
        }
        
        # PROFISSÕES E SUAS LIMITAÇÕES ESPECÍFICAS (expandido)
        self.profession_limitations = {
            # Profissões de comunicação e atendimento
            'atendente': ['comunicacao telefonica', 'uso de headset', 'escutar cliente', 'concentracao auditiva'],
            'telemarketing': ['comunicacao telefonica', 'uso de headset', 'escutar cliente', 'concentracao prolongada'],
            'operador': ['comunicacao telefonica', 'uso de equipamentos', 'concentracao auditiva'],
            'operadora': ['comunicacao telefonica', 'uso de equipamentos', 'concentracao auditiva'],
            'recepcionista': ['atendimento publico', 'comunicacao telefonica', 'uso equipamentos'],
            'secretaria': ['atividades administrativas', 'comunicacao telefonica', 'uso computador'],
            'secretario': ['atividades administrativas', 'comunicacao telefonica', 'uso computador'],
            
            # Profissões educacionais
            'dentista': ['precisao manual', 'segurar instrumentos', 'atender pacientes', 'concentracao'],
            'professor': ['dar aula', 'concentracao', 'interacao social', 'controle emocional'],
            'professora': ['dar aula', 'concentracao', 'interacao social', 'controle emocional'],
            
            # Profissões físicas
            'motorista': ['dirigir', 'reflexos', 'esforco fisico', 'concentracao'],
            'pedreiro': ['carregar peso', 'esforco fisico', 'trabalhar em altura'],
            'enfermeiro': ['plantao', 'esforco fisico', 'cuidar pacientes', 'tomar decisoes'],
            'enfermeira': ['plantao', 'esforco fisico', 'cuidar pacientes', 'tomar decisoes'],
            'medico': ['plantao', 'tomar decisoes', 'concentracao', 'precisao'],
            'medica': ['plantao', 'tomar decisoes', 'concentracao', 'precisao'],
            
            # Profissões comerciais
            'vendedor': ['comunicacao', 'esforco fisico', 'concentracao'],
            'vendedora': ['comunicacao', 'esforco fisico', 'concentracao'],
            'caixa': ['atendimento publico', 'ficar em pe', 'concentracao'],
            
            # Profissões técnicas
            'tecnico': ['atividades tecnicas', 'concentracao', 'uso equipamentos'],
            'tecnica': ['atividades tecnicas', 'concentracao', 'uso equipamentos'],
            'analista': ['analises complexas', 'concentracao prolongada', 'uso computador'],
            
            # Profissões de serviços
            'faxineiro': ['esforco fisico', 'carregar peso', 'movimentos repetitivos'],
            'faxineira': ['esforco fisico', 'carregar peso', 'movimentos repetitivos'],
            'seguranca': ['vigilancia', 'reflexos', 'esforco fisico'],
            'vigilante': ['vigilancia prolongada', 'atencao constante'],
            
            # Profissões industriais
            'operario': ['esforco fisico', 'carregar peso', 'linha producao'],
            'operaria': ['esforco fisico', 'carregar peso', 'linha producao'],
            'soldador': ['concentracao visual', 'controle motor', 'ambiente industrial'],
            'soldadora': ['concentracao visual', 'controle motor', 'ambiente industrial'],
            'mecanico': ['esforco fisico', 'uso ferramentas', 'posicoes inadequadas'],
            'mecanica': ['esforco fisico', 'uso ferramentas', 'posicoes inadequadas']
        }
        
        # INDICADORES DE GRAVIDADE POR BENEFÍCIO
        self.severity_indicators = {
            'bpc': [
                'dependente para tudo', 'nao consegue sozinho', 'precisa cuidador',
                'sem autonomia', 'limitacao severa', 'incapacidade total',
                'vida independente comprometida', 'participacao social impossivel'
            ],
            'incapacidade': [
                'impossivel trabalhar', 'incapaz trabalhar', 'nao aguento mais',
                'profissao impossivel', 'limitacao total para trabalho',
                'incapacidade permanente', 'afastamento definitivo'
            ],
            'auxilio_acidente': [
                'reducao capacidade', 'limitacao parcial', 'sequela permanente',
                'capacidade diminuida', 'aptidao reduzida'
            ]
        }
        
        # ESPECIALIDADES MÉDICAS REFINADAS
        self.medical_specialties = {
            'otorrinolaringologia': [
                'perda auditiva', 'surdez', 'nao escuto', 'ouvido', 'audicao',
                'zumbido', 'tontura', 'vertigem', 'otite', 'sinusite',
                'garganta', 'nariz', 'fone machuca', 'headset dói'
            ],
            'psiquiatria': [
                'depressao', 'ansiedade', 'panico', 'transtorno mental',
                'saude mental', 'psiquiatrico', 'bipolar', 'esquizofrenia',
                'sindrome panico', 'crise ansiedade', 'estresse', 'insonia',
                'concentracao ruim', 'memoria ruim', 'humor alterado'
            ],
            'cardiologia': [
                'coracao', 'infarto', 'pressao alta', 'cardiovascular',
                'cardiaco', 'angina', 'insuficiencia cardiaca', 'arritmia',
                'hipertensao', 'esforco fisico cardiaco', 'falta ar', 'cansaco'
            ],
            'ortopedia': [
                'dor coluna', 'dor lombar', 'hernia disco', 'fratura',
                'dor costas', 'carregar peso', 'lombalgia', 'dor articular',
                'dor muscular', 'lesao ortopedica', 'problema coluna',
                'articulacao', 'osso', 'joelho', 'ombro', 'punho'
            ],
            'neurologia': [
                'avc', 'derrame', 'parkinson', 'epilepsia', 'neurologico',
                'convulsao', 'demencia', 'alzheimer', 'esclerose multipla',
                'dor cabeca', 'enxaqueca', 'cefaleia', 'tontura neurológica'
            ],
            'reumatologia': [
                'artrite', 'artrose', 'reumatoide', 'lupus', 'fibromialgia',
                'reumatico', 'dor articular cronica', 'inflamacao articular'
            ],
            'oncologia': [
                'cancer', 'tumor', 'neoplasia', 'quimioterapia', 'oncologico',
                'metastase', 'carcinoma', 'leucemia', 'linfoma', 'radioterapia'
            ],
            'endocrinologia': [
                'diabetes', 'tireoide', 'hormonio', 'endocrino', 'glicemia',
                'insulina', 'hipotireoidismo', 'hipertireoidismo'
            ]
        }
    
    def classify_context(self, patient_info: str, transcription: str, documents_text: str = "") -> Dict[str, Any]:
        """Classificar contexto médico de forma simples e funcional"""
        
        # Combinar todo o texto
        full_text = f"{patient_info} {transcription} {documents_text}".strip()
        text_lower = full_text.lower()
        
        print(f"🔍 Analisando texto: {full_text[:200]}...")
        
        # Detectar especialidade
        detected_specialty = self._detect_specialty_simple(full_text)
        print(f"🏥 Especialidade detectada: {detected_specialty}")
        
        # Análise básica de palavras-chave
        basic_scores = self._analyze_keywords_simple(text_lower)
        print(f"📊 Scores básicos: {basic_scores}")
        
        # Determinar benefício principal
        main_benefit = self._determine_main_benefit_simple(basic_scores, text_lower)
        print(f"🎯 Benefício principal: {main_benefit}")
        
        return {
            'main_benefit': main_benefit,
            'detected_specialty': detected_specialty,
            'confidence_score': 0.8,
            'scores': basic_scores
        }
    
    def _analyze_keywords_simple(self, text: str) -> Dict[str, Dict]:
        """Análise simples de palavras-chave"""
        
        scores = {
            'bpc': {'score': 0, 'keywords': []},
            'auxilio_acidente': {'score': 0, 'keywords': []},
            'auxilio_doenca': {'score': 0, 'keywords': []},
            'isencao_ir': {'score': 0, 'keywords': []},
            'incapacidade': {'score': 0, 'keywords': []},
            'pericia': {'score': 0, 'keywords': []},
            'clinica': {'score': 0, 'keywords': []}
        }
        
        # BPC
        bpc_keywords = ['bpc', 'loas', 'glaucoma', 'cuidador', 'não consegue se cuidar', 'deficiência']
        for keyword in bpc_keywords:
            if keyword in text:
                scores['bpc']['score'] += 2
                scores['bpc']['keywords'].append(keyword)
        
        # Auxílio-acidente
        acidente_keywords = ['acidente de trabalho', 'acidente laboral', 'ocupacional']
        for keyword in acidente_keywords:
            if keyword in text:
                scores['auxilio_acidente']['score'] += 3
                scores['auxilio_acidente']['keywords'].append(keyword)
        
        # Isenção IR
        ir_keywords = ['câncer', 'neoplasia', 'isenção', 'imposto de renda', 'quimioterapia']
        for keyword in ir_keywords:
            if keyword in text:
                scores['isencao_ir']['score'] += 3
                scores['isencao_ir']['keywords'].append(keyword)
        
        # Auxílio-doença (padrão)
        if 'depressão' in text or 'ansiedade' in text or 'temporário' in text:
            scores['auxilio_doenca']['score'] += 2
        
        return scores
    
    def _determine_main_benefit_simple(self, scores: Dict, text: str) -> str:
        """Determinar benefício principal de forma simples"""
        
        # Prioridades específicas
        if 'isenção' in text and 'imposto' in text:
            return 'isencao-ir'
        
        if 'acidente' in text and 'trabalho' in text:
            return 'auxilio-acidente'
        
        if any(term in text for term in ['glaucoma', 'cuidador', 'não consegue se cuidar']):
            return 'bpc'
        
        # Usar maior pontuação
        max_benefit = max(scores.items(), key=lambda x: x[1]['score'])
        if max_benefit[1]['score'] > 0:
            return max_benefit[0].replace('_', '-')
        
        return 'auxilio-doenca'

    def _detect_specialty_simple(self, text: str) -> str:
        """Detectar especialidade médica de forma abrangente e precisa"""
        
        text_lower = text.lower()
        
        # ESPECIALIDADES MÉDICAS PRINCIPAIS - ORDEM POR PRIORIDADE
        
        # 1. OFTALMOLOGIA
        if any(term in text_lower for term in [
            'glaucoma', 'catarata', 'visão', 'oftalmologia', 'olhos', 'cegueira', 
            'baixa visão', 'retina', 'miopia', 'astigmatismo', 'não consegue ver',
            'perda visual', 'dificuldade para enxergar', 'vista embaçada'
        ]):
            return 'oftalmologia'
        
        # 2. MEDICINA DO TRABALHO / OCUPACIONAL
        elif any(term in text_lower for term in [
            'acidente de trabalho', 'ocupacional', 'laboral', 'trabalho', 'ler/dort',
            'tendinite ocupacional', 'intoxicação ocupacional', 'doença do trabalho',
            'acidente laboral', 'medicina do trabalho', 'perito do trabalho'
        ]):
            return 'medicina_trabalho'
        
        # 3. ONCOLOGIA
        elif any(term in text_lower for term in [
            'câncer', 'tumor', 'oncologia', 'quimioterapia', 'radioterapia', 
            'neoplasia', 'leucemia', 'linfoma', 'metástase', 'carcinoma',
            'sarcoma', 'melanoma', 'tratamento oncológico'
        ]):
            return 'oncologia'
        
        # 4. NEUROLOGIA
        elif any(term in text_lower for term in [
            'alzheimer', 'demência', 'neurologia', 'parkinson', 'esclerose múltipla',
            'epilepsia', 'avc', 'derrame', 'paralisia', 'neuropatia', 'cefaleia',
            'enxaqueca', 'convulsão', 'perda de memória'
        ]):
            return 'neurologia'
        
        # 5. PSIQUIATRIA
        elif any(term in text_lower for term in [
            'depressão', 'ansiedade', 'psiquiatria', 'transtorno bipolar', 
            'esquizofrenia', 'pânico', 'fobia', 'burnout', 'estresse', 
            'transtorno mental', 'saúde mental', 'psicológico'
        ]):
            return 'psiquiatria'
        
        # 6. CARDIOLOGIA
        elif any(term in text_lower for term in [
            'coração', 'cardiologia', 'cardiopatia', 'infarto', 'pressão alta',
            'hipertensão', 'arritmia', 'insuficiência cardíaca', 'angina',
            'marca-passo', 'cirurgia cardíaca', 'cateterismo'
        ]):
            return 'cardiologia'
        
        # 7. ORTOPEDIA
        elif any(term in text_lower for term in [
            'ortopedia', 'fratura', 'osso', 'articulação', 'coluna', 'joelho',
            'ombro', 'punho', 'tornozelo', 'hérnia de disco', 'lombalgia',
            'artrose', 'artrite', 'cirurgia ortopédica', 'prótese'
        ]):
            return 'ortopedia'
        
        # 8. REUMATOLOGIA
        elif any(term in text_lower for term in [
            'reumatologia', 'artrite reumatoide', 'lúpus', 'fibromialgia',
            'artrose', 'gota', 'espondilite', 'dor articular', 'inflamação',
            'autoimune', 'reumatismo'
        ]):
            return 'reumatologia'
        
        # 9. ENDOCRINOLOGIA
        elif any(term in text_lower for term in [
            'diabetes', 'endocrinologia', 'tireoide', 'hormônio', 'insulina',
            'glicose', 'obesidade', 'síndrome metabólica', 'hipotireoidismo'
        ]):
            return 'endocrinologia'
        
        # 10. PNEUMOLOGIA
        elif any(term in text_lower for term in [
            'pneumologia', 'pulmão', 'asma', 'bronquite', 'enfisema',
            'tuberculose', 'falta de ar', 'tosse', 'respiratório'
        ]):
            return 'pneumologia'
        
        # 11. GASTROENTEROLOGIA
        elif any(term in text_lower for term in [
            'gastroenterologia', 'estômago', 'fígado', 'intestino', 'úlcera',
            'hepatite', 'cirrose', 'gastrite', 'refluxo', 'diarreia'
        ]):
            return 'gastroenterologia'
        
        # 12. NEFROLOGIA
        elif any(term in text_lower for term in [
            'nefrologia', 'rim', 'insuficiência renal', 'hemodiálise',
            'transplante renal', 'pedra no rim', 'uremia'
        ]):
            return 'nefrologia'
        
        # 13. GINECOLOGIA
        elif any(term in text_lower for term in [
            'ginecologia', 'útero', 'ovário', 'menstruação', 'gravidez',
            'menopausa', 'câncer de mama', 'histerectomia'
        ]):
            return 'ginecologia'
        
        # 14. DERMATOLOGIA
        elif any(term in text_lower for term in [
            'dermatologia', 'pele', 'melanoma', 'psoríase', 'eczema',
            'dermatite', 'alergia de pele', 'lesão de pele'
        ]):
            return 'dermatologia'
        
        # 15. UROLOGIA
        elif any(term in text_lower for term in [
            'urologia', 'próstata', 'bexiga', 'uretra', 'incontinência',
            'cálculo renal', 'cistite'
        ]):
            return 'urologia'
        
        # DEFAULT: CLÍNICA GERAL
        return 'clinica_geral'