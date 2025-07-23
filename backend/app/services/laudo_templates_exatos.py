from datetime import datetime
from typing import Dict, Any, List
import re

class LaudoTemplatesExatos:
    """Templates seguindo EXATAMENTE o padrão dos 7 pontos (anamnese) e 6 pontos (laudo) com benefícios"""
    
    def __init__(self):
        self.natureza_impedimento = {
            "psiquiatria": "mental",
            "neurologia": "física/mental", 
            "oftalmologia": "sensorial",
            "cardiologia": "física",
            "ortopedia": "física",
            "oncologia": "física",
            "endocrinologia": "física",
            "reumatologia": "física",
            "pneumologia": "física",
            "nefrologia": "física",
            "clinica_geral": "física",
            "otorrinolaringologia": "sensorial"
        }
        
        self.justificativas_profissionais = {
            "professora": "Os sintomas psiquiátricos impedem a concentração, interação com alunos e controle emocional necessários ao magistério",
            "professor": "Os sintomas psiquiátricos impedem a concentração, interação com alunos e controle emocional necessários ao magistério",
            "motorista": "As limitações cardiovasculares impedem esforços físicos e concentração necessários à condução segura",
            "pedreiro": "As limitações ortopédicas impedem levantamento de peso, trabalho em altura e esforços físicos da construção civil",
            "enfermeira": "As limitações funcionais impedem plantões, cuidados diretos ao paciente e tomada de decisões em situações críticas",
            "enfermeiro": "As limitações funcionais impedem plantões, cuidados diretos ao paciente e tomada de decisões em situações críticas",
            "dentista": "Os sintomas impedem a concentração necessária para procedimentos odontológicos, controle motor fino e interação com pacientes",
            # PROFISSÕES DE ATENDIMENTO E COMUNICAÇÃO:
            "atendente": "As limitações auditivas impedem a comunicação telefônica eficaz, comprometem a compreensão de solicitações e impossibilitam o uso adequado de equipamentos de áudio",
            "telemarketing": "As limitações auditivas impedem a comunicação telefônica eficaz, comprometem a compreensão de solicitações e impossibilitam o uso adequado de equipamentos de áudio",
            "operador": "As limitações auditivas impedem a comunicação telefônica eficaz, comprometem a compreensão de solicitações e impossibilitam o uso adequado de equipamentos de áudio",
            "operadora": "As limitações auditivas impedem a comunicação telefônica eficaz, comprometem a compreensão de solicitações e impossibilitam o uso adequado de equipamentos de áudio",
            "recepcionista": "As limitações auditivas impedem a comunicação telefônica eficaz, o atendimento ao público e o uso de equipamentos de comunicação",
            "secretária": "As limitações funcionais impedem atividades administrativas, comunicação telefônica e uso prolongado de equipamentos",
            "secretario": "As limitações funcionais impedem atividades administrativas, comunicação telefônica e uso prolongado de equipamentos",
            # PROFISSÕES COMERCIAIS:
            "vendedor": "As limitações funcionais impedem a comunicação eficaz com clientes, concentração prolongada e esforços físicos exigidos pela função",
            "vendedora": "As limitações funcionais impedem a comunicação eficaz com clientes, concentração prolongada e esforços físicos exigidos pela função",
            "caixa": "As limitações funcionais impedem o atendimento ao público, permanência em pé por longos períodos e concentração necessária ao trabalho",
            "promotor": "As limitações funcionais impedem a comunicação eficaz, esforços físicos e concentração prolongada exigidos pela atividade promocional",
            "promotora": "As limitações funcionais impedem a comunicação eficaz, esforços físicos e concentração prolongada exigidos pela atividade promocional",
            # PROFISSÕES TÉCNICAS:
            "técnico": "As limitações funcionais impedem atividades técnicas especializadas, concentração prolongada e uso de equipamentos específicos",
            "técnica": "As limitações funcionais impedem atividades técnicas especializadas, concentração prolongada e uso de equipamentos específicos",
            "analista": "As limitações funcionais impedem análises complexas, concentração prolongada e uso intensivo de computadores",
            "assistente": "As limitações funcionais impedem atividades de apoio, comunicação eficaz e uso de equipamentos administrativos",
            "auxiliar": "As limitações funcionais impedem atividades auxiliares, esforços físicos e concentração necessária ao trabalho",
            # PROFISSÕES DE SERVIÇOS:
            "faxineiro": "As limitações ortopédicas impedem esforços físicos intensos, levantamento de peso e movimentos repetitivos exigidos pela limpeza",
            "faxineira": "As limitações ortopédicas impedem esforços físicos intensos, levantamento de peso e movimentos repetitivos exigidos pela limpeza",
            "porteiro": "As limitações funcionais impedem vigilância prolongada, comunicação eficaz e esforços físicos necessários à segurança",
            "porteira": "As limitações funcionais impedem vigilância prolongada, comunicação eficaz e esforços físicos necessários à segurança",
            "segurança": "As limitações funcionais impedem vigilância constante, reflexos rápidos e esforços físicos exigidos pela segurança",
            "vigilante": "As limitações funcionais impedem vigilância prolongada, atenção constante e capacidade de resposta rápida",
            # PROFISSÕES INDUSTRIAIS:
            "operário": "As limitações ortopédicas impedem esforços físicos intensos, levantamento de peso e trabalho em linha de produção",
            "operária": "As limitações ortopédicas impedem esforços físicos intensos, levantamento de peso e trabalho em linha de produção",
            "soldador": "As limitações funcionais impedem concentração visual, controle motor fino e tolerância a ambientes industriais",
            "soldadora": "As limitações funcionais impedem concentração visual, controle motor fino e tolerância a ambientes industriais",
            "mecânico": "As limitações ortopédicas impedem esforços físicos, uso de ferramentas e trabalho em posições inadequadas",
            "mecânica": "As limitações ortopédicas impedem esforços físicos, uso de ferramentas e trabalho em posições inadequadas",
            # PROFISSÕES DE SAÚDE:
            "médico": "As limitações funcionais impedem diagnósticos precisos, procedimentos médicos e tomada de decisões críticas",
            "médica": "As limitações funcionais impedem diagnósticos precisos, procedimentos médicos e tomada de decisões críticas",
            "fisioterapeuta": "As limitações ortopédicas impedem procedimentos fisioterápicos, esforços físicos e manipulação adequada de pacientes",
            "psicólogo": "As limitações psiquiátricas impedem avaliação mental adequada, concentração prolongada e interação terapêutica",
            "psicóloga": "As limitações psiquiátricas impedem avaliação mental adequada, concentração prolongada e interação terapêutica",
            # PROFISSÕES EDUCACIONAIS:
            "pedagogo": "As limitações funcionais impedem atividades pedagógicas, concentração prolongada e interação adequada com estudantes",
            "pedagoga": "As limitações funcionais impedem atividades pedagógicas, concentração prolongada e interação adequada com estudantes",
            "coordenador": "As limitações funcionais impedem coordenação de equipes, tomada de decisões e comunicação eficaz",
            "coordenadora": "As limitações funcionais impedem coordenação de equipes, tomada de decisões e comunicação eficaz",
            # PROFISSÕES JURÍDICAS:
            "advogado": "As limitações funcionais impedem análise jurídica complexa, concentração prolongada e comunicação eficaz em tribunais",
            "advogada": "As limitações funcionais impedem análise jurídica complexa, concentração prolongada e comunicação eficaz em tribunais",
            "juiz": "As limitações funcionais impedem análise judicial complexa, concentração prolongada e tomada de decisões críticas",
            "juíza": "As limitações funcionais impedem análise judicial complexa, concentração prolongada e tomada de decisões críticas",
            # PROFISSÕES CONTÁBEIS:
            "contador": "As limitações funcionais impedem cálculos complexos, concentração prolongada e uso intensivo de sistemas contábeis",
            "contadora": "As limitações funcionais impedem cálculos complexos, concentração prolongada e uso intensivo de sistemas contábeis",
            # PROFISSÕES DE ENGENHARIA:
            "engenheiro": "As limitações funcionais impedem análises técnicas complexas, concentração prolongada e tomada de decisões de engenharia",
            "engenheira": "As limitações funcionais impedem análises técnicas complexas, concentração prolongada e tomada de decisões de engenharia",
            # PROFISSÕES CULINÁRIAS:
            "cozinheiro": "As limitações funcionais impedem atividades culinárias, esforços físicos e permanência prolongada em pé",
            "cozinheira": "As limitações funcionais impedem atividades culinárias, esforços físicos e permanência prolongada em pé",
            "garçom": "As limitações funcionais impedem atendimento ao público, esforços físicos e comunicação eficaz",
            "garçonete": "As limitações funcionais impedem atendimento ao público, esforços físicos e comunicação eficaz",
            # DEFAULT:
            "default": "As limitações atuais impedem o adequado desempenho das funções profissionais habituais"
        }
    
    # ===== GERAÇÃO DE ANAMNESE - 7 PONTOS =====
    
    def gerar_anamnese_completa(self, dados: Dict[str, Any]) -> str:
        """Gerar anamnese seguindo modelo EXATO dos 7 pontos obrigatórios"""
        
        especialidade = dados.get('especialidade', 'clínica geral')
        beneficio = dados.get('beneficio', 'incapacidade')
        patient_info = dados.get('patient_info', '')
        transcription = dados.get('transcription', '')
        
        info = self._extrair_informacoes(patient_info, transcription)
        
        anamnese_template = f"""
ANAMNESE PARA {beneficio.upper()} - MODALIDADE: TELEMEDICINA

1. IDENTIFICAÇÃO DO PACIENTE
- Nome: {info.get('nome', 'Não informado')}
- Idade: {info.get('idade', 'Não informado')} anos
- Sexo: {info.get('sexo', 'Não informado')}
- Profissão: {info.get('profissao', 'Não relatado')}
- Documento de identificação (RG/CPF): {info.get('documento', 'Não apresentado')}
- Número de processo ou referência: {info.get('processo', 'Não aplicável')}

2. QUEIXA PRINCIPAL
- Motivo da consulta: {self._get_motivo_consulta(beneficio)}
- Solicitação específica: {info.get('queixa_principal', 'Avaliação médica para fins previdenciários')}
- Solicitação do advogado: {info.get('advogado', 'Não informada')}

3. HISTÓRIA DA DOENÇA ATUAL (HDA)
- Data de início dos sintomas e/ou diagnóstico: {info.get('data_inicio', 'Não especificada')}
- Fatores desencadeantes ou agravantes: {self._get_fatores_desencadeantes_correto(especialidade, transcription)}
- Tratamentos realizados e resultados: {self._get_tratamentos_realizados(transcription)}
- Situação atual: {self._get_situacao_atual_detalhada(especialidade, beneficio, transcription)}

4. ANTECEDENTES PESSOAIS E FAMILIARES RELEVANTES
- Doenças prévias: {self._extrair_antecedentes(transcription)}
- Histórico ocupacional e previdenciário: {self._get_historico_ocupacional_detalhado(transcription, info.get('profissao'))}
- Histórico familiar: {info.get('historico_familiar', 'Não relatado')}

5. DOCUMENTAÇÃO APRESENTADA
- Exames complementares, relatórios, prontuários: {self._get_documentacao_apresentada(transcription)}
- Observação: {self._get_observacao_documentos(transcription)}

6. EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)
- Relato de autoavaliação guiada: {self._get_autoavaliacao_detalhada(especialidade, transcription)}
- Observação visual por vídeo: {self._get_observacao_video(transcription)}
- Limitações funcionais observadas ou relatadas: {self._get_limitacoes_funcionais_detalhadas(especialidade, beneficio, transcription)}

7. AVALIAÇÃO MÉDICA (ASSESSMENT)
- Hipótese diagnóstica: {self._get_hipotese_diagnostica_detalhada(especialidade, transcription)}
- CID-10: {info.get('cid', self._sugerir_cid_baseado_transcricao(especialidade, transcription))}

MODALIDADE: Teleconsulta para avaliação de {beneficio}
ESPECIALIDADE: {especialidade.title()}
DATA: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
"""
        
        return anamnese_template
    
    # ===== GERAÇÃO DE LAUDO - 6 PONTOS COM BENEFÍCIOS =====
    
    def gerar_laudo_completo(self, dados: Dict[str, Any]) -> str:
        """Gerar laudo seguindo EXATAMENTE os 6 pontos com conclusão alinhada ao benefício"""
        
        especialidade = dados.get('especialidade', 'clínica geral')
        beneficio = dados.get('beneficio', 'incapacidade')
        patient_info = dados.get('patient_info', '')
        transcription = dados.get('transcription', '')
        
        info = self._extrair_informacoes(patient_info, transcription)
        
        # MOSTRAR CLARAMENTE O BENEFÍCIO NO CABEÇALHO
        finalidade_beneficio = self._get_finalidade_com_beneficio(beneficio)
        
        laudo_template = f"""
LAUDO MÉDICO {finalidade_beneficio}

IDENTIFICAÇÃO
- Paciente: {info.get('nome', 'Não informado')}
- Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
- Modalidade: Teleconsulta {especialidade.title()}
- Finalidade: {self._get_tipo_beneficio_detalhado(beneficio)}
- Benefício Solicitado: {beneficio.upper()}

1. HISTÓRIA CLÍNICA
{self._gerar_historia_clinica_detalhada(info, especialidade, transcription)}

2. LIMITAÇÃO FUNCIONAL
{self._gerar_limitacao_funcional_detalhada(info, beneficio, especialidade, transcription)}

3. EXAMES (QUANDO HOUVER)
{self._gerar_secao_exames_detalhada(transcription)}

4. TRATAMENTO
{self._gerar_secao_tratamento_detalhada(info, especialidade, transcription)}

5. PROGNÓSTICO
{self._gerar_prognostico_detalhado(info, especialidade, beneficio, transcription)}

6. CONCLUSÃO – ALINHADA AO BENEFÍCIO

CID-10: {self._sugerir_cid_baseado_transcricao(especialidade, transcription)}

{self._gerar_conclusao_beneficio_especifica(info, beneficio, especialidade, transcription)}

Médico Responsável: ________________________
CRM: ________________________
Especialidade: {especialidade.title()}
Data: {datetime.now().strftime('%d/%m/%Y')}
"""
        
        return laudo_template
    
    # ===== MÉTODOS PARA BENEFÍCIOS ESPECÍFICOS =====
    
    def _get_finalidade_com_beneficio(self, beneficio: str) -> str:
        """Finalidade clara mostrando o benefício"""
        finalidades = {
            "bpc": "PARA BENEFÍCIO DE PRESTAÇÃO CONTINUADA (BPC/LOAS)",
            "incapacidade": "PARA BENEFÍCIO POR INCAPACIDADE LABORATIVA",
            "auxilio_acidente": "PARA AUXÍLIO-ACIDENTE PREVIDENCIÁRIO",
            "isencao_ir": "PARA ISENÇÃO DE IMPOSTO DE RENDA POR DOENÇA GRAVE",
            "pericia": "PERICIAL"
        }
        return finalidades.get(beneficio, "MÉDICO")

    def _get_tipo_beneficio_detalhado(self, beneficio: str) -> str:
        """Tipo de benefício detalhado"""
        tipos = {
            "bpc": "Benefício de Prestação Continuada (BPC/LOAS) - Avaliação de impedimento de longo prazo",
            "incapacidade": "Auxílio-doença/Aposentadoria por invalidez - Avaliação de incapacidade laborativa", 
            "auxilio_acidente": "Auxílio-acidente previdenciário - Avaliação de redução da capacidade laborativa",
            "isencao_ir": "Isenção de Imposto de Renda - Comprovação de doença grave",
            "pericia": "Perícia médica judicial ou administrativa"
        }
        return tipos.get(beneficio, "Avaliação médica especializada")

    def _gerar_conclusao_beneficio_especifica(self, info: Dict, beneficio: str, especialidade: str, transcription: str) -> str:
        """Conclusão ESPECÍFICA para cada tipo de benefício conforme padrões obrigatórios"""
        
        data_inicio = self._extrair_data_inicio_precisa(transcription)
        profissao = info.get('profissao', 'atividade profissional')
        
        if beneficio == 'incapacidade':
            # INCAPACIDADE LABORATIVA - Modelo EXATO
            return f"""BENEFÍCIO POR INCAPACIDADE LABORATIVA:

Diante do quadro clínico, exames e limitação funcional descritos, conclui-se que o(a) paciente encontra-se INCAPACITADO(A) para o exercício de sua atividade habitual como {profissao.lower()} desde {data_inicio}, recomendando-se afastamento das funções laborativas por tempo indeterminado, com reavaliação periódica.

JUSTIFICATIVA TÉCNICA:
{self._get_justificativa_profissional_detalhada(profissao, especialidade, transcription)}

NEXO CAUSAL: Entre as limitações funcionais apresentadas e a impossibilidade de desempenho das atividades profissionais habituais.

PARECER: FAVORÁVEL ao deferimento do benefício por incapacidade laborativa."""
        
        elif beneficio == 'bpc':
            # BPC/LOAS - Modelo EXATO
            natureza = self.natureza_impedimento.get(especialidade, 'física')
            
            # Verificar se é criança ou adulto
            idade = info.get('idade', '0')
            try:
                idade_num = int(idade) if idade.isdigit() else 0
            except:
                idade_num = 0
            
            if idade_num < 18:
                # MODELO PARA CRIANÇA
                return f"""BENEFÍCIO DE PRESTAÇÃO CONTINUADA (BPC/LOAS) - CRIANÇA:

A criança avaliada apresenta impedimento de longo prazo, de natureza {natureza}, caracterizado por limitações persistentes nas atividades adaptativas e participação social, conforme critérios legais vigentes.

IMPEDIMENTO DE LONGO PRAZO: Restrição permanente para o desempenho de atividades de vida diária adequadas à faixa etária, com limitação da participação social e necessidade de cuidados especiais.

NATUREZA DO IMPEDIMENTO: {natureza.title()}

CRITÉRIOS LEGAIS: As limitações enquadram-se na definição legal de impedimento (restrição de participação social e autonomia), iniciadas em {data_inicio}.

PARECER: FAVORÁVEL ao deferimento do BPC/LOAS."""
            else:
                # MODELO PARA ADULTO
                return f"""BENEFÍCIO DE PRESTAÇÃO CONTINUADA (BPC/LOAS) - ADULTO:

O paciente apresenta impedimento de longo prazo, de natureza {natureza}, com restrição permanente para o desempenho de atividades de vida diária e participação social.

IMPEDIMENTO DE LONGO PRAZO: Limitações funcionais permanentes que impedem a vida independente e a participação plena na sociedade.

NATUREZA DO IMPEDIMENTO: {natureza.title()}

DEFINIÇÃO LEGAL: Restrição de participação social e autonomia, com dependência para atividades básicas de vida diária.

Tais limitações, iniciadas em {data_inicio}, enquadram-se nos critérios exigidos para o benefício assistencial.

PARECER: FAVORÁVEL ao deferimento do BPC/LOAS."""
        
        elif beneficio == 'auxilio_acidente':
            # AUXÍLIO-ACIDENTE - Modelo EXATO
            return f"""AUXÍLIO-ACIDENTE PREVIDENCIÁRIO:

⚠️ ATENÇÃO CFM: Nexo causal trabalhista não pode ser estabelecido por telemedicina (CFM 2.314/2022).

REDUÇÃO DA CAPACIDADE LABORATIVA:
Há redução permanente da capacidade laborativa, com diminuição do desempenho para atividades que exigem {self._get_tipo_esforco(especialidade)}, embora ainda possível exercer parte das funções, com necessidade de adaptações e restrição de determinadas tarefas.

CAPACIDADE RESIDUAL: Parcial, com limitações específicas para determinadas atividades da profissão habitual.

IMPACTO ECONÔMICO: Redução da capacidade de geração de renda devido às limitações funcionais.

OBSERVAÇÃO: Avaliação limitada pela modalidade de telemedicina, sendo recomendada avaliação presencial para estabelecimento de nexo causal trabalhista.

PARECER: Redução de capacidade laborativa sem estabelecimento de nexo causal trabalhista."""
        
        elif beneficio == 'isencao_ir':
            # ISENÇÃO DE IMPOSTO DE RENDA - Modelo EXATO
            doenca_grave = self._get_doenca_grave_especifica(especialidade, transcription)
            
            return f"""ISENÇÃO DE IMPOSTO DE RENDA POR DOENÇA GRAVE:

O paciente é portador de {doenca_grave}, diagnosticada em {data_inicio}, condição esta que se enquadra no rol de doenças graves previstas na legislação (Lei 7.713/88, Art. 6º, inciso XIV).

DIAGNÓSTICO: {doenca_grave}
TEMPO DA DOENÇA: {data_inicio}
CORRESPONDÊNCIA LEGAL: Enquadra-se no rol de doenças graves da Receita Federal
NATUREZA: Doença de caráter permanente com comprometimento funcional

A condição apresentada justifica a solicitação de isenção do imposto de renda conforme dispositivos legais vigentes.

PARECER: FAVORÁVEL à isenção de imposto de renda por doença grave."""
        
        else:
            return f"""AVALIAÇÃO MÉDICA ESPECIALIZADA:

Conclusão a ser definida conforme finalidade específica da avaliação e critérios técnicos pertinentes ao caso.

PARECER: Conforme avaliação médica realizada."""

    def _get_doenca_grave_especifica(self, especialidade: str, transcription: str) -> str:
        """Obter doença grave específica para isenção de IR"""
        texto = transcription.lower()
        
        # Doenças graves específicas por palavra-chave
        if 'câncer' in texto or 'cancer' in texto or 'neoplasia' in texto:
            return 'neoplasia maligna'
        elif 'aids' in texto or 'hiv' in texto:
            return 'AIDS (Síndrome da Imunodeficiência Adquirida)'
        elif 'parkinson' in texto:
            return 'doença de Parkinson'
        elif 'alzheimer' in texto:
            return 'doença de Alzheimer'
        elif 'esclerose múltipla' in texto:
            return 'esclerose múltipla'
        elif 'cardiopatia' in texto or 'coração' in texto:
            return 'cardiopatia grave'
        elif 'renal' in texto or 'rim' in texto:
            return 'nefropatia grave'
        elif 'cegueira' in texto or 'visão' in texto:
            return 'cegueira (inclusive monocular)'
        elif especialidade == 'oncologia':
            return 'neoplasia maligna'
        elif especialidade == 'cardiologia':
            return 'cardiopatia grave'
        elif especialidade == 'neurologia':
            return 'doença neurológica degenerativa'
        else:
            return 'doença grave conforme relatado'
    
    # ===== MÉTODOS AUXILIARES PARA ANAMNESE =====
    
    def _get_fatores_desencadeantes_correto(self, especialidade: str, transcription: str) -> str:
        """Extrair fatores desencadeantes específicos da transcrição"""
        text = transcription.lower()
        
        if 'acidente' in text:
            return 'Acidente conforme relatado pelo paciente'
        elif 'trabalho' in text and ('esforço' in text or 'carregar' in text):
            return 'Sobrecarga laboral e esforços repetitivos'
        elif 'fone' in text or 'headset' in text or 'fones de ouvido' in text:
            return 'Uso prolongado de equipamentos auditivos em ambiente laboral'
        elif 'estresse' in text or 'pressão' in text:
            return 'Fatores psicossociais e estresse ocupacional'
        elif especialidade == 'cardiologia' and ('infarto' in text or 'coração' in text):
            return 'Evento cardiovascular agudo'
        elif especialidade == 'ortopedia' and 'dor' in text:
            return 'Atividade laboral com sobrecarga física'
        else:
            return 'Conforme relatado pelo paciente durante a consulta'

    def _get_tratamentos_realizados(self, transcription: str) -> str:
        """Extrair tratamentos da transcrição"""
        text = transcription.lower()
        
        tratamentos = []
        
        medicacoes = ['rivotril', 'clonazepam', 'sertralina', 'fluoxetina', 'amitriptilina', 
                      'losartan', 'sinvastatina', 'metformina', 'insulina', 'pirona', 'dipirona']
        
        for med in medicacoes:
            if med in text:
                tratamentos.append(f'Uso de {med.title()}')
        
        if 'fisioterapia' in text:
            tratamentos.append('Fisioterapia')
        if 'cirurgia' in text:
            tratamentos.append('Procedimento cirúrgico')
        if 'psicólogo' in text or 'terapia' in text:
            tratamentos.append('Acompanhamento psicológico')
        if 'fonoaudiologia' in text:
            tratamentos.append('Fonoaudiologia')
        
        return '; '.join(tratamentos) if tratamentos else 'Tratamentos conforme relatados pelo paciente'

    def _get_situacao_atual_detalhada(self, especialidade: str, beneficio: str, transcription: str) -> str:
        """Situação atual detalhada baseada na transcrição"""
        text = transcription.lower()
        
        limitacoes = []
        
        if 'não consigo' in text:
            limitacoes.append('Incapacidade funcional relatada')
        if 'dor' in text:
            limitacoes.append('Quadro álgico persistente')
        if 'cansaço' in text or 'fadiga' in text:
            limitacoes.append('Fadiga e limitação para esforços')
        if 'concentração' in text:
            limitacoes.append('Dificuldade de concentração')
        if 'perda auditiva' in text or 'não escuto' in text:
            limitacoes.append('Déficit auditivo progressivo')
        
        if beneficio == 'bpc':
            base = 'Dependência para atividades básicas de vida diária'
        elif beneficio == 'incapacidade':
            base = 'Incapacidade para exercício da atividade laboral habitual'
        else:
            base = 'Limitações funcionais atuais'
        
        if limitacoes:
            return f"{base}. {'; '.join(limitacoes)}"
        else:
            return base

    def _extrair_antecedentes(self, transcription: str) -> str:
        """Extrair antecedentes da transcrição"""
        text = transcription.lower()
        
        antecedentes = []
        doencas_comuns = ['diabetes', 'hipertensão', 'depressão', 'ansiedade', 'artrite', 
                          'artrose', 'fibromialgia', 'hipotireoidismo', 'enxaqueca', 'cefaleia']
        
        for doenca in doencas_comuns:
            if doenca in text:
                antecedentes.append(doenca.title())
        
        return ', '.join(antecedentes) if antecedentes else 'Não relatadas doenças prévias significativas'

    def _get_historico_ocupacional_detalhado(self, transcription: str, profissao: str) -> str:
        """Histórico ocupacional detalhado"""
        text = transcription.lower()
        
        tempo_patterns = [
            r'há (\d+) anos',
            r'(\d+) anos de trabalho',
            r'trabalho há (\d+)'
        ]
        
        tempo_trabalho = None
        for pattern in tempo_patterns:
            match = re.search(pattern, text)
            if match:
                tempo_trabalho = match.group(1)
                break
        
        base = f"Atua como {profissao or 'profissional'}"
        if tempo_trabalho:
            base += f" há {tempo_trabalho} anos"
        
        if 'contribuição' in text or 'inss' in text:
            base += ". Contribuinte do INSS"
        
        return base

    def _get_documentacao_apresentada(self, transcription: str) -> str:
        """Documentação apresentada baseada na transcrição"""
        text = transcription.lower()
        
        docs = []
        if 'exame' in text:
            docs.append('Exames complementares')
        if 'relatório' in text or 'laudo' in text:
            docs.append('Relatórios médicos')
        if 'receita' in text:
            docs.append('Prescrições médicas')
        if 'audiometria' in text:
            docs.append('Audiometria')
        
        return ', '.join(docs) if docs else 'Não foram apresentados documentos durante a teleconsulta'

    def _get_observacao_documentos(self, transcription: str) -> str:
        """Observação sobre documentos"""
        text = transcription.lower()
        
        if 'exame' in text or 'relatório' in text:
            return 'Documentação apresentada será considerada na avaliação'
        else:
            return 'Ausência de documentação médica complementar durante a teleconsulta'

    def _get_autoavaliacao_detalhada(self, especialidade: str, transcription: str) -> str:
        """Autoavaliação guiada detalhada"""
        if especialidade == 'psiquiatria':
            return 'Avaliação do estado mental, humor e capacidade funcional psíquica relatada'
        elif especialidade == 'cardiologia':
            return 'Autoavaliação da capacidade para esforços físicos e tolerância cardiovascular'
        elif especialidade == 'ortopedia':
            return 'Avaliação da mobilidade, força muscular e capacidade física relatada'
        elif especialidade == 'otorrinolaringologia' or 'perda auditiva' in transcription.lower():
            return 'Autoavaliação da capacidade auditiva e tolerância a esforços visuais relatada'
        else:
            return 'Autoavaliação funcional geral conforme relatado pelo paciente'

    def _get_observacao_video(self, transcription: str) -> str:
        """Observação visual por vídeo"""
        return 'Paciente orientado, colaborativo durante a teleconsulta'

    def _get_limitacoes_funcionais_detalhadas(self, especialidade: str, beneficio: str, transcription: str) -> str:
        """Limitações funcionais detalhadas"""
        text = transcription.lower()
        
        limitacoes_especificas = []
        
        if 'não consigo trabalhar' in text:
            limitacoes_especificas.append('Incapacidade para atividade laboral')
        if 'não consigo carregar' in text:
            limitacoes_especificas.append('Limitação para levantamento de peso')
        if 'não consigo concentrar' in text:
            limitacoes_especificas.append('Déficit de concentração')
        if 'dor forte' in text or 'dor de cabeça' in text:
            limitacoes_especificas.append('Limitação por quadro álgico intenso')
        if 'não consigo escutar' in text or 'perda auditiva' in text:
            limitacoes_especificas.append('Déficit auditivo unilateral')
        
        if beneficio == 'bpc':
            base = 'Limitações severas para atividades básicas de vida diária e participação social'
        else:
            base = 'Limitações funcionais que impedem o adequado desempenho laboral'
        
        if limitacoes_especificas:
            return f"{base}: {'; '.join(limitacoes_especificas)}"
        else:
            return base

    def _get_hipotese_diagnostica_detalhada(self, especialidade: str, transcription: str) -> str:
        """Hipótese diagnóstica detalhada baseada na transcrição"""
        text = transcription.lower()
        
        if 'perda auditiva' in text and 'dor de cabeça' in text:
            return 'Perda auditiva unilateral com cefaleia tensional secundária a esforço ocupacional'
        elif 'perda auditiva' in text:
            return 'Perda auditiva neurossensorial com comprometimento funcional'
        elif 'depressão' in text:
            return 'Transtorno depressivo com comprometimento funcional'
        elif 'ansiedade' in text:
            return 'Transtorno de ansiedade com limitação social e laboral'
        elif 'coração' in text or 'cardíaco' in text:
            return 'Cardiopatia com limitação funcional cardiovascular'
        elif 'coluna' in text or 'costas' in text:
            return 'Comprometimento da coluna vertebral com limitação motora'
        elif especialidade == 'psiquiatria':
            return 'Transtorno mental com comprometimento funcional significativo'
        elif especialidade == 'cardiologia':
            return 'Cardiopatia com limitação para esforços físicos'
        elif especialidade == 'ortopedia':
            return 'Comprometimento ortopédico com limitação funcional'
        elif especialidade == 'otorrinolaringologia':
            return 'Comprometimento auditivo com limitação para comunicação'
        else:
            return 'Condição médica com limitação funcional para atividades laborais'

    def _sugerir_cid_baseado_transcricao(self, especialidade: str, transcription: str) -> str:
        """Sugerir CID baseado na transcrição e especialidade"""
        text = transcription.lower()
        
        # CIDs específicos por sintomas mencionados - CASO RAQUEL
        if ('perda auditiva' in text or 'não consigo escutar' in text) and ('dor de cabeça' in text or 'enxaqueca' in text):
            if 'lado direito' in text or 'unilateral' in text:
                return 'H90.3 (Perda auditiva neurossensorial unilateral) e G44.2 (Cefaleia do tipo tensional)'
            else:
                return 'H90.5 (Perda auditiva neurossensorial não especificada) e G44.2 (Cefaleia do tipo tensional)'
        elif 'perda auditiva' in text or 'não consigo escutar' in text or 'surdez' in text:
            if 'lado direito' in text or 'unilateral' in text:
                return 'H90.3 (Perda auditiva neurossensorial unilateral)'
            else:
                return 'H90.5 (Perda auditiva neurossensorial não especificada)'
        elif 'dor de cabeça' in text or 'enxaqueca' in text or 'cefaleia' in text:
            return 'G44.2 (Cefaleia do tipo tensional)'
        elif 'depressão' in text:
            return 'F32.9 (Episódio depressivo não especificado)'
        elif 'ansiedade' in text:
            return 'F41.9 (Transtorno de ansiedade não especificado)'
        elif 'coluna' in text or 'lombar' in text:
            return 'M54.5 (Lombalgia)'
        elif 'coração' in text:
            return 'I25.9 (Doença isquêmica crônica do coração)'
        elif 'artrite' in text:
            return 'M05.9 (Artrite reumatoide soropositiva não especificada)'
        elif especialidade == 'psiquiatria':
            return 'F32.9 (Episódio depressivo não especificado)'
        elif especialidade == 'cardiologia':
            return 'I25.9 (Doença isquêmica crônica do coração)'
        elif especialidade == 'ortopedia':
            return 'M79.9 (Transtorno dos tecidos moles, não especificado)'
        elif especialidade == 'reumatologia':
            return 'M05.9 (Artrite reumatoide soropositiva não especificada)'
        elif especialidade == 'otorrinolaringologia':
            return 'H90.9 (Perda auditiva não especificada)'
        else:
            return 'Z03.9 (Observação para suspeita de doença ou afecção não especificada)'
    
    # ===== MÉTODOS AUXILIARES PARA LAUDO =====
    
    def _gerar_historia_clinica_detalhada(self, info: Dict, especialidade: str, transcription: str) -> str:
        """1. História Clínica - Relato detalhado com datas"""
        texto = transcription.lower()
        
        inicio_sintomas = self._extrair_inicio_detalhado(texto)
        evolucao = self._extrair_evolucao_sintomas(texto, especialidade)
        contexto = self._extrair_contexto_clinico(texto, especialidade)
        
        historia = f"""Paciente {info.get('sexo', '').lower()}, {info.get('idade', 'idade não informada')} anos, {info.get('profissao', 'profissão não relatada')}, apresenta quadro de {self._extrair_quadro_principal(texto, especialidade)}.

{inicio_sintomas}

{evolucao}

{contexto}

Antecedentes pessoais: {self._extrair_antecedentes_detalhados(texto)}"""
        
        return historia

    def _gerar_limitacao_funcional_detalhada(self, info: Dict, beneficio: str, especialidade: str, transcription: str) -> str:
        """2. Limitação Funcional - Descrição clara correlacionada com profissão"""
        texto = transcription.lower()
        profissao = info.get('profissao', 'profissional')
        
        limitacoes_atividades = self._extrair_limitacoes_atividades_diarias(texto)
        limitacoes_profissionais = self._extrair_limitacoes_profissionais(texto, profissao, especialidade)
        
        if beneficio == 'bpc':
            return f"""Apresenta limitações severas para atividades básicas de vida diária: {limitacoes_atividades}

Demonstra dependência para autocuidado, mobilidade e participação social, caracterizando impedimento de longo prazo conforme critérios legais."""
        
        else:
            return f"""Apresenta limitações funcionais significativas nas seguintes atividades diárias: {limitacoes_atividades}

{limitacoes_profissionais}

As limitações atuais impedem o exercício da função de {profissao.lower()}, especialmente para atividades que demandam {self._get_demandas_profissionais(profissao, especialidade)}."""

    def _gerar_secao_exames_detalhada(self, transcription: str) -> str:
        """3. Exames - Lista e análise objetiva com datas"""
        texto = transcription.lower()
        
        exames_mencionados = []
        
        tipos_exames = {
            'audiometria': 'Audiometria',
            'ressonância': 'Ressonância magnética',
            'raio x': 'Radiografia',
            'tomografia': 'Tomografia computadorizada',
            'ultrassom': 'Ultrassonografia',
            'eletrocardiograma': 'Eletrocardiograma',
            'hemograma': 'Hemograma completo',
            'glicemia': 'Glicemia de jejum',
            'colesterol': 'Perfil lipídico'
        }
        
        for termo, nome_exame in tipos_exames.items():
            if termo in texto:
                data_exame = self._extrair_data_exame(texto, termo)
                resultado = self._extrair_resultado_exame(texto, termo)
                exames_mencionados.append(f"- {nome_exame} ({data_exame}): {resultado}")
        
        if exames_mencionados:
            return "Exames complementares apresentados:\n" + "\n".join(exames_mencionados)
        else:
            return "Não foram apresentados exames complementares durante a teleconsulta. Recomenda-se complementação propedêutica conforme indicação clínica."

    def _gerar_secao_tratamento_detalhada(self, info: Dict, especialidade: str, transcription: str) -> str:
        """4. Tratamento - Detalhado com datas e resposta"""
        texto = transcription.lower()
        
        medicacoes_atuais = self._extrair_medicacoes_detalhadas(texto)
        tratamentos_realizados = self._extrair_tratamentos_detalhados(texto)
        resposta_tratamento = self._extrair_resposta_tratamento(texto)
        
        tratamento = f"""Medicações em uso atual: {medicacoes_atuais}

Tratamentos realizados: {tratamentos_realizados}

Resposta apresentada: {resposta_tratamento}

Orientações: Manutenção do tratamento atual conforme acompanhamento especializado."""
        
        return tratamento

    def _gerar_prognostico_detalhado(self, info: Dict, especialidade: str, beneficio: str, transcription: str) -> str:
        """5. Prognóstico - Expectativa de evolução detalhada"""
        texto = transcription.lower()
        
        gravidade = self._analisar_gravidade_caso(texto, especialidade)
        
        if beneficio == 'bpc':
            return f"""Prognóstico reservado para recuperação funcional significativa. {gravidade}

Expectativa de dependência permanente para atividades de vida diária, com necessidade de cuidador em tempo integral.

Possibilidade de agravamento progressivo conforme evolução natural da condição."""
        
        elif beneficio == 'incapacidade':
            return f"""Prognóstico reservado para retorno às atividades laborais habituais no curto prazo. {gravidade}

Previsão de manutenção das limitações funcionais atuais, com baixa possibilidade de recuperação para exercício da atividade profissional habitual.

Recomenda-se reavaliação periódica para monitoramento da evolução."""
        
        else:
            return f"""Prognóstico variável conforme resposta ao tratamento. {gravidade}

Expectativa de evolução dependente de adesão terapêutica e cuidados especializados."""
    
    # ===== MÉTODOS AUXILIARES DETALHADOS =====
    
    def _extrair_informacoes(self, patient_info: str, transcription: str) -> Dict[str, str]:
        texto_completo = f"{patient_info} {transcription}".lower()
        
        info = {
            'nome': self._extrair_nome(patient_info + " " + transcription),
            'idade': self._extrair_idade(texto_completo),
            'sexo': self._extrair_sexo(texto_completo),
            'profissao': self._extrair_profissao(texto_completo),
            'sintomas': self._extrair_sintomas(texto_completo),
            'data_inicio': self._extrair_data_inicio(texto_completo),
            'medicacoes': self._extrair_medicacoes(texto_completo),
            'queixa_principal': self._extrair_queixa_principal(patient_info + " " + transcription),
            'doencas_previas': self._extrair_doencas_previas(texto_completo),
            'historico_ocupacional': self._extrair_historico_ocupacional(texto_completo),
            'historico_familiar': 'Não relatado',
            'documentos': 'Não apresentados',
            'obs_documentos': 'Ausência de documentação médica complementar',
            'observacao_video': 'Não realizada',
            'processo': 'Não aplicável',
            'advogado': 'Não informada',
            'documento': 'Não apresentado'
        }
        
        return info
    
    def _extrair_nome(self, texto: str) -> str:
        """Extrair nome do paciente"""
        patterns = [
            r'nome[:]\s*([A-ZÀ-ú][a-zà-ú\s]+)',
            r'eu sou ([A-ZÀ-ú][a-zà-ú\s]+)',
            r'me chamo ([A-ZÀ-ú][a-zà-ú\s]+)',
            r'([A-ZÀ-ú][a-zà-ú]+),?\s+\d+\s+anos'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                nome = match.group(1).strip()
                if len(nome) > 2:
                    return nome.title()
        
        return "Não informado"
    
    def _extrair_idade(self, texto: str) -> str:
        """Extrair idade do paciente"""
        patterns = [
            r'(\d+)\s+anos',
            r'idade[:]\s*(\d+)',
            r'tenho\s+(\d+)\s+anos'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto)
            if match:
                return match.group(1)
        
        return "Não informado"
    
    def _extrair_sexo(self, texto: str) -> str:
        """Extrair sexo do paciente"""
        if any(word in texto for word in ['feminino', 'mulher', 'senhora', 'sra']):
            return "Feminino"
        elif any(word in texto for word in ['masculino', 'homem', 'senhor', 'sr']):
            return "Masculino"
        
        # Inferir por profissão
        if any(prof in texto for prof in ['professora', 'enfermeira', 'secretária', 'recepcionista']):
            return "Feminino"
        elif any(prof in texto for prof in ['professor', 'enfermeiro', 'pedreiro', 'motorista']):
            return "Masculino"
        
        return "Não informado"
    
    def _extrair_profissao(self, texto: str) -> str:
        """Extrair profissão do paciente"""
        profissoes = [
            'professor', 'professora', 'dentista', 'motorista', 'pedreiro',
            'enfermeiro', 'enfermeira', 'médico', 'médica', 'advogado',
            'advogada', 'engenheiro', 'engenheira', 'comerciante',
            'vendedor', 'vendedora', 'contador', 'contadora',
            # NOVAS PROFISSÕES:
            'atendente', 'telemarketing', 'operador', 'operadora',
            'recepcionista', 'secretária', 'secretario', 'caixa',
            'auxiliar', 'assistente', 'analista', 'técnico', 'técnica',
            'faxineiro', 'faxineira', 'porteiro', 'porteira', 'segurança',
            'vigilante', 'operário', 'operária', 'soldador', 'soldadora',
            'mecânico', 'mecânica', 'fisioterapeuta', 'psicólogo', 'psicóloga',
            'pedagogo', 'pedagoga', 'coordenador', 'coordenadora',
            'juiz', 'juíza', 'cozinheiro', 'cozinheira', 'garçom', 'garçonete',
            'promotor', 'promotora'
        ]
        
        for profissao in profissoes:
            if profissao in texto:
                return profissao.title()
        
        # Padrões específicos para extrair profissões
        patterns = [
            r'profiss[ãa]o[:]\s*([A-zÀ-ú\s]+)',
            r'trabalho como\s+([A-zÀ-ú\s]+)',
            r'sou\s+([A-zÀ-ú\s]+)',
            r'atendimento ao cliente',
            r'custom service',
            r'call center',
            r'telemarketing'
        ]
        
        # Verificar padrões específicos primeiro
        if 'atendimento ao cliente' in texto or 'custom service' in texto:
            return 'Atendente'
        elif 'call center' in texto or 'telemarketing' in texto:
            return 'Telemarketing'
        
        for pattern in patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                prof = match.group(1).strip() if match.groups() else match.group(0)
                if len(prof) > 2 and prof not in ['de', 'da', 'do', 'na', 'no']:
                    return prof.title()
        
        return "Não relatado"
    
    def _extrair_sintomas(self, texto: str) -> str:
        """Extrair sintomas principais"""
        sintomas_encontrados = []
        
        sintomas_comuns = [
            'dor', 'ansiedade', 'depressao', 'insonia', 'fadiga',
            'tontura', 'nausea', 'vomito', 'febre', 'tosse',
            'falta de ar', 'palpitacao', 'tremor', 'perda auditiva',
            'dor de cabeça', 'enxaqueca'
        ]
        
        for sintoma in sintomas_comuns:
            if sintoma in texto:
                sintomas_encontrados.append(sintoma)
        
        return ', '.join(sintomas_encontrados) if sintomas_encontrados else "Não especificados"
    
    def _extrair_data_inicio(self, texto: str) -> str:
        """Extrair data de início dos sintomas"""
        patterns = [
            r'há\s+(\d+)\s+anos?',
            r'(\d+)\s+anos?\s+atrás',
            r'desde\s+(\d{4})',
            r'iniciou\s+em\s+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto)
            if match:
                return f"Há {match.group(1)}"
        
        return "Não especificada"
    
    def _extrair_medicacoes(self, texto: str) -> str:
        """Extrair medicações em uso"""
        medicacoes = []
        
        medicacoes_comuns = [
            'rivotril', 'clonazepam', 'sertralina', 'fluoxetina',
            'amitriptilina', 'losartan', 'sinvastatina', 'metformina',
            'insulina', 'captopril', 'hidroclorotiazida', 'pirona', 'dipirona'
        ]
        
        for med in medicacoes_comuns:
            if med in texto:
                medicacoes.append(med.title())
        
        return ', '.join(medicacoes) if medicacoes else "Não relatadas"
    
    def _extrair_queixa_principal(self, texto: str) -> str:
        """Extrair queixa principal"""
        patterns = [
            r'"([^"]+)"',
            r'queixa[:]\s*([^.]+)',
            r'motivo[:]\s*([^.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        sentences = texto.split('.')
        for sentence in sentences:
            if len(sentence.strip()) > 10:
                return sentence.strip()
        
        return "Não especificada"
    
    def _extrair_doencas_previas(self, texto: str) -> str:
        """Extrair doenças prévias"""
        doencas = []
        
        doencas_comuns = [
            'diabetes', 'hipertensao', 'depressao', 'ansiedade',
            'artrite', 'artrose', 'fibromialgia', 'lupus',
            'hipotireoidismo', 'hipertireoidismo', 'enxaqueca'
        ]
        
        for doenca in doencas_comuns:
            if doenca in texto:
                doencas.append(doenca.title())
        
        return ', '.join(doencas) if doencas else "Não relatadas"
    
    def _extrair_historico_ocupacional(self, texto: str) -> str:
        """Extrair histórico ocupacional"""
        patterns = [
            r'trabalho há\s+(\d+)\s+anos?',
            r'(\d+)\s+anos?\s+de\s+trabalho',
            r'tempo de servico[:]\s*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto)
            if match:
                return f"{match.group(1)} anos de atividade"
        
        return "Não relatado"
    
    # ===== MÉTODOS AUXILIARES ESPECÍFICOS PARA LAUDO =====
    
    def _extrair_inicio_detalhado(self, texto: str) -> str:
        """Extrair início dos sintomas de forma detalhada"""
        patterns = [
            (r'há (\d+) anos', lambda m: f"Refere início dos sintomas há {m.group(1)} anos"),
            (r'desde (\d{4})', lambda m: f"Sintomas iniciados desde {m.group(1)}"),
            (r'começou em (\w+)', lambda m: f"Quadro iniciado em {m.group(1)}")
        ]
        
        for pattern, formatter in patterns:
            match = re.search(pattern, texto)
            if match:
                return formatter(match) + ", com evolução progressiva."
        
        return "Início dos sintomas conforme relatado pelo paciente, com evolução progressiva."

    def _extrair_evolucao_sintomas(self, texto: str, especialidade: str) -> str:
        """Extrair evolução dos sintomas"""
        if 'piorou' in texto or 'piorando' in texto:
            return "Evolução com piora progressiva dos sintomas ao longo do tempo."
        elif 'melhorou' in texto or 'melhorando' in texto:
            return "Evolução com melhora parcial, porém com persistência das limitações funcionais."
        elif 'estável' in texto:
            return "Evolução estável, sem melhora significativa das limitações."
        else:
            return "Evolução conforme relatado, com impacto funcional progressivo."

    def _extrair_contexto_clinico(self, texto: str, especialidade: str) -> str:
        """Extrair contexto clínico específico"""
        if 'fone' in texto or 'headset' in texto:
            return "Contexto de uso prolongado de equipamentos auditivos em ambiente laboral contribuindo para o quadro."
        elif 'trabalho' in texto and ('estresse' in texto or 'pressão' in texto):
            return "Contexto de sobrecarga laboral e fatores estressores ocupacionais contribuindo para o quadro."
        elif 'acidente' in texto:
            return "Contexto de evento traumático conforme relatado pelo paciente."
        elif especialidade == 'psiquiatria' and 'família' in texto:
            return "Contexto familiar e psicossocial relevante para o quadro atual."
        else:
            return "Contexto clínico conforme história relatada pelo paciente."

    def _extrair_quadro_principal(self, texto: str, especialidade: str) -> str:
        """Extrair quadro clínico principal"""
        if 'perda auditiva' in texto and 'dor de cabeça' in texto:
            return 'perda auditiva unilateral com cefaleia ocupacional'
        elif 'perda auditiva' in texto:
            return 'perda auditiva neurossensorial com comprometimento funcional'
        elif 'depressão' in texto:
            return 'transtorno depressivo com comprometimento funcional'
        elif 'ansiedade' in texto:
            return 'transtorno de ansiedade com limitação psicossocial'
        elif 'dor' in texto and 'coluna' in texto:
            return 'lombalgias com limitação funcional'
        elif 'artrite' in texto:
            return 'artrite reumatoide com comprometimento funcional'
        elif 'coração' in texto:
            return 'cardiopatia com limitação cardiovascular'
        elif especialidade == 'psiquiatria':
            return 'transtorno mental com comprometimento funcional'
        elif especialidade == 'ortopedia':
            return 'comprometimento ortopédico com limitação motora'
        elif especialidade == 'reumatologia':
            return 'doença reumatológica com limitação articular'
        elif especialidade == 'otorrinolaringologia':
            return 'comprometimento auditivo com limitação comunicativa'
        else:
            return 'condição médica com limitação funcional'

    def _extrair_antecedentes_detalhados(self, texto: str) -> str:
        """Extrair antecedentes detalhados"""
        antecedentes = []
        
        condicoes = {
            'diabetes': 'Diabetes mellitus',
            'hipertensão': 'Hipertensão arterial sistêmica',
            'depressão': 'Episódios depressivos prévios',
            'ansiedade': 'Transtornos de ansiedade',
            'cirurgia': 'Procedimentos cirúrgicos prévios',
            'enxaqueca': 'Episódios de cefaleia do tipo enxaqueca'
        }
        
        for termo, descricao in condicoes.items():
            if termo in texto:
                antecedentes.append(descricao)
        
        return '. '.join(antecedentes) if antecedentes else 'Nega comorbidades significativas'

    def _extrair_limitacoes_atividades_diarias(self, texto: str) -> str:
        """Extrair limitações específicas para atividades diárias"""
        limitacoes = []
        
        padroes_limitacao = {
            'não consigo dormir': 'distúrbios do sono',
            'não consigo caminhar': 'limitação para deambulação',
            'não consigo carregar': 'limitação para levantamento de peso',
            'não consigo concentrar': 'déficit de concentração',
            'não consigo escutar': 'déficit auditivo',
            'perda auditiva': 'déficit auditivo',
            'dor forte': 'limitação por quadro álgico intenso',
            'dor de cabeça': 'limitação por quadro álgico intenso',
            'cansaço': 'fadiga e intolerância a esforços'
        }
        
        for padrao, limitacao in padroes_limitacao.items():
            if padrao in texto:
                limitacoes.append(limitacao)
        
        return ', '.join(limitacoes) if limitacoes else 'limitações funcionais conforme relatado'

    def _extrair_limitacoes_profissionais(self, texto: str, profissao: str, especialidade: str) -> str:
        """Extrair limitações específicas para a profissão"""
        limitacoes_prof = {
            'professor': 'Incapacidade para ministrar aulas, manter concentração em sala e interação adequada com alunos.',
            'professora': 'Incapacidade para ministrar aulas, manter concentração em sala e interação adequada com alunos.',
            'motorista': 'Limitação para condução de veículos, reflexos comprometidos e intolerância a esforços.',
            'pedreiro': 'Impossibilidade de levantamento de peso, trabalho em altura e esforços físicos da construção.',
            'enfermeiro': 'Limitação para plantões, cuidados diretos ao paciente e tomada de decisões críticas.',
            'enfermeira': 'Limitação para plantões, cuidados diretos ao paciente e tomada de decisões críticas.',
            'dentista': 'Incapacidade para procedimentos odontológicos, controle motor fino e interação com pacientes.',
            # NOVAS PROFISSÕES:
            'atendente': 'Incapacidade para atendimento telefônico, dificuldade de comunicação e intolerância a equipamentos auditivos.',
            'telemarketing': 'Incapacidade para comunicação telefônica, uso de headsets e concentração prolongada.',
            'operador': 'Incapacidade para operação de equipamentos, comunicação telefônica e concentração prolongada.',
            'operadora': 'Incapacidade para operação de equipamentos, comunicação telefônica e concentração prolongada.',
            'recepcionista': 'Incapacidade para atendimento ao público, comunicação telefônica e uso de equipamentos.',
            'secretária': 'Limitação para atividades administrativas, comunicação telefônica e uso prolongado de computador.',
            'secretario': 'Limitação para atividades administrativas, comunicação telefônica e uso prolongado de computador.',
            'vendedor': 'Incapacidade para comunicação com clientes, esforços físicos e concentração prolongada.',
            'vendedora': 'Incapacidade para comunicação com clientes, esforços físicos e concentração prolongada.',
            'caixa': 'Limitação para atendimento ao público, permanência em pé e uso de equipamentos.',
            'técnico': 'Limitação para atividades técnicas, concentração prolongada e uso de equipamentos especializados.',
            'técnica': 'Limitação para atividades técnicas, concentração prolongada e uso de equipamentos especializados.',
            'analista': 'Limitação para análises complexas, concentração prolongada e uso intensivo de computadores.',
            'assistente': 'Limitação para atividades de apoio, comunicação eficaz e uso de equipamentos administrativos.',
            'auxiliar': 'Limitação para atividades auxiliares, esforços físicos e concentração necessária.',
            'faxineiro': 'Impossibilidade de esforços físicos intensos, levantamento de peso e movimentos repetitivos.',
            'faxineira': 'Impossibilidade de esforços físicos intensos, levantamento de peso e movimentos repetitivos.',
            'segurança': 'Limitação para vigilância constante, reflexos rápidos e esforços físicos.',
            'vigilante': 'Limitação para vigilância prolongada, atenção constante e capacidade de resposta.',
            'operário': 'Impossibilidade de esforços físicos intensos, levantamento de peso e trabalho industrial.',
            'operária': 'Impossibilidade de esforços físicos intensos, levantamento de peso e trabalho industrial.',
            'mecânico': 'Limitação para esforços físicos, uso de ferramentas e trabalho em posições inadequadas.',
            'mecânica': 'Limitação para esforços físicos, uso de ferramentas e trabalho em posições inadequadas.'
        }
        
        prof_key = profissao.lower() if profissao else 'default'
        return limitacoes_prof.get(prof_key, f'Limitações funcionais que impedem o adequado exercício da função de {profissao}.')

    def _get_demandas_profissionais(self, profissao: str, especialidade: str) -> str:
        """Obter demandas específicas da profissão"""
        demandas = {
            'professor': 'concentração prolongada, interação social e controle emocional',
            'professora': 'concentração prolongada, interação social e controle emocional',
            'motorista': 'reflexos rápidos, concentração e esforço físico',
            'pedreiro': 'levantamento de peso, trabalho em altura e esforços físicos intensos',
            'enfermeiro': 'plantões noturnos, tomada de decisões e cuidados diretos ao paciente',
            'enfermeira': 'plantões noturnos, tomada de decisões e cuidados diretos ao paciente',
            'dentista': 'concentração prolongada, controle motor fino e precisão manual',
            # NOVAS PROFISSÕES:
            'atendente': 'comunicação telefônica prolongada, concentração auditiva e tolerância a equipamentos',
            'telemarketing': 'comunicação telefônica eficaz, uso de headsets e concentração prolongada',
            'operador': 'comunicação telefônica, operação de equipamentos e concentração prolongada',
            'operadora': 'comunicação telefônica, operação de equipamentos e concentração prolongada',
            'recepcionista': 'atendimento ao público, comunicação telefônica e uso de equipamentos',
            'secretária': 'atividades administrativas, comunicação e uso prolongado de computador',
            'secretario': 'atividades administrativas, comunicação e uso prolongado de computador',
            'vendedor': 'comunicação eficaz, esforços físicos e concentração',
            'vendedora': 'comunicação eficaz, esforços físicos e concentração',
            'caixa': 'atendimento ao público, permanência em pé e concentração',
            'técnico': 'atividades técnicas especializadas, concentração e uso de equipamentos',
            'técnica': 'atividades técnicas especializadas, concentração e uso de equipamentos',
            'analista': 'análises complexas, concentração prolongada e uso de computadores',
            'assistente': 'atividades de apoio, comunicação e uso de equipamentos',
            'auxiliar': 'atividades auxiliares, esforços físicos e concentração',
            'faxineiro': 'esforços físicos intensos, levantamento de peso e movimentos repetitivos',
            'faxineira': 'esforços físicos intensos, levantamento de peso e movimentos repetitivos',
            'segurança': 'vigilância constante, reflexos rápidos e esforços físicos',
            'vigilante': 'vigilância prolongada, atenção constante e resposta rápida',
            'operário': 'esforços físicos intensos, levantamento de peso e trabalho industrial',
            'operária': 'esforços físicos intensos, levantamento de peso e trabalho industrial',
            'mecânico': 'esforços físicos, uso de ferramentas e trabalho técnico',
            'mecânica': 'esforços físicos, uso de ferramentas e trabalho técnico'
        }
        
        return demandas.get(profissao.lower(), 'esforço físico e mental adequados')

    def _extrair_data_exame(self, texto: str, tipo_exame: str) -> str:
        """Extrair data do exame"""
        patterns = [
            rf'{tipo_exame}.*?(\d{{1,2}}/\d{{1,2}}/\d{{4}})',
            rf'{tipo_exame}.*?(\d{{4}})',
            rf'{tipo_exame}.*?(há \d+ meses?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return 'data não especificada'

    def _extrair_resultado_exame(self, texto: str, tipo_exame: str) -> str:
        """Extrair resultado do exame"""
        if 'normal' in texto:
            return 'dentro dos parâmetros normais'
        elif 'alterado' in texto:
            return 'alterações conforme laudo apresentado'
        else:
            return 'conforme laudo apresentado'

    def _extrair_medicacoes_detalhadas(self, texto: str) -> str:
        """Extrair medicações com mais detalhes"""
        medicacoes = []
        
        medicacoes_patterns = [
            (r'rivotril.*?(\d+.*?mg)', 'Rivotril'),
            (r'clonazepam.*?(\d+.*?mg)', 'Clonazepam'),
            (r'sertralina.*?(\d+.*?mg)', 'Sertralina'),
            (r'fluoxetina.*?(\d+.*?mg)', 'Fluoxetina'),
            (r'pirona.*?(\d+.*?mg)', 'Pirona'),
            (r'dipirona.*?(\d+.*?mg)', 'Dipirona')
        ]
        
        for pattern, nome in medicacoes_patterns:
            match = re.search(pattern, texto, re.IGNORECASE)
            if match:
                dose = match.group(1) if match.groups() else 'dose conforme prescrição'
                medicacoes.append(f'{nome} {dose}')
        
        # Verificar medicações sem dose específica
        if 'pirona' in texto and not any('Pirona' in med for med in medicacoes):
            medicacoes.append('Pirona ocasional')
        
        return ', '.join(medicacoes) if medicacoes else 'Medicações conforme relatado pelo paciente'

    def _extrair_tratamentos_detalhados(self, texto: str) -> str:
        """Extrair tratamentos detalhados"""
        tratamentos = []
        
        if 'fisioterapia' in texto:
            tratamentos.append('Fisioterapia realizada')
        if 'psicoterapia' in texto or 'psicólogo' in texto:
            tratamentos.append('Acompanhamento psicológico')
        if 'cirurgia' in texto:
            tratamentos.append('Procedimento cirúrgico')
        if 'fonoaudiologia' in texto:
            tratamentos.append('Acompanhamento fonoaudiológico')
        
        return '; '.join(tratamentos) if tratamentos else 'Tratamentos medicamentosos conforme prescrição médica'

    def _extrair_resposta_tratamento(self, texto: str) -> str:
        """Extrair resposta ao tratamento"""
        if 'melhorou' in texto:
            return 'Melhora parcial com persistência das limitações funcionais'
        elif 'piorou' in texto:
            return 'Ausência de melhora significativa, com agravamento do quadro'
        elif 'não melhorou' in texto:
            return 'Resposta insatisfatória ao tratamento instituído'
        else:
            return 'Resposta ao tratamento conforme relatado pelo paciente'

    def _analisar_gravidade_caso(self, texto: str, especialidade: str) -> str:
        """Analisar gravidade do caso"""
        if 'grave' in texto or 'muito forte' in texto:
            return 'Quadro de gravidade significativa.'
        elif 'moderado' in texto:
            return 'Quadro de intensidade moderada.'
        else:
            return 'Quadro com impacto funcional relevante.'

    def _extrair_data_inicio_precisa(self, transcription: str) -> str:
        """Extrair data de início mais precisa"""
        texto = transcription.lower()
        
        patterns = [
            r'há (\d+) anos',
            r'desde (\d{4})',
            r'(\d+) anos atrás'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texto)
            if match:
                return match.group(0)
        
        return 'data não especificada'

    def _get_justificativa_profissional_detalhada(self, profissao: str, especialidade: str, transcription: str) -> str:
        """Justificativa detalhada baseada na profissão e transcrição"""
        texto = transcription.lower()
        
        # CASO ESPECÍFICO DA RAQUEL - ATENDENTE COM PERDA AUDITIVA
        if 'atendente' in profissao.lower() or 'telemarketing' in profissao.lower():
            if 'perda auditiva' in texto or 'não consigo escutar' in texto:
                return 'As limitações auditivas impedem a comunicação telefônica eficaz necessária para atendimento ao cliente, comprometem a compreensão de solicitações e impossibilitam o uso adequado de equipamentos de áudio exigidos pela profissão.'
        
        elif 'professor' in profissao.lower():
            if 'ansiedade' in texto or 'depressão' in texto:
                return 'Os sintomas psiquiátricos impedem a concentração necessária para ministrar aulas, o controle emocional para lidar com situações de sala de aula e a interação adequada com alunos, tornando impossível o exercício seguro e eficaz da docência.'
        
        elif 'motorista' in profissao.lower():
            if 'coração' in texto or 'cardíaco' in texto:
                return 'As limitações cardiovasculares impedem a manutenção da concentração necessária para condução segura, comprometem os reflexos em situações de emergência e impossibilitam a tolerância aos esforços físicos exigidos pela profissão.'
        
        elif 'dentista' in profissao.lower():
            if 'artrite' in texto or 'mãos' in texto:
                return 'As limitações articulares nas mãos impedem a precisão manual necessária para procedimentos odontológicos, o controle de instrumentos delicados e a realização de movimentos finos exigidos pela profissão.'
        
        # Pegar justificativa do dicionário
        prof_key = profissao.lower() if profissao else 'default'
        if prof_key in self.justificativas_profissionais:
            return self.justificativas_profissionais[prof_key]
        
        # Justificativa genérica baseada na especialidade
        justificativas_especialidade = {
            'psiquiatria': 'Os transtornos mentais impedem a concentração, tomada de decisões e controle emocional necessários',
            'cardiologia': 'As limitações cardiovasculares impedem esforços físicos e comprometem a capacidade laborativa',
            'ortopedia': 'As limitações ortopédicas impedem movimentos, levantamento de peso e atividades físicas',
            'reumatologia': 'As limitações articulares impedem movimentos precisos e esforços físicos',
            'otorrinolaringologia': 'As limitações auditivas impedem a comunicação eficaz e o uso adequado de equipamentos auditivos'
        }
        
        base = justificativas_especialidade.get(especialidade, 'As limitações funcionais atuais impedem')
        return f'{base} para o adequado desempenho das funções profissionais habituais.'
    
    # ===== MÉTODOS AUXILIARES GERAIS =====
    
    def _get_motivo_consulta(self, beneficio: str) -> str:
        motivos = {
            'bpc': 'Solicitação de BPC/LOAS',
            'incapacidade': 'Avaliação de incapacidade laboral',
            'auxilio_acidente': 'Auxílio-acidente previdenciário',
            'isencao_ir': 'Isenção de Imposto de Renda',
            'pericia': 'Perícia médica'
        }
        return motivos.get(beneficio, 'Consulta médica')
    
    def _get_tipo_esforco(self, especialidade: str) -> str:
        """Obter tipo de esforço comprometido por especialidade"""
        tipos = {
            'cardiologia': 'esforço físico intenso',
            'ortopedia': 'levantamento de peso e trabalho físico',
            'psiquiatria': 'concentração e tomada de decisões',
            'neurologia': 'coordenação e funções cognitivas',
            'oftalmologia': 'acuidade visual e coordenação visual-motora',
            'reumatologia': 'movimentos articulares e esforços físicos',
            'otorrinolaringologia': 'comunicação eficaz e uso de equipamentos auditivos'
        }
        return tipos.get(especialidade, 'esforço físico e mental')

# Instância global
laudo_generator = LaudoTemplatesExatos()