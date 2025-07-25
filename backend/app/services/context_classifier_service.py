import re
from typing import Dict, List, Tuple
from datetime import datetime

class ContextClassifierService:
    """Classificador APRIMORADO para alinhar perfeitamente com LaudoTemplatesExatos"""
    
    def __init__(self):
        # PALAVRAS-CHAVE REFINADAS E EXPANDIDAS
        self.context_keywords = {
            'bpc': [
                # Termos diretos BPC/LOAS
                'bpc', 'beneficio de prestacao continuada', 'loas', 'assistencia social',
                'vida independente', 'cuidador', 'autonomia', 'atividades basicas',
                'higiene pessoal', 'participacao social', 'impedimento longo prazo',
                
                # Indicadores de dependência severa (BPC)
                'nao consegue cuidar', 'precisa de ajuda para tudo', 'dependente para',
                'nao tem como se cuidar', 'sem autonomia', 'nao consegue sozinho',
                'vulnerabilidade social', 'sem renda familiar', 'familia pobre',
                'deficiencia grave', 'limitacao severa', 'incapacidade total',
                
                # Crianças/jovens (BPC específico)
                'crianca', 'menor de idade', 'adolescente', 'desenvolvimento atrasado',
                'necessidades especiais', 'cuidados especiais'
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
                
                # Correlações profissão-limitação
                'profissao exige', 'trabalho requer', 'funcao demanda',
                'atividade profissional', 'capacidade de trabalho',
                'precisao manual', 'esforco fisico', 'concentracao',
                'atender pacientes', 'segurar instrumentos', 'dar aula',
                'dirigir veiculo', 'carregar peso', 'ficar em pe',
                'trabalhar sob pressao', 'tomar decisoes', 'plantao',
                'comunicacao telefonica', 'uso de headset', 'fones de ouvido',
                
                # Especiais para atendimento/telemarketing
                'atendimento ao cliente', 'call center', 'telemarketing',
                'nao consigo escutar cliente', 'nao consigo atender telefone',
                'custom service', 'headset machuca', 'fone de ouvido dói'
            ],
            
            'auxilio_acidente': [
                'auxilio acidente', 'reducao da capacidade', 'acidente de trabalho',
                'sequela', 'incapacidade parcial', 'capacidade reduzida',
                'acidente na fabrica', 'acidente na empresa', 'lesao no trabalho',
                'cat', 'comunicacao de acidente', 'doenca ocupacional',
                'ler dort', 'lesao por esforco repetitivo'
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
    
    def classify_context(self, patient_info: str, transcription: str, documents_text: str = "") -> Dict:
        """Classificação INTELIGENTE refinada para perfeito alinhamento com templates"""
        
        full_text = f"{patient_info} {transcription} {documents_text}".lower()
        
        print(f"🔍 Analisando texto: {full_text[:200]}...")
        
        # 1. DETECTAR ESPECIALIDADE MÉDICA
        detected_specialty = self._detect_medical_specialty(full_text)
        print(f"🏥 Especialidade detectada: {detected_specialty}")
        
        # 2. ANÁLISE BÁSICA COM PALAVRAS-CHAVE
        basic_scores = self._basic_keyword_analysis(full_text)
        print(f"📊 Scores básicos: {basic_scores}")
        
        # 3. ANÁLISE INTELIGENTE DE INCAPACIDADE IMPLÍCITA
        incapacity_analysis = self._analyze_implicit_incapacity(full_text)
        print(f"🧠 Análise incapacidade: {incapacity_analysis}")
        
        # 4. ANÁLISE DE CORRELAÇÃO PROFISSÃO-LIMITAÇÃO
        profession_correlation = self._analyze_profession_limitation(full_text)
        print(f"👔 Correlação profissão: {profession_correlation}")
        
        # 5. ANÁLISE DE GRAVIDADE E DEPENDÊNCIA
        severity_analysis = self._analyze_severity_and_dependency(full_text)
        print(f"⚠️ Análise gravidade: {severity_analysis}")
        
        # 6. ANÁLISE ESPECÍFICA DE CONTEXTO (BPC vs INCAPACIDADE)
        context_specific = self._analyze_specific_context(full_text)
        print(f"🎯 Contexto específico: {context_specific}")
        
        # 7. COMBINAR TODAS AS ANÁLISES
        final_scores = self._combine_all_analyses(
            basic_scores, incapacity_analysis, profession_correlation, 
            severity_analysis, context_specific
        )
        print(f"🔢 Scores finais: {final_scores}")
        
        # 8. DETERMINAR CONTEXTO FINAL COM LÓGICA REFINADA
        main_benefit = self._determine_main_benefit(final_scores, full_text)
        print(f"🎯 Benefício principal: {main_benefit}")
        
        # 9. CRIAR CONTEXTO HÍBRIDO COM ESPECIALIDADE
        if detected_specialty and detected_specialty != 'clinica_geral' and main_benefit != 'clinica':
            hybrid_context = f"{detected_specialty}_{main_benefit}"
        else:
            hybrid_context = main_benefit
        
        return {
            'main_context': hybrid_context,
            'confidence': final_scores.get(main_benefit, {}).get('score', 0),
            'matched_keywords': final_scores.get(main_benefit, {}).get('keywords', []),
            'all_scores': final_scores,
            'detected_specialty': detected_specialty,
            'main_benefit': main_benefit,
            'analysis_details': {
                'basic_scores': basic_scores,
                'incapacity_analysis': incapacity_analysis,
                'profession_correlation': profession_correlation,
                'severity_analysis': severity_analysis,
                'context_specific': context_specific
            }
        }
    
    def _detect_medical_specialty(self, text: str) -> str:
        """Detectar especialidade médica com precisão aprimorada"""
        
        specialty_scores = {}
        
        for specialty, indicators in self.medical_specialties.items():
            score = 0
            matched_terms = []
            
            for indicator in indicators:
                # Busca por termos exatos e variações
                pattern = rf'\b{re.escape(indicator)}\b'
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                
                if matches > 0:
                    # Peso baseado na especificidade e frequência
                    weight = self._calculate_specialty_weight(indicator, specialty)
                    score += matches * weight
                    matched_terms.append(indicator)
            
            if score > 0:
                specialty_scores[specialty] = {
                    'score': score,
                    'terms': matched_terms
                }
        
        if specialty_scores:
            best_specialty = max(specialty_scores.items(), key=lambda x: x[1]['score'])
            print(f"🏥 Especialidade: {best_specialty[0]} (score: {best_specialty[1]['score']}, termos: {best_specialty[1]['terms']})")
            return best_specialty[0]
        
        return 'clinica_geral'
    
    def _calculate_specialty_weight(self, indicator: str, specialty: str) -> float:
        """Calcular peso do indicador por especialidade"""
        
        # Indicadores altamente específicos
        high_specificity = {
            'otorrinolaringologia': ['perda auditiva', 'surdez', 'audiometria'],
            'psiquiatria': ['depressao', 'ansiedade', 'transtorno mental'],
            'cardiologia': ['infarto', 'insuficiencia cardiaca', 'arritmia'],
            'ortopedia': ['hernia disco', 'lombalgia', 'fratura'],
            'oncologia': ['cancer', 'tumor', 'quimioterapia']
        }
        
        if specialty in high_specificity and indicator in high_specificity[specialty]:
            return 5.0
        elif len(indicator.split()) > 2:  # Frases específicas
            return 3.0
        elif len(indicator.split()) == 2:  # Termos compostos
            return 2.0
        else:  # Termos simples
            return 1.0
    
    def _basic_keyword_analysis(self, text: str) -> Dict:
        """Análise básica refinada com pesos inteligentes"""
        
        context_scores = {}
        
        for context_type, keywords in self.context_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                # Busca por termos exatos
                pattern = rf'\b{re.escape(keyword)}\b'
                count = len(re.findall(pattern, text, re.IGNORECASE))
                
                if count > 0:
                    weight = self._get_keyword_weight(context_type, keyword)
                    score += count * weight
                    matched_keywords.append(f"{keyword} (x{count})")
            
            context_scores[context_type] = {
                'score': score,
                'keywords': matched_keywords
            }
        
        return context_scores
    
    def _analyze_implicit_incapacity(self, text: str) -> Dict:
        """Detectar indicadores IMPLÍCITOS refinados de incapacidade"""
        
        incapacity_score = 0
        matched_patterns = []
        
        # PADRÕES DE INCAPACIDADE REFINADOS
        patterns = [
            # Impossibilidade explícita (peso alto)
            (r'n[ãa]o consigo mais (\w+)', 4.0, "Impossibilidade explícita"),
            (r'n[ãa]o posso mais (\w+)', 4.0, "Impossibilidade explícita"),
            (r'impossível (\w+)', 4.0, "Impossibilidade declarada"),
            
            # Incompatibilidade profissional (peso muito alto)
            (r'profiss[ãa]o exige.*n[ãa]o (tenho|consigo|posso)', 5.0, "Incompatibilidade profissional"),
            (r'trabalho requer.*n[ãa]o (tenho|consigo|posso)', 5.0, "Incompatibilidade profissional"),
            (r'fun[çc][ãa]o demanda.*n[ãa]o (tenho|consigo|posso)', 5.0, "Incompatibilidade profissional"),
            
            # Limitações funcionais específicas
            (r'precis[ãa]o manual.*n[ãa]o tenho', 4.0, "Limitação manual específica"),
            (r'esfor[çc]o f[íi]sico.*n[ãa]o aguento', 4.0, "Limitação física"),
            (r'concentra[çc][ãa]o.*n[ãa]o consigo', 3.5, "Limitação cognitiva"),
            (r'comunica[çc][ãa]o.*n[ãa]o consigo', 4.0, "Limitação comunicativa"),
            
            # Específico para atendimento/telemarketing
            (r'atender.*telefone.*n[ãa]o consigo', 4.5, "Incapacidade para atendimento"),
            (r'headset.*n[ãa]o (aguento|consigo|posso)', 4.0, "Incapacidade para equipamentos"),
            (r'fone.*ouvido.*n[ãa]o (aguento|consigo|posso)', 4.0, "Incapacidade auditiva laboral"),
            (r'escutar.*cliente.*n[ãa]o consigo', 4.5, "Incapacidade comunicativa laboral"),
            
            # Atividades profissionais específicas
            (r'atender pacientes.*n[ãa]o consigo', 3.5, "Incapacidade assistencial"),
            (r'segurar instrumentos.*n[ãa]o consigo', 4.0, "Incapacidade instrumental"),
            (r'dirigir.*n[ãa]o posso', 3.5, "Incapacidade para condução"),
            (r'dar aula.*n[ãa]o consigo', 3.5, "Incapacidade docente"),
            (r'carregar peso.*n[ãa]o (aguento|consigo)', 3.5, "Incapacidade física"),
            
            # Indicadores de intensidade
            (r'n[ãa]o aguento mais', 3.0, "Limitação por intolerância"),
            (r'muito dif[íi]cil', 2.0, "Dificuldade severa"),
            (r'quase impossível', 3.0, "Limitação quase total")
        ]
        
        for pattern, weight, description in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                incapacity_score += weight * len(matches)
                matched_patterns.append(f"{description}: {matches[0] if matches else 'detectado'}")
        
        return {
            'incapacidade': {
                'score': incapacity_score,
                'keywords': matched_patterns
            }
        }
    
    def _analyze_profession_limitation(self, text: str) -> Dict:
        """Analisar correlação profissão-limitação refinada"""
        
        profession_score = 0
        correlations = []
        
        # DETECTAR PROFISSÃO com mais precisão
        detected_profession = None
        profession_confidence = 0
        
        for profession in self.profession_limitations.keys():
            if profession in text:
                # Verificar contexto da menção da profissão
                profession_patterns = [
                    rf'sou {profession}',
                    rf'trabalho como {profession}',
                    rf'profiss[ãa]o.*{profession}',
                    rf'{profession}.*profiss[ãa]o'
                ]
                
                for pattern in profession_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        detected_profession = profession
                        profession_confidence = 3.0
                        break
                
                if not detected_profession:
                    detected_profession = profession
                    profession_confidence = 1.0
                break
        
        if detected_profession:
            limitations = self.profession_limitations[detected_profession]
            
            # VERIFICAR LIMITAÇÕES ESPECÍFICAS DA PROFISSÃO
            for limitation in limitations:
                limitation_patterns = [
                    rf'n[ãa]o consigo.*{limitation}',
                    rf'n[ãa]o posso.*{limitation}',
                    rf'{limitation}.*comprometid[oa]',
                    rf'{limitation}.*dificuldade',
                    rf'{limitation}.*limitad[oa]',
                    rf'{limitation}.*impossível',
                    rf'problema.*{limitation}'
                ]
                
                for pattern in limitation_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        profession_score += 3.0 * profession_confidence
                        correlations.append(f"{detected_profession} → limitação em {limitation}")
                        break
        
        return {
            'incapacidade': {
                'score': profession_score,
                'keywords': correlations
            }
        }
    
    def _analyze_severity_and_dependency(self, text: str) -> Dict:
        """Analisar gravidade e dependência para BPC vs Incapacidade"""
        
        severity_scores = {
            'bpc': {'score': 0, 'keywords': []},
            'incapacidade': {'score': 0, 'keywords': []}
        }
        
        for benefit_type, indicators in self.severity_indicators.items():
            for indicator in indicators:
                if indicator in text:
                    weight = 3.0 if benefit_type == 'bpc' else 2.0
                    severity_scores[benefit_type]['score'] += weight
                    severity_scores[benefit_type]['keywords'].append(indicator)
        
        return severity_scores
    
    def _analyze_specific_context(self, text: str) -> Dict:
        """Análise específica de contexto BPC vs Incapacidade"""
        
        context_scores = {
            'bpc': {'score': 0, 'keywords': []},
            'incapacidade': {'score': 0, 'keywords': []}
        }
        
        # INDICADORES ESPECÍFICOS DE BPC
        bpc_indicators = [
            'vida independente', 'atividades básicas', 'cuidador',
            'dependente para', 'sem autonomia', 'participação social',
            'impedimento longo prazo', 'deficiência', 'limitação severa'
        ]
        
        # INDICADORES ESPECÍFICOS DE INCAPACIDADE LABORAL
        incapacity_indicators = [
            'trabalho', 'profissão', 'atividade laboral', 'função',
            'emprego', 'serviço', 'ocupação', 'carreira',
            'afastamento', 'licença', 'inss', 'previdência'
        ]
        
        for indicator in bpc_indicators:
            if indicator in text:
                context_scores['bpc']['score'] += 2.0
                context_scores['bpc']['keywords'].append(indicator)
        
        for indicator in incapacity_indicators:
            if indicator in text:
                context_scores['incapacidade']['score'] += 1.5
                context_scores['incapacidade']['keywords'].append(indicator)
        
        return context_scores
    
    def _combine_all_analyses(self, basic: Dict, incapacity: Dict, profession: Dict, 
                            severity: Dict, context_specific: Dict) -> Dict:
        """Combinar todas as análises com pesos balanceados"""
        
        final_scores = {}
        
        # INICIALIZAR COM ANÁLISE BÁSICA
        for context in basic:
            final_scores[context] = {
                'score': basic[context]['score'],
                'keywords': basic[context]['keywords'].copy()
            }
        
        # ADICIONAR ANÁLISE DE INCAPACIDADE IMPLÍCITA
        for context in incapacity:
            if context in final_scores:
                final_scores[context]['score'] += incapacity[context]['score']
                final_scores[context]['keywords'].extend(incapacity[context]['keywords'])
            else:
                final_scores[context] = incapacity[context].copy()
        
        # ADICIONAR ANÁLISE DE PROFISSÃO
        for context in profession:
            if context in final_scores:
                final_scores[context]['score'] += profession[context]['score']
                final_scores[context]['keywords'].extend(profession[context]['keywords'])
        
        # ADICIONAR ANÁLISE DE GRAVIDADE
        for context in severity:
            if context in final_scores:
                final_scores[context]['score'] += severity[context]['score']
                final_scores[context]['keywords'].extend(severity[context]['keywords'])
            elif severity[context]['score'] > 0:
                final_scores[context] = severity[context].copy()
        
        # ADICIONAR ANÁLISE DE CONTEXTO ESPECÍFICO
        for context in context_specific:
            if context in final_scores:
                final_scores[context]['score'] += context_specific[context]['score']
                final_scores[context]['keywords'].extend(context_specific[context]['keywords'])
            elif context_specific[context]['score'] > 0:
                final_scores[context] = context_specific[context].copy()
        
        return final_scores
    
    def _determine_main_benefit(self, final_scores: Dict, text: str) -> str:
        """Determinar benefício principal com lógica refinada"""
        
        # LÓGICA DE PRIORIZAÇÃO INTELIGENTE
        
        # 1. Se há menção explícita de benefício específico
        explicit_mentions = {
            'bpc': r'\b(bpc|loas|beneficio.*prestacao.*continuada)\b',
            'auxilio_acidente': r'\b(auxilio.*acidente|acidente.*trabalho)\b',
            'isencao_ir': r'\b(isencao.*imposto|receita.*federal)\b',
            'incapacidade': r'\b(auxilio.*doenca|aposentadoria.*invalidez|incapacidade.*laboral)\b'
        }
        
        for benefit, pattern in explicit_mentions.items():
            if re.search(pattern, text, re.IGNORECASE):
                print(f"🎯 Menção explícita de {benefit} detectada")
                if benefit in final_scores:
                    final_scores[benefit]['score'] += 5.0  # Boost por menção explícita
                else:
                    final_scores[benefit] = {'score': 5.0, 'keywords': ['menção explícita']}
        
        # 2. Filtrar scores muito baixos
        significant_scores = {k: v for k, v in final_scores.items() 
                            if v['score'] >= 1.0}
        
        if not significant_scores:
            return 'clinica'
        
        # 3. Aplicar lógica de diferenciação BPC vs INCAPACIDADE
        if 'bpc' in significant_scores and 'incapacidade' in significant_scores:
            bpc_score = significant_scores['bpc']['score']
            incap_score = significant_scores['incapacidade']['score']
            
            # Fatores de diferenciação
            dependency_factors = [
                'dependente para', 'cuidador', 'sem autonomia', 
                'vida independente', 'atividades básicas'
            ]
            
            work_factors = [
                'trabalho', 'profissão', 'emprego', 'função',
                'atividade laboral', 'ocupação'
            ]
            
            dependency_count = sum(1 for factor in dependency_factors if factor in text)
            work_count = sum(1 for factor in work_factors if factor in text)
            
            # Se há mais indicadores de dependência severa → BPC
            if dependency_count > work_count and dependency_count >= 2:
                significant_scores['bpc']['score'] += 3.0
                print(f"🔍 Boost BPC por indicadores de dependência ({dependency_count})")
            
            # Se há mais indicadores de trabalho → INCAPACIDADE
            elif work_count > dependency_count and work_count >= 2:
                significant_scores['incapacidade']['score'] += 3.0
                print(f"🔍 Boost INCAPACIDADE por indicadores laborais ({work_count})")
        
        # 4. Detectar idade para BPC infantil
        idade_match = re.search(r'(\d+)\s+anos?', text)
        if idade_match:
            idade = int(idade_match.group(1))
            if idade < 18 and 'bpc' in significant_scores:
                significant_scores['bpc']['score'] += 2.0
                print(f"🔍 Boost BPC por idade infantil ({idade} anos)")
        
        # 5. Retornar benefício com maior score
        main_benefit = max(significant_scores, key=lambda x: significant_scores[x]['score'])
        
        print(f"🎯 Benefício determinado: {main_benefit} (score: {significant_scores[main_benefit]['score']})")
        return main_benefit
    
    def _get_keyword_weight(self, context_type: str, keyword: str) -> float:
        """Pesos refinados para palavras-chave por contexto"""
        
        # PESOS MUITO ALTOS (5.0) - Indicadores definitivos
        very_high_weight = {
            'incapacidade': [
                'nao consigo mais trabalhar', 'impossivel trabalhar', 
                'incapaz de trabalhar', 'profissao exige', 'trabalho requer',
                'auxilio doenca', 'aposentadoria por invalidez'
            ],
            'bpc': [
                'bpc', 'loas', 'beneficio de prestacao continuada',
                'vida independente', 'impedimento longo prazo'
            ],
            'auxilio_acidente': [
                'auxilio acidente', 'acidente de trabalho'
            ],
            'isencao_ir': [
                'isencao', 'imposto de renda', 'doenca grave'
            ]
        }
        
        # PESOS ALTOS (3.0) - Indicadores importantes
        high_weight = {
            'incapacidade': [
                'incapacidade laboral', 'nao consigo mais atender',
                'nao consigo mais seguir', 'limitacao para trabalhar',
                'comunicacao telefonica', 'uso de headset', 'atendimento cliente'
            ],
            'bpc': [
                'cuidador', 'dependente para', 'sem autonomia',
                'atividades basicas', 'participacao social'
            ]
        }
        
        # PESOS MÉDIOS (2.0) - Indicadores relevantes
        medium_weight = {
            'incapacidade': [
                'nao consigo concentrar', 'dificuldade para trabalhar',
                'precisao manual', 'esforco fisico'
            ],
            'bpc': [
                'limitacao severa', 'necessidades especiais'
            ]
        }
        
        # PESOS BAIXOS (0.5) - Indicadores fracos
        low_weight = {
            'clinica': ['sintomas', 'dor', 'medicacao', 'tratamento']
        }
        
        # Verificar em ordem de prioridade
        for weight_dict, weight_value in [
            (very_high_weight, 5.0),
            (high_weight, 3.0), 
            (medium_weight, 2.0),
            (low_weight, 0.5)
        ]:
            if context_type in weight_dict and keyword in weight_dict[context_type]:
                return weight_value
        
        # Peso padrão
        return 1.0
    
    def get_specialized_prompt(self, context_type: str, patient_info: str, transcription: str) -> Dict:
        """Prompts especializados alinhados com templates"""
        
        prompts = {
            'bpc': {
                'anamnese_prompt': f"""
GERAR ANAMNESE PARA BPC/LOAS seguindo EXATAMENTE o padrão de 7 pontos:

DADOS DO PACIENTE: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

Estruturar conforme padrão BPC/LOAS com foco em:
- Impedimento de longo prazo
- Limitações para vida independente  
- Necessidade de cuidador
- Participação social comprometida
- Atividades básicas de vida diária

Usar especialidade médica detectada e correlacionar com limitações funcionais.
""",
                'laudo_prompt': f"""
GERAR LAUDO PARA BPC/LOAS seguindo EXATAMENTE o padrão de 6 pontos:

DADOS DO PACIENTE: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

CONCLUSÃO deve ser FAVORÁVEL ao BPC com:
- Impedimento de longo prazo confirmado
- Natureza do impedimento (física/mental/sensorial)
- Restrição para vida independente
- Critérios legais atendidos
"""
            },
            'incapacidade': {
                'anamnese_prompt': f"""
GERAR ANAMNESE PARA INCAPACIDADE LABORAL seguindo EXATAMENTE o padrão de 7 pontos:

DADOS DO PACIENTE: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

Estruturar com foco em:
- Correlação entre limitações clínicas e incapacidade profissional
- Impossibilidade para atividade habitual
- Justificativa técnica profissão x limitação
- Histórico ocupacional detalhado

Usar especialidade médica detectada e correlacionar com profissão específica.
""",
                'laudo_prompt': f"""
GERAR LAUDO PARA INCAPACIDADE LABORAL seguindo EXATAMENTE o padrão de 6 pontos:

DADOS DO PACIENTE: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

CONCLUSÃO deve ser FAVORÁVEL à incapacidade com:
- Incapacidade para atividade habitual confirmada
- Justificativa técnica profissão x limitação
- Avaliação médica fundamentada
- Recomendação de afastamento
"""
            },
            'auxilio_acidente': {
                'anamnese_prompt': f"""
⚠️ ATENÇÃO CFM: Avaliação trabalhista requer critérios específicos

GERAR ANAMNESE PARA AUXÍLIO-ACIDENTE seguindo padrão de 7 pontos:

DADOS DO PACIENTE: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

OBSERVAÇÃO: Limitação de telemedicina para avaliação trabalhista
""",
                'laudo_prompt': f"""
⚠️ LIMITAÇÃO CFM: Avaliação trabalhista requer critérios específicos

GERAR LAUDO PARA AUXÍLIO-ACIDENTE seguindo padrão de 6 pontos:

DADOS DO PACIENTE: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

CONCLUSÃO: Redução de capacidade conforme critérios médicos
"""
            },
            'isencao_ir': {
                'anamnese_prompt': f"""
GERAR ANAMNESE PARA ISENÇÃO IR seguindo padrão de 7 pontos:

DADOS DO PACIENTE: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

Foco em doença grave conforme Lei 7.713/88
""",
                'laudo_prompt': f"""
GERAR LAUDO PARA ISENÇÃO IR seguindo padrão de 6 pontos:

DADOS DO PACIENTE: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

CONCLUSÃO: Doença grave enquadrada na legislação
"""
            },
            'clinica': {
                'anamnese_prompt': f"""
GERAR ANAMNESE CLÍNICA seguindo padrão de 7 pontos:

DADOS DO PACIENTE: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

Estrutura clínica geral sem foco previdenciário
""",
                'laudo_prompt': f"""
GERAR RELATÓRIO MÉDICO CLÍNICO seguindo padrão de 6 pontos:

DADOS DO PACIENTE: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

Relatório clínico sem finalidade previdenciária
"""
            }
        }
        
        # CONTEXTOS HÍBRIDOS (especialidade + benefício)
        if '_' in context_type:
            specialty, benefit = context_type.split('_')
            base_prompts = prompts.get(benefit, prompts['clinica'])
            
            # Personalizar prompts para especialidade
            specialty_focus = {
                'otorrinolaringologia': 'Foco em limitações auditivas e comunicativas',
                'psiquiatria': 'Foco em limitações psíquicas e cognitivas', 
                'cardiologia': 'Foco em limitações cardiovasculares e esforço físico',
                'ortopedia': 'Foco em limitações motoras e esforço físico',
                'neurologia': 'Foco em limitações neurológicas e cognitivas',
                'reumatologia': 'Foco em limitações articulares e motoras',
                'oncologia': 'Foco em limitações por doença grave'
            }
            
            if specialty in specialty_focus:
                focus_text = f"\n\nESPECIALIDADE: {specialty.upper()}\n{specialty_focus[specialty]}"
                base_prompts['anamnese_prompt'] += focus_text
                base_prompts['laudo_prompt'] += focus_text
            
            return base_prompts
        
        return prompts.get(context_type, prompts['clinica'])
    
    def validate_classification(self, classification_result: Dict, patient_info: str, transcription: str) -> Dict:
        """Validar e refinar classificação final"""
        
        main_benefit = classification_result['main_benefit']
        confidence = classification_result['confidence']
        
        # VALIDAÇÕES DE QUALIDADE
        validation_issues = []
        
        # 1. Verificar se há informações suficientes
        text_length = len(f"{patient_info} {transcription}")
        if text_length < 100:
            validation_issues.append("Texto muito curto para classificação precisa")
            confidence *= 0.7
        
        # 2. Verificar consistência profissão x benefício
        full_text = f"{patient_info} {transcription}".lower()
        detected_professions = [prof for prof in self.profession_limitations.keys() if prof in full_text]
        
        if detected_professions and main_benefit == 'bpc':
            validation_issues.append("Possível inconsistência: profissão detectada com BPC")
            confidence *= 0.8
        
        # 3. Verificar idade x benefício
        idade_match = re.search(r'(\d+)\s+anos?', full_text)
        if idade_match:
            idade = int(idade_match.group(1))
            if idade > 65 and main_benefit == 'incapacidade':
                validation_issues.append("Possível inconsistência: idade avançada com incapacidade laboral")
                confidence *= 0.9
        
        # 4. Ajustar confiança final
        if confidence > 10.0:
            confidence = min(confidence, 10.0)  # Normalizar
        
        confidence_level = "ALTA" if confidence >= 7.0 else "MÉDIA" if confidence >= 4.0 else "BAIXA"
        
        return {
            **classification_result,
            'confidence': confidence,
            'confidence_level': confidence_level,
            'validation_issues': validation_issues,
            'recommendation': self._get_classification_recommendation(main_benefit, confidence_level, validation_issues)
        }
    
    def _get_classification_recommendation(self, benefit: str, confidence_level: str, issues: List[str]) -> str:
        """Gerar recomendação baseada na classificação"""
        
        if confidence_level == "ALTA":
            return f"Classificação confiável para {benefit.upper()}. Prosseguir com geração de documentos."
        
        elif confidence_level == "MÉDIA":
            return f"Classificação moderada para {benefit.upper()}. Revisar contexto antes de gerar documentos."
        
        else:
            issues_text = "; ".join(issues) if issues else "Informações insuficientes"
            return f"Classificação incerta. Problemas: {issues_text}. Recomenda-se coleta de mais informações."

# Instância global refinada
context_classifier = ContextClassifierService()