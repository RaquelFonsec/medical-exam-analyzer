import re
from typing import Dict, List, Tuple

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
                'trabalho', 'profissao', 'funcao', 'atividade laboral', 'carregar peso'
            ],
            'pericia': [
                'pericia medica', 'avaliacao pericial', 'junta medica',
                'exame pericial', 'laudo pericial', 'capacidade laboral',
                'nexo causal', 'acidente de trabalho', 'dano corporal',
                'sequela', 'invalidez', 'incapacidade', 'grau de comprometimento'
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
        """Retorna prompts especializados baseados no contexto"""
        
        prompts = {
            'bpc': {
                'anamnese_prompt': f"""
Gere uma ANAMNESE ESPECÍFICA PARA BPC (Benefício de Prestação Continuada):

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

ESTRUTURA OBRIGATÓRIA PARA BPC:

## 📋 IDENTIFICAÇÃO SOCIAL
- Nome completo: [extrair dos dados]
- Idade: [extrair dos dados]
- RG/CPF: [se disponível]
- Composição familiar: [investigar se mencionado]
- Renda familiar per capita: [investigar se mencionado]

## 🏥 DEFICIÊNCIA/INCAPACIDADE IDENTIFICADA
- Tipo de deficiência: [física/mental/intelectual/sensorial baseado na transcrição]
- CID-10 principal: [código específico da condição]
- Data de início da condição: [quando começou conforme relato]
- Evolução: [progressiva/estável/regressiva]

## 🏠 AVALIAÇÃO DA VIDA INDEPENDENTE
- Atividades básicas de vida diária (ABVD):
  * Alimentação: [consegue/não consegue/precisa ajuda]
  * Higiene pessoal: [consegue/não consegue/precisa ajuda]
  * Vestir-se: [consegue/não consegue/precisa ajuda]
  * Locomoção: [consegue/não consegue/precisa ajuda]
  * Controle esfincteriano: [consegue/não consegue/precisa ajuda]

- Atividades instrumentais de vida diária (AIVD):
  * Preparar refeições: [consegue/não consegue]
  * Fazer compras: [consegue/não consegue]
  * Gerenciar medicações: [consegue/não consegue]
  * Usar transporte: [consegue/não consegue]

## 👥 NECESSIDADE DE CUIDADOR
- Necessita de cuidador: [SIM/NÃO]
- Tipo de cuidado necessário: [total/parcial/supervisão]
- Quem é o cuidador atual: [familiar/profissional/ninguém]

## 🏡 IMPACTO SOCIAL
- Consegue viver sozinho: [SIM/NÃO]
- Impedimentos para vida independente: [listar específicos]
- Adaptações ambientais necessárias: [se aplicável]

FOCO ESPECÍFICO BPC: Avaliar impedimentos para VIDA INDEPENDENTE, não capacidade laboral.
""",
                'laudo_prompt': f"""
Gere um LAUDO MÉDICO ESPECÍFICO PARA BPC (LOAS):

CONTEXTO: Benefício de Prestação Continuada - Assistência Social
DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

ESTRUTURA OBRIGATÓRIA PARA BPC:

## 🏥 IDENTIFICAÇÃO E DIAGNÓSTICO
- **Paciente:** [nome e dados básicos]
- **CID-10 Principal:** [código específico da deficiência]
- **Diagnósticos Secundários:** [se relevantes]
- **Data de início da condição:** [baseado no relato]

## 🔍 DESCRIÇÃO DA DEFICIÊNCIA
- **Natureza da deficiência:** [física/mental/intelectual/sensorial]
- **Grau de comprometimento:** [leve/moderado/grave/total]
- **Característica:** [permanente/temporária]
- **Prognóstico:** [reversível/irreversível/estável/progressivo]

## 🏠 AVALIAÇÃO FUNCIONAL PARA VIDA INDEPENDENTE
### Atividades Básicas de Vida Diária (ABVD):
- **Alimentação:** [independente/dependente/supervisão necessária]
- **Higiene corporal:** [independente/dependente/supervisão necessária]
- **Vestuário:** [independente/dependente/supervisão necessária]
- **Mobilidade:** [independente/dependente/supervisão necessária]
- **Transferências:** [independente/dependente/supervisão necessária]

### Atividades Instrumentais de Vida Diária (AIVD):
- **Preparo de refeições:** [capaz/incapaz]
- **Gerenciamento de medicações:** [capaz/incapaz]
- **Atividades domésticas:** [capaz/incapaz]
- **Manejo financeiro:** [capaz/incapaz]

## 👥 NECESSIDADE DE CUIDADOS DE TERCEIROS
- **Necessita de cuidador:** SIM/NÃO
- **Tipo de cuidado:** [total/parcial/supervisão/orientação]
- **Frequência:** [24h/diário/ocasional]
- **Atividades que necessita ajuda:** [especificar]

## ⚖️ CONCLUSÃO PERICIAL PARA BPC
### Critérios LOAS - Lei 8.742/93:
1. **A pessoa possui deficiência que a impede de vida independente?** 
   - **RESPOSTA:** SIM/NÃO
   - **Justificativa:** [baseada na avaliação funcional]

2. **A deficiência é de longo prazo (mínimo 2 anos)?**
   - **RESPOSTA:** SIM/NÃO
   - **Justificativa:** [baseada no prognóstico]

3. **Há impedimento de participação plena e efetiva na sociedade?**
   - **RESPOSTA:** SIM/NÃO
   - **Justificativa:** [baseada nas limitações identificadas]

## 📋 RECOMENDAÇÃO FINAL
- **PARECER:** FAVORÁVEL/DESFAVORÁVEL ao deferimento do BPC
- **CID-10 para fins de benefício:** [código principal]
- **Necessidade de reavaliação:** SIM/NÃO
- **Prazo para reavaliação:** [se aplicável]

## ⚠️ OBSERVAÇÕES IMPORTANTES
- Avaliação baseada exclusivamente em critérios de vida independente
- Não considera capacidade laboral (critério diferente do auxílio-doença)
- Laudo específico para fins de BPC/LOAS conforme legislação vigente

**IMPORTANTE:** Este laudo atesta especificamente os impedimentos para vida independente, critério essencial para concessão do BPC.
"""
            },
            
            'incapacidade': {
                'anamnese_prompt': f"""
Gere uma ANAMNESE ESPECÍFICA PARA INCAPACIDADE LABORAL:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

ESTRUTURA PARA PERÍCIA DE INCAPACIDADE:

## 👤 IDENTIFICAÇÃO TRABALHISTA
- Nome: [extrair dos dados]
- Idade: [extrair dos dados]
- Profissão/Função: [atividade laboral exercida]
- Empresa/Local de trabalho: [se mencionado]
- Tempo na função atual: [anos/meses se relatado]
- Tempo total de trabalho: [se disponível]

## 💼 DESCRIÇÃO DA ATIVIDADE LABORAL
- Função exercida: [detalhes do trabalho]
- Atividades principais: [o que faz no trabalho]
- Esforço físico exigido: [leve/moderado/pesado]
- Posturas predominantes: [em pé/sentado/agachado/etc]
- Carga horária: [se mencionada]
- Ambiente de trabalho: [condições se relatadas]

## 🏥 INCAPACIDADE LABORAL ATUAL
- Data de início dos sintomas: [quando começou]
- Relação com o trabalho: [ocupacional/agravamento/sem relação]
- Sintomas que impedem o trabalho: [listar específicos da transcrição]
- Limitações funcionais específicas: [o que não consegue fazer]
- Dor durante atividade laboral: [intensidade e características]

## ⚖️ AVALIAÇÃO DA CAPACIDADE LABORAL
- Consegue exercer a função habitual? [SIM/NÃO]
- Limitações para função específica: [detalhar impedimentos]
- Consegue exercer outra função? [SIM/NÃO]
- Limitações para qualquer trabalho: [se aplicável]
- Necessidade de afastamento: [temporário/permanente]

## 🔄 PROGNÓSTICO LABORAL
- Tempo estimado para recuperação: [dias/meses/indefinido]
- Possibilidade de retorno à função: [provável/improvável/impossível]
- Necessidade de reabilitação: [SIM/NÃO]
- Mudança de função necessária: [SIM/NÃO]

FOCO: Capacidade/incapacidade específica para o TRABALHO e atividade laboral.
""",
                'laudo_prompt': f"""
Gere um LAUDO MÉDICO PARA INCAPACIDADE LABORAL (INSS):

CONTEXTO: Perícia para Auxílio-Doença/Aposentadoria por Invalidez
DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

ESTRUTURA PARA PERÍCIA INSS:

## 🏥 DIAGNÓSTICO MÉDICO OCUPACIONAL
- **CID-10 Principal:** [código relacionado à incapacidade]
- **CID-10 Secundários:** [se relevantes para incapacidade]
- **Natureza da doença:** [ocupacional/comum/acidente de trabalho]
- **Evolução:** [aguda/crônica/progressiva/estável]
- **Data do início:** [quando começaram os sintomas]

## 💼 ANÁLISE DA ATIVIDADE LABORAL
- **Profissão:** [função exercida]
- **Demandas físicas da função:** [esforços exigidos]
- **Posturas de trabalho:** [predominantes na atividade]
- **Movimentos repetitivos:** [se presentes]
- **Carga de trabalho:** [física/mental]

## ⚖️ AVALIAÇÃO DA CAPACIDADE LABORAL
### Para a função habitual:
- **Capaz de exercer função habitual:** SIM/NÃO
- **Limitações específicas:** [impedimentos para a profissão]
- **Movimentos limitados:** [quais não consegue realizar]
- **Carga de peso suportada:** [limitações específicas]

### Para qualquer trabalho:
- **Capaz de exercer qualquer trabalho:** SIM/NÃO
- **Limitações gerais:** [impedimentos para qualquer atividade]
- **Adaptações necessárias:** [se aplicável]

## 📊 CLASSIFICAÇÃO DA INCAPACIDADE
- **Tipo:** Temporária/Permanente
- **Grau:** Parcial/Total
- **Para função habitual:** Incapaz/Capaz com restrições/Capaz
- **Para qualquer trabalho:** Incapaz/Capaz com restrições/Capaz

## 🔄 PROGNÓSTICO OCUPACIONAL
- **Recuperação esperada:** [tempo estimado]
- **Retorno ao trabalho:** Provável/Improvável/Impossível
- **Mesma função:** Sim/Não/Com adaptações
- **Reabilitação profissional:** Necessária/Desnecessária
- **Readaptação funcional:** Indicada/Contraindicada

## ⚖️ CONCLUSÃO PERICIAL INSS
### Parecer Final:
- **APTO/INAPTO** para o trabalho
- **Tempo de afastamento necessário:** [dias/meses/indefinido]
- **Data estimada de retorno:** [se aplicável]
- **Incapacidade:** Temporária/Permanente
- **Grau:** Parcial/Total

### Recomendações Previdenciárias:
- **Auxílio-doença:** Indicado/Não indicado
- **Aposentadoria por invalidez:** Indicada/Não indicada
- **Reabilitação profissional:** Necessária/Desnecessária

## 📋 CID-10 PARA FINS PREVIDENCIÁRIOS
- **Principal:** [código para benefício]
- **Secundários:** [se influenciarem na incapacidade]

**IMPORTANTE:** Laudo específico para avaliação de capacidade laboral conforme critérios do INSS.
"""
            },
            
            'pericia': {
                'anamnese_prompt': f"""
Gere uma ANAMNESE PERICIAL MÉDICA LEGAL:

DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

ESTRUTURA PERICIAL COMPLETA:

## 👤 IDENTIFICAÇÃO DO PERICIANDO
- Nome completo: [extrair dos dados]
- Idade: [extrair dos dados]
- Documento de identidade: [se disponível]
- Motivo da perícia: [determinar baseado no contexto]
- Quesitos a responder: [se mencionados]
- Data do evento: [se relatado acidente/doença]

## 📋 HISTÓRIA CLÍNICA PERICIAL
- Fatos médicos relevantes para perícia: [cronologia baseada na transcrição]
- Data e circunstâncias do evento: [acidente/doença/lesão]
- Evolução desde o evento: [melhora/piora/estabilidade]
- Tratamentos realizados: [se mencionados]
- Sequelas apresentadas: [atuais]

## 🔍 EXAME PERICIAL ATUAL
- Estado geral atual: [baseado nos relatos]
- Sequelas identificadas: [físicas/mentais/funcionais]
- Limitações funcionais: [específicas encontradas]
- Grau de comprometimento: [leve/moderado/grave]
- Capacidade funcional residual: [o que ainda consegue fazer]

## ⚖️ NEXO CAUSAL PERICIAL
- Relação entre evento e lesão/doença: [investigar]
- Nexo temporal: [compatibilidade de datas]
- Nexo topográfico: [local da lesão compatível]
- Nexo etiológico: [causa compatível com efeito]

FOCO: Estabelecer NEXO CAUSAL e avaliar grau de comprometimento/sequelas.
""",
                'laudo_prompt': f"""
Gere um LAUDO PERICIAL MÉDICO LEGAL:

CONTEXTO: Perícia Médica Legal/Judicial
DADOS: {patient_info}
TRANSCRIÇÃO: {transcription}

ESTRUTURA TÉCNICA PERICIAL:

## 🏥 DIAGNÓSTICO PERICIAL
- **CID-10 Principal:** [código da condição periciada]
- **CID-10 Secundários:** [se relevantes]
- **Natureza da lesão/doença:** [traumática/degenerativa/ocupacional]
- **Data do evento:** [quando ocorreu]
- **Data do exame pericial:** [atual]

## 🔍 DESCRIÇÃO DAS SEQUELAS
- **Sequelas anatômicas:** [alterações estruturais permanentes]
- **Sequelas funcionais:** [limitações de movimento/força]
- **Sequelas estéticas:** [deformidades visíveis]
- **Sequelas psíquicas:** [se aplicável]

## ⚖️ ANÁLISE DO NEXO CAUSAL
### Nexo Temporal:
- **Compatibilidade temporal:** SIM/NÃO
- **Justificativa:** [análise das datas]

### Nexo Topográfico:
- **Compatibilidade anatômica:** SIM/NÃO
- **Justificativa:** [relação local evento/lesão]

### Nexo Etiológico:
- **Causa compatível com efeito:** SIM/NÃO
- **Justificativa:** [mecanismo lesional]

### Nexo Causal Estabelecido:
- **CONCLUSÃO:** SIM/NÃO/PROVÁVEL/IMPROVÁVEL

## 📊 AVALIAÇÃO DO DANO CORPORAL
- **Grau de incapacidade:** [percentual se aplicável]
- **Tipo de incapacidade:** Temporária/Permanente
- **Extensão:** Parcial/Total
- **Natureza:** Reversível/Irreversível

## 💼 REPERCUSSÃO LABORAL
- **Incapacidade para trabalho habitual:** SIM/NÃO
- **Incapacidade para qualquer trabalho:** SIM/NÃO
- **Necessidade de mudança de função:** SIM/NÃO
- **Redução da capacidade laborativa:** [percentual]

## 🔄 PROGNÓSTICO PERICIAL
- **Estabilização das sequelas:** Sim/Não/Parcial
- **Possibilidade de melhora:** Sim/Não/Limitada
- **Necessidade de tratamento continuado:** Sim/Não
- **Consolidação das lesões:** Completa/Incompleta

## ⚖️ CONCLUSÕES PERICIAIS
### Respostas aos Quesitos (se aplicável):
1. **Há dano corporal?** SIM/NÃO
2. **Existe nexo causal?** SIM/NÃO
3. **Qual o grau de incapacidade?** [percentual]
4. **A incapacidade é permanente?** SIM/NÃO
5. **Há necessidade de tratamento?** SIM/NÃO

### Classificação Legal do Dano:
- **Dano corporal:** [tipo e extensão]
- **Incapacidade laborativa:** [grau e natureza]
- **Invalidez:** [parcial/total se aplicável]

## 📋 CONSIDERAÇÕES FINAIS
- **CID-10 para fins periciais:** [código principal]
- **Consolidação das sequelas:** [data estimada]
- **Necessidade de nova avaliação:** SIM/NÃO
- **Prazo para reavaliação:** [se aplicável]

**IMPORTANTE:** Laudo elaborado com imparcialidade técnica e fundamentação científica conforme princípios da medicina legal.
"""
            },
            
            'clinica': {
                'anamnese_prompt': f"""
Gere uma ANAMNESE CLÍNICA GERAL:

DADOS: {patient_info}
TRANSCR.: {transcription}

ESTRUTURA:

## IDENTIFICAÇÃO
- Nome: [extrair dos dados]
- Idade: [extrair dos dados]
- Sexo: [se mencionado]

## QUEIXA PRINCIPAL
[Extrair da transcrição o motivo da consulta]

## HISTÓRIA DA DOENÇA ATUAL
[Cronologia dos sintomas baseada na transcrição]

## REVISÃO DE SISTEMAS
[Sintomas mencionados por sistemas]

## EXAME FÍSICO
[Se mencionado na transcrição]

## MEDICAÇÕES EM USO
[Se mencionadas]

FOCO: Consulta médica geral e acompanhamento.
""",
                'laudo_prompt': f"""
Gere um LAUDO CLÍNICO GERAL:

CONTEXTO: Consulta Médica Regular
DADOS: {patient_info}

ESTRUTURA:

## DIAGNÓSTICO CLÍNICO
[Baseado nos sintomas e dados fornecidos]

## AVALIAÇÃO
[Estado geral do paciente]

## PLANO TERAPÊUTICO
[Tratamento recomendado]

## SEGUIMENTO
[Orientações de acompanhamento]

## OBSERVAÇÕES
[Informações adicionais relevantes]

IMPORTANTE: Linguagem médica adequada para consulta clínica.
"""
            }
        }
        
        # Retornar prompt do contexto específico ou clínica como fallback
        return prompts.get(context_type, prompts['clinica'])

# Instância global
context_classifier = ContextClassifierService()
