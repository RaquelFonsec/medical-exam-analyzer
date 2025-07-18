import re
from typing import Dict, List, Tuple
from datetime import datetime

class ContextClassifierService:
    """Classifica o tipo de consulta/laudo baseado no contexto"""
    
    def __init__(self):
        # Palavras-chave EXPANDIDAS para cada tipo de contexto
        self.context_keywords = {
            'bpc': [
                'bpc', 'beneficio de prestacao continuada', 'prestacao continuada',
                'loas', 'assistencia social', 'deficiencia', 'incapacidade permanente',
                'renda per capita', 'vulnerabilidade social', 'vida independente',
                'cuidador', 'autonomia', 'atividades basicas', 'higiene pessoal'
            ],
            'incapacidade': [
                'auxilio doenca', 'aposentadoria por invalidez', 'incapacidade temporaria',
                'incapacidade laboral', 'inss', 'beneficio por incapacidade',
                'afastamento do trabalho', 'incapaz para o trabalho', 'pedreiro',
                'trabalho', 'profissao', 'funcao', 'atividade laboral', 'carregar peso',
                'afastamento', 'previdenciario', 'pericia medica'
            ],
            'auxilio_acidente': [
                'auxilio acidente', 'reducao da capacidade', 'acidente de trabalho',
                'sequela', 'incapacidade parcial', 'redução laboral',
                'capacidade reduzida', 'limitacao parcial'
            ],
            'pericia': [
                'pericia medica', 'avaliacao pericial', 'junta medica',
                'exame pericial', 'laudo pericial', 'capacidade laboral',
                'nexo causal', 'acidente de trabalho', 'dano corporal',
                'sequela', 'invalidez', 'processo', 'advogado', 'judicial'
            ],
            'isencao_ir': [
                'isencao', 'imposto de renda', 'ir', 'receita federal',
                'doenca grave', 'neoplasia', 'cancer', 'cardiopatia',
                'nefropatia', 'hepatopatia', 'moléstia profissional',
                'tuberculose', 'alienacao mental', 'esclerose multipla',
                'cegueira', 'hanseníase', 'paralisia', 'aids', 'hiv'
            ],
            'clinica': [
                'consulta medica', 'acompanhamento', 'tratamento',
                'medicacao', 'exame de rotina', 'check up', 'dor', 'sintomas'
            ]
        }
    
    def classify_context(self, patient_info: str, transcription: str, documents_text: str = "") -> Dict:
        """Classifica o contexto da consulta"""
        
        # Texto completo para análise
        full_text = f"{patient_info} {transcription} {documents_text}".lower()
        
        # Contar ocorrências de cada contexto
        context_scores = {}
        
        for context_type, keywords in self.context_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                count = len(re.findall(rf'\b{re.escape(keyword)}\b', full_text))
                if count > 0:
                    score += count
                    matched_keywords.append(keyword)
            
            context_scores[context_type] = {
                'score': score,
                'keywords': matched_keywords
            }
        
        # Determinar contexto principal
        main_context = max(context_scores, key=lambda x: context_scores[x]['score'])
        
        # Se nenhum contexto específico, assumir clínica
        if context_scores[main_context]['score'] == 0:
            main_context = 'clinica'
        
        return {
            'main_context': main_context,
            'confidence': context_scores[main_context]['score'],
            'matched_keywords': context_scores[main_context]['keywords'],
            'all_scores': context_scores
        }
    
    def get_specialized_prompt(self, context_type: str, patient_info: str, transcription: str) -> Dict:
        """Retorna prompts especializados - SEGUINDO ORIENTAÇÕES ESPECÍFICAS"""
        
        prompts = {
            'bpc': {
                'anamnese_prompt': f"""
Gere uma ANAMNESE PARA BPC seguindo EXATAMENTE o modelo estabelecido:

DADOS FORNECIDOS: {patient_info}
TRANSCRIÇÃO DA CONSULTA: {transcription}

ESTRUTURA OBRIGATÓRIA:

## 1. 📋 IDENTIFICAÇÃO DO PACIENTE
- **Nome:** [extrair dos dados fornecidos]
- **Idade:** [extrair dos dados]
- **Sexo:** [extrair ou inferir dos dados]
- **Profissão:** [extrair se mencionado]
- **Documento de identificação:** [RG/CPF se fornecido]
- **Número de processo ou referência:** [se mencionado na transcrição]

## 2. 🗣️ QUEIXA PRINCIPAL
- **Motivo da consulta:** [extrair da transcrição - ex.: BPC, afastamento, isenção IR]
- **Solicitação específica:** [detalhar pedido baseado na transcrição]
- **Solicitação do advogado:** [se houver menção]

## 3. 📖 HISTÓRIA DA DOENÇA ATUAL (HDA)
- **Data de início dos sintomas e/ou diagnóstico:** [extrair da transcrição]
- **Fatores desencadeantes ou agravantes:** [ex.: acidente, agravamento laboral]
- **Tratamentos realizados e resultados:** [medicações, cirurgias, fisioterapia]
- **Situação atual:** [limitações, sintomas persistentes]

## 4. 🏥 ANTECEDENTES PESSOAIS E FAMILIARES RELEVANTES
- **Doenças prévias:** [crônicas, degenerativas, psiquiátricas]
- **Histórico ocupacional e previdenciário:** [atividade laboral, contribuições]

## 5. 📄 DOCUMENTAÇÃO APRESENTADA
- **Exames complementares, relatórios, prontuários:** [documentos anexados]
- **Observação:** [suficiência e consistência dos documentos]

## 6. 🎥 EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)
- **Relato de autoavaliação guiada:** [força, mobilidade, dor]
- **Observação visual por vídeo:** [quando possível]
- **Limitações funcionais observadas ou relatadas:** [especificar]

## 7. ⚕️ AVALIAÇÃO MÉDICA (ASSESSMENT)
- **Hipótese diagnóstica ou confirmação de CID-10:** [código específico]

**MODALIDADE:** Telemedicina - Consulta para avaliação de BPC
**DATA:** {datetime.now().strftime('%d/%m/%Y')}
""",
                'laudo_prompt': f"""
Gere um LAUDO MÉDICO PARA BPC seguindo EXATAMENTE a estrutura de 6 pontos:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

## 🏥 LAUDO MÉDICO PARA BPC/LOAS

### 📋 IDENTIFICAÇÃO
- **Paciente:** [nome completo extraído dos dados]
- **Data:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}
- **Modalidade:** Teleconsulta médica
- **Finalidade:** Benefício de Prestação Continuada (BPC/LOAS)

### 1. 📖 HISTÓRIA CLÍNICA
Relato detalhado do quadro clínico, início e evolução dos sintomas, antecedentes e contexto, com datas sempre que possível:

[Desenvolver narrativa detalhada baseada na transcrição, incluindo:]
- Início dos sintomas com data específica quando mencionada
- Evolução da condição ao longo do tempo
- Antecedentes médicos relevantes
- Contexto das limitações atuais

### 2. 🚫 LIMITAÇÃO FUNCIONAL
Descrição clara das limitações nas atividades diárias:

[Baseado na transcrição, detalhar:]
- Atividades básicas de vida diária comprometidas
- Dependência para cuidados pessoais
- Restrições na participação social
- Grau de autonomia atual
- Necessidade de cuidador

### 3. 🔬 EXAMES (Quando Houver)
[Se documentos foram anexados:]
- Lista e análise objetiva dos exames apresentados, citando sempre a data de realização
- Resultados relevantes para o diagnóstico
- Consistência com o quadro clínico

[Se não há exames:] Nenhum exame complementar apresentado na consulta.

### 4. 💊 TRATAMENTO
Tratamentos realizados, duração, resposta apresentada, mudanças de conduta e orientações, sempre que possível com datas:

[Baseado na transcrição, incluir:]
- Medicações utilizadas e duração
- Cirurgias ou procedimentos realizados
- Fisioterapia ou reabilitação
- Resposta aos tratamentos
- Orientações médicas atuais

### 5. 🔮 PROGNÓSTICO
Expectativa de evolução, previsão de recuperação, possibilidade de agravamento ou manutenção das limitações:

[Avaliar baseado no caso:]
- Possibilidade de recuperação funcional
- Caráter permanente das limitações
- Progressão esperada da condição
- Necessidade de cuidados continuados

### 6. ⚖️ CONCLUSÃO - ALINHADA AO BENEFÍCIO BPC

**CID-10:** [código específico da condição]

**Para BPC/LOAS - Modelo EXATO conforme orientação:**

O paciente apresenta **impedimento de longo prazo**, de natureza **[física/mental/intelectual/sensorial]**, com **restrição permanente para o desempenho de atividades de vida diária e participação social**. 

Tais limitações, iniciadas em **[data quando disponível]**, enquadram-se nos critérios exigidos para o benefício assistencial.

**IMPORTANTE:** Evitar menção à incapacidade laboral. Focar em vida independente e participação social.

**PARECER:** FAVORÁVEL ao deferimento do BPC/LOAS.

### ⚠️ OBSERVAÇÕES TELEMEDICINA
- Avaliação baseada em relato do paciente via teleconsulta
- Limitações inerentes ao exame remoto
- Documentação complementar recomendada quando necessário

**Médico Responsável:** ________________________
**CRM:** ________________________
**Data:** {datetime.now().strftime('%d/%m/%Y')}
"""
            },
            
            'incapacidade': {
                'anamnese_prompt': f"""
Gere uma ANAMNESE PARA INCAPACIDADE LABORAL seguindo EXATAMENTE o modelo:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

ESTRUTURA OBRIGATÓRIA:

## 1. 📋 IDENTIFICAÇÃO DO PACIENTE
- **Nome:** [extrair dos dados]
- **Idade:** [extrair]
- **Sexo:** [extrair/inferir]
- **Profissão:** [atividade laboral exercida]
- **Documento de identificação:** [RG/CPF se disponível]
- **Número de processo ou referência:** [se mencionado]

## 2. 🗣️ QUEIXA PRINCIPAL
- **Motivo da consulta:** [afastamento, auxílio-doença, aposentadoria]
- **Solicitação específica do advogado:** [se houver]

## 3. 📖 HISTÓRIA DA DOENÇA ATUAL (HDA)
- **Data de início dos sintomas e/ou diagnóstico:** [quando começaram]
- **Fatores desencadeantes ou agravantes:** [acidente de trabalho, esforço repetitivo]
- **Tratamentos realizados e resultados:** [medicações, fisioterapia, cirurgias]
- **Situação atual:** [limitações, sintomas persistentes]

## 4. 🏥 ANTECEDENTES PESSOAIS E FAMILIARES RELEVANTES
- **Doenças prévias:** [crônicas, degenerativas, psiquiátricas]
- **Histórico ocupacional e previdenciário:** [atividade laboral, contribuições]

## 5. 📄 DOCUMENTAÇÃO APRESENTADA
- **Exames complementares, relatórios, prontuários:** [documentos anexados]
- **Observação:** [suficiência e consistência dos documentos]

## 6. 🎥 EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)
- **Relato de autoavaliação guiada:** [força, mobilidade, dor]
- **Observação visual por vídeo:** [quando possível]
- **Limitações funcionais observadas ou relatadas:** [específicas para o trabalho]

## 7. ⚕️ AVALIAÇÃO MÉDICA (ASSESSMENT)
- **Hipótese diagnóstica ou confirmação de CID-10:** [código específico]

**MODALIDADE:** Telemedicina - Avaliação de incapacidade laboral
**DATA:** {datetime.now().strftime('%d/%m/%Y')}
""",
                'laudo_prompt': f"""
LAUDO PARA INCAPACIDADE LABORAL - ESTRUTURA DE 6 PONTOS:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

## 🏥 LAUDO PARA BENEFÍCIO POR INCAPACIDADE LABORATIVA

### 📋 IDENTIFICAÇÃO
- **Segurado:** [nome completo]
- **Data:** {datetime.now().strftime('%d/%m/%Y')}
- **Modalidade:** Teleconsulta médica
- **Finalidade:** Auxílio-doença/Aposentadoria por invalidez

### 1. 📖 HISTÓRIA CLÍNICA
Relato detalhado do quadro clínico, início e evolução dos sintomas, antecedentes e contexto, com datas sempre que possível:

[Narrativa baseada na transcrição]

### 2. 🚫 LIMITAÇÃO FUNCIONAL
Descrição clara das limitações nas atividades diárias.

**CORRELAÇÃO OBRIGATÓRIA COM A PROFISSÃO:**
As limitações atuais impedem o exercício da função de **[profissão extraída dos dados]**, especialmente para atividades que demandam **[especificar baseado na transcrição: levantamento de peso, longos períodos em pé, movimentos repetitivos, etc.]**.

### 3. 🔬 EXAMES (Quando Houver)
Lista e análise objetiva dos exames apresentados, citando sempre a data de realização.

[Se não há exames:] Nenhum exame complementar apresentado na consulta.

### 4. 💊 TRATAMENTO
Tratamentos realizados, duração, resposta apresentada, mudanças de conduta e orientações, sempre que possível com datas.

### 5. 🔮 PROGNÓSTICO
Expectativa de evolução, previsão de recuperação, possibilidade de agravamento ou manutenção das limitações.

### 6. ⚖️ CONCLUSÃO - INCAPACIDADE LABORATIVA

**CID-10:** [código específico da condição]

**Modelo EXATO conforme orientação:**

Diante do quadro clínico, **[exames quando houver]** e limitação funcional descritos, conclui-se que o(a) paciente encontra-se **incapacitado(a) para o exercício de sua atividade habitual** desde **[data quando disponível]**, recomendando-se afastamento das funções laborativas por **[tempo determinado/indeterminado]**, com reavaliação periódica.

**Justificativa:** Fundamentar a incapacidade para o trabalho exercido, justificando o nexo entre a doença, as limitações e a impossibilidade de desempenho das funções profissionais.

### ⚠️ OBSERVAÇÕES TELEMEDICINA
- Avaliação baseada em anamnese e observação remota
- Limitações do exame físico à distância

**CRM:** ________________________
**Especialidade:** [área de atuação]
**Data:** {datetime.now().strftime('%d/%m/%Y')}
"""
            },
            
            'auxilio_acidente': {
                'anamnese_prompt': f"""
ANAMNESE PARA AUXÍLIO-ACIDENTE seguindo o modelo estabelecido:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

[Mesma estrutura de 7 pontos, focando em sequelas de acidente de trabalho]
""",
                'laudo_prompt': f"""
LAUDO PARA AUXÍLIO-ACIDENTE - ESTRUTURA DE 6 PONTOS:

### 6. ⚖️ CONCLUSÃO - AUXÍLIO-ACIDENTE

**CID-10:** [código específico da sequela]

**Modelo EXATO conforme orientação:**

Há **redução permanente da capacidade laborativa**, com diminuição do desempenho para atividades que exigem **[especificar tipo de esforço baseado na transcrição]**, embora ainda possível exercer parte das funções, com necessidade de adaptações e restrição de determinadas tarefas.

**Pontos obrigatórios:**
- Redução da capacidade laboral residual
- Tipo de redução e se permite exercício parcial
- Impacto econômico

**PARECER:** FAVORÁVEL ao auxílio-acidente pela redução da capacidade laborativa.
"""
            },
            
            'isencao_ir': {
                'anamnese_prompt': f"""
ANAMNESE PARA ISENÇÃO DE IMPOSTO DE RENDA seguindo o modelo:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

[Estrutura de 7 pontos focando em doença grave]
""",
                'laudo_prompt': f"""
LAUDO PARA ISENÇÃO DE IMPOSTO DE RENDA - ESTRUTURA DE 6 PONTOS:

### 6. ⚖️ CONCLUSÃO - ISENÇÃO IMPOSTO DE RENDA

**CID-10:** [código específico]

**Modelo EXATO conforme orientação:**

O paciente é portador de **[nome da doença extraída da transcrição]**, diagnosticada em **[data do diagnóstico quando mencionada]**, condição esta que se enquadra no rol de doenças graves previstas na legislação, justificando a solicitação de isenção do imposto de renda.

**Pontos obrigatórios:**
- Tempo da doença
- Diagnóstico específico
- Correspondência com rol legal
- Evitar linguagem subjetiva

**PARECER:** FAVORÁVEL à isenção de imposto de renda.
"""
            },
            
            'pericia': {
                'anamnese_prompt': f"""
ANAMNESE PERICIAL seguindo o modelo estabelecido:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

[Estrutura de 7 pontos para perícia legal]
""",
                'laudo_prompt': f"""
LAUDO PERICIAL - ESTRUTURA DE 6 PONTOS:

### 1. 📖 HISTÓRIA CLÍNICA
Relato detalhado do quadro clínico, início e evolução dos sintomas, antecedentes e contexto, com datas sempre que possível.

### 2. 🚫 LIMITAÇÃO FUNCIONAL
Descrição clara das limitações nas atividades diárias.
Correlacionar com a profissão quando pertinente.

### 3. 🔬 EXAMES (Quando Houver)
Lista e análise objetiva dos exames apresentados, citando sempre a data de realização.

### 4. 💊 TRATAMENTO
Tratamentos realizados, duração, resposta apresentada, mudanças de conduta e orientações, sempre que possível com datas.

### 5. 🔮 PROGNÓSTICO
Expectativa de evolução, previsão de recuperação, possibilidade de agravamento ou manutenção das limitações.

### 6. ⚖️ CONCLUSÃO PERICIAL
[Conclusão específica baseada no caso, respondendo aos quesitos]
"""
            },
            
            'clinica': {
                'anamnese_prompt': f"""
ANAMNESE CLÍNICA seguindo EXATAMENTE o modelo estabelecido:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

ESTRUTURA OBRIGATÓRIA:

## 1. 📋 IDENTIFICAÇÃO DO PACIENTE
- **Nome:** [extrair dos dados]
- **Idade:** [extrair]
- **Sexo:** [extrair/inferir]
- **Profissão:** [se mencionada]
- **Documento de identificação:** [RG/CPF se fornecido]
- **Número de processo ou referência:** [se aplicável]

## 2. 🗣️ QUEIXA PRINCIPAL
- **Motivo da consulta:** [extrair da transcrição]
- **Solicitação específica do advogado:** [se houver]

## 3. 📖 HISTÓRIA DA DOENÇA ATUAL (HDA)
- **Data de início dos sintomas e/ou diagnóstico:** [extrair da transcrição]
- **Fatores desencadeantes ou agravantes:** [ex.: acidente, agravamento laboral]
- **Tratamentos realizados e resultados:** [medicações, cirurgias, fisioterapia]
- **Situação atual:** [limitações, sintomas persistentes]

## 4. 🏥 ANTECEDENTES PESSOAIS E FAMILIARES RELEVANTES
- **Doenças prévias:** [crônicas, degenerativas, psiquiátricas]
- **Histórico ocupacional e previdenciário:** [atividade laboral, contribuições]

## 5. 📄 DOCUMENTAÇÃO APRESENTADA
- **Exames complementares, relatórios, prontuários:** [documentos anexados]
- **Observação:** [suficiência e consistência dos documentos]

## 6. 🎥 EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)
- **Relato de autoavaliação guiada:** [força, mobilidade, dor]
- **Observação visual por vídeo:** [quando possível]
- **Limitações funcionais observadas ou relatadas:** [especificar]

## 7. ⚕️ AVALIAÇÃO MÉDICA (ASSESSMENT)
- **Hipótese diagnóstica ou confirmação de CID-10:** [código específico]

**MODALIDADE:** Teleconsulta médica
**DATA:** {datetime.now().strftime('%d/%m/%Y')}
""",
                'laudo_prompt': f"""
RELATÓRIO MÉDICO - TELECONSULTA seguindo ESTRUTURA DE 6 PONTOS:

## 🏥 RELATÓRIO DE TELECONSULTA

### 📋 IDENTIFICAÇÃO
- **Paciente:** [nome completo]
- **Data:** {datetime.now().strftime('%d/%m/%Y às %H:%M')}
- **Modalidade:** Telemedicina
- **Tipo:** Consulta clínica geral

### 1. 📖 HISTÓRIA CLÍNICA
Relato detalhado do quadro clínico, início e evolução dos sintomas, antecedentes e contexto, com datas sempre que possível.

### 2. 🚫 LIMITAÇÃO FUNCIONAL
Descrição clara das limitações nas atividades diárias.

### 3. 🔬 EXAMES (Quando Houver)
Lista e análise objetiva dos exames apresentados, citando sempre a data de realização.

### 4. 💊 TRATAMENTO
Tratamentos realizados, duração, resposta apresentada, mudanças de conduta e orientações, sempre que possível com datas.

### 5. 🔮 PROGNÓSTICO
Expectativa de evolução, previsão de recuperação, possibilidade de agravamento ou manutenção das limitações.

### 6. ⚖️ CONCLUSÃO CLÍNICA

**CID-10:** [código da condição]

[Conclusão baseada na avaliação clínica]

### ⚠️ LIMITAÇÕES DA TELEMEDICINA
- Exame físico restrito à observação visual
- Recomenda-se consulta presencial se necessário

**Médico Responsável:** ________________________
**CRM:** ________________________
**Data:** {datetime.now().strftime('%d/%m/%Y')}
"""
            }
        }
        
        # Retornar prompt do contexto específico ou clínica como fallback
        return prompts.get(context_type, prompts['clinica'])

# Instância global
context_classifier = ContextClassifierService()