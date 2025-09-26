# llm.py
import openai
import asyncio
import logging
import os
import re
from typing import Dict, List
from datetime import datetime

# Configurações
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

logger = logging.getLogger(__name__)

class InterpretadorLLM:
    """Interpretador universal de documentos - Médicos, Jurídicos, Financeiros, Técnicos, etc."""
    
    def __init__(self):
        if OPENAI_API_KEY:
            self.client = openai.OpenAI(
                api_key=OPENAI_API_KEY,
                timeout=480.0,  # 8 minutos
                max_retries=3
            )
            logger.info("OpenAI LLM configurado")
        else:
            self.client = None
            logger.error("OpenAI API Key não encontrada para LLM")
    
    async def interpretar_exame_para_frontend(self, texto_extraido: str, nome_arquivo: str, patient_info: Dict = None) -> Dict:
        """Interpreta qualquer tipo de documento de forma inteligente - COMPATÍVEL COM FRONTEND EXISTENTE"""
        
        if not self.client:
            return {
                'success': False,
                'error': 'OpenAI API Key não configurada no arquivo .env',
                'llm_analysis': {}
            }
        
        try:
            logger.info(f"Interpretando documento: {nome_arquivo}")
            
            # Detectar tipo de documento automaticamente
            tipo_documento = self._detectar_tipo_documento(texto_extraido, nome_arquivo)
            
            # Gerar prompt específico para o tipo de documento
            prompt = self._gerar_prompt_contextual(texto_extraido, nome_arquivo, tipo_documento, patient_info)
            
            logger.info(f"Tipo de documento detectado: {tipo_documento}")
            
            # Chamar OpenAI
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_system_prompt(tipo_documento)
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=16000,
                    temperature=0.2
                ),
                timeout=480  # 8 minutos
            )
            
            interpretacao = response.choices[0].message.content.strip()
            
            logger.info(f"Interpretação concluída: {len(interpretacao)} caracteres")
            
            # Verificar se a interpretação está completa
            # Para documentos médicos, procurar "ANÁLISE DE DADOS FINALIZADA"
            # Para outros, procurar "ANÁLISE FINALIZADA"
            if 'MEDICO' in tipo_documento or 'EXAME' in tipo_documento:
                esta_completa = "ANÁLISE DE DADOS FINALIZADA" in interpretacao
            else:
                esta_completa = "ANÁLISE FINALIZADA" in interpretacao
            
            if not esta_completa:
                logger.warning("Interpretação pode estar incompleta")
            
            # Extrair informações estruturadas (mantém compatibilidade com frontend)
            elementos_chave = self._extrair_achados_principais(texto_extraido)
            
            # FORMATO COMPATÍVEL COM FRONTEND EXISTENTE
            return {
                'success': True,
                'llm_analysis': {
                    'clinical_analysis': interpretacao,
                    'exam_type': tipo_documento,
                    'key_findings': elementos_chave,
                    'overall_status': self._gerar_status_geral(tipo_documento, interpretacao),
                    'document_classification': tipo_documento,
                    'processing_info': {
                        'document_type_detected': tipo_documento,
                        'analysis_complete': esta_completa,
                        'processing_timestamp': datetime.now().isoformat()
                    }
                },
                'extracted_text': texto_extraido,
                'filename': nome_arquivo,
                'model_used': 'gpt-4o',
                'interpretation_complete': esta_completa,
                'processing_timestamp': datetime.now().isoformat()
            }
            
        except asyncio.TimeoutError:
            logger.error("Timeout na interpretação LLM (8 minutos)")
            return {
                'success': False,
                'error': 'Timeout na interpretação - documento muito complexo',
                'llm_analysis': {}
            }
        except Exception as e:
            logger.error(f"Erro na interpretação LLM: {e}")
            return {
                'success': False,
                'error': str(e),
                'llm_analysis': {}
            }
    
    def _detectar_tipo_documento(self, texto: str, nome_arquivo: str) -> str:
        """Detecta automaticamente o tipo de documento"""
        texto_lower = texto.lower()
        nome_lower = nome_arquivo.lower()
        
        # DOCUMENTOS MÉDICOS (mantém lógica original)
        if any(palavra in texto_lower for palavra in [
            'hemograma', 'leucócitos', 'hemácias', 'plaquetas', 'glicose', 'colesterol',
            'exame', 'laudo', 'diagnóstico', 'paciente', 'médico', 'hospital', 'clínica',
            'tomografia', 'ressonância', 'ultrassom', 'raio-x', 'biopsia', 'cirurgia',
            'urina', 'eas', 'tsh', 't3', 't4', 'hormônio', 'citologia', 'anatomopatológico'
        ]):
            return self._identificar_tipo_documento(texto_lower)  # Usa método original
        
        # DOCUMENTOS JURÍDICOS
        elif any(palavra in texto_lower for palavra in [
            'contrato', 'acordo', 'cláusula', 'termo', 'condição', 'parte contratante',
            'lei', 'artigo', 'parágrafo', 'jurídico', 'legal', 'tribunal', 'juiz',
            'processo', 'ação', 'sentença', 'advogado', 'defensoria', 'ministério público',
            'petição', 'recurso', 'apelação', 'mandado', 'certidão', 'procuração'
        ]):
            return 'Documento Jurídico'
        
        # DOCUMENTOS FINANCEIROS
        elif any(palavra in texto_lower for palavra in [
            'balanço', 'receita', 'despesa', 'lucro', 'prejuízo', 'ativo', 'passivo',
            'demonstrativo', 'fluxo de caixa', 'orçamento', 'faturamento', 'cobrança',
            'nota fiscal', 'boleto', 'fatura', 'pagamento', 'débito', 'crédito',
            'empréstimo', 'financiamento', 'juros', 'taxa', 'investimento'
        ]):
            return 'Documento Financeiro'
        
        # DOCUMENTOS TÉCNICOS/ENGENHARIA
        elif any(palavra in texto_lower for palavra in [
            'especificação', 'projeto', 'desenho', 'planta', 'esquema', 'diagrama',
            'manual', 'procedimento', 'norma', 'padrão', 'teste', 'ensaio',
            'relatório técnico', 'análise técnica', 'engenharia', 'construção'
        ]):
            return 'Documento Técnico'
        
        # DOCUMENTOS ADMINISTRATIVOS
        elif any(palavra in texto_lower for palavra in [
            'memorando', 'ofício', 'circular', 'portaria', 'resolução', 'instrução',
            'ata', 'relatório', 'parecer', 'informativo', 'comunicado', 'edital'
        ]):
            return 'Documento Administrativo'
        
        # DOCUMENTOS ACADÊMICOS
        elif any(palavra in texto_lower for palavra in [
            'artigo', 'pesquisa', 'estudo', 'análise', 'metodologia', 'conclusão',
            'bibliografia', 'referências', 'abstract', 'resumo', 'introdução',
            'dissertação', 'tese', 'monografia', 'trabalho de conclusão'
        ]):
            return 'Documento Acadêmico'
        
        else:
            return 'Documento Geral'
    
    def _identificar_tipo_documento(self, texto_lower: str) -> str:
        """Identifica o tipo de documento médico baseado no conteúdo - EXPANDIDO PARA TODOS OS TIPOS"""
        
        # EXAMES LABORATORIAIS
        if any(palavra in texto_lower for palavra in ['hemograma', 'hemácias', 'leucócitos', 'plaquetas', 'hematócrito']):
            return 'Hemograma'
        elif any(palavra in texto_lower for palavra in ['glicose', 'colesterol', 'triglicérides', 'hdl', 'ldl', 'ureia', 'creatinina']):
            return 'Bioquímica Completa'
        elif any(palavra in texto_lower for palavra in ['urina', 'eas', 'sedimento', 'urocultura', 'proteinúria']):
            return 'Exame de Urina'
        elif any(palavra in texto_lower for palavra in ['tsh', 't3', 't4', 'hormônio', 'cortisol', 'insulina', 'prolactina']):
            return 'Exame Hormonal'
        elif any(palavra in texto_lower for palavra in ['gasometria', 'ph', 'pco2', 'po2', 'bicarbonato']):
            return 'Gasometria Arterial'
        elif any(palavra in texto_lower for palavra in ['coagulograma', 'tap', 'ttpa', 'inr', 'plaquetas']):
            return 'Coagulograma'
        elif any(palavra in texto_lower for palavra in ['eletroforese', 'proteínas', 'albumina', 'globulinas']):
            return 'Eletroforese de Proteínas'
        
        # EXAMES DE IMAGEM
        elif any(palavra in texto_lower for palavra in ['tomografia', 'tc ', 'ct ', 'contraste']):
            return 'Tomografia Computadorizada'
        elif any(palavra in texto_lower for palavra in ['ressonância', 'rm ', 'magnetic', 'gadolínio']):
            return 'Ressonância Magnética'
        elif any(palavra in texto_lower for palavra in ['ultrassom', 'ultrassonografia', 'ecografia', 'doppler']):
            return 'Ultrassom'
        elif any(palavra in texto_lower for palavra in ['raio-x', 'radiografia', 'rx ', 'tórax']):
            return 'Radiografia'
        elif any(palavra in texto_lower for palavra in ['mamografia', 'mamográfico', 'mama', 'birads']):
            return 'Mamografia'
        elif any(palavra in texto_lower for palavra in ['densitometria', 'osteoporose', 'densidade óssea']):
            return 'Densitometria Óssea'
        elif any(palavra in texto_lower for palavra in ['cintilografia', 'medicina nuclear', 'tecnécio']):
            return 'Cintilografia'
        
        # EXAMES ENDOSCÓPICOS
        elif any(palavra in texto_lower for palavra in ['endoscopia', 'eda', 'gastroscopia', 'esôfago', 'estômago']):
            return 'Endoscopia Digestiva Alta'
        elif any(palavra in texto_lower for palavra in ['colonoscopia', 'cólon', 'reto', 'sigmoidoscopia']):
            return 'Colonoscopia'
        elif any(palavra in texto_lower for palavra in ['histeroscopia', 'útero', 'endométrio']):
            return 'Histeroscopia'
        elif any(palavra in texto_lower for palavra in ['laringoscopia', 'laringe', 'cordas vocais']):
            return 'Laringoscopia'
        
        # EXAMES FUNCIONAIS CARDIOVASCULARES
        elif any(palavra in texto_lower for palavra in ['eletrocardiograma', 'ecg', 'ekg', 'ritmo cardíaco']):
            return 'Eletrocardiograma'
        elif any(palavra in texto_lower for palavra in ['ecocardiograma', 'eco', 'doppler cardíaco', 'fração de ejeção']):
            return 'Ecocardiograma'
        elif any(palavra in texto_lower for palavra in ['teste ergométrico', 'esteira', 'esforço']):
            return 'Teste Ergométrico'
        elif any(palavra in texto_lower for palavra in ['holter', '24h', 'monitização', 'arritmia']):
            return 'Holter 24h'
        elif any(palavra in texto_lower for palavra in ['mapa', 'pressão arterial', 'monitorização ambulatorial']):
            return 'MAPA'
        elif any(palavra in texto_lower for palavra in ['cateterismo', 'angiografia', 'coronárias']):
            return 'Cateterismo Cardíaco'
        
        # EXAMES FUNCIONAIS RESPIRATÓRIOS
        elif any(palavra in texto_lower for palavra in ['espirometria', 'função pulmonar', 'cvf', 'vef1']):
            return 'Espirometria'
        elif any(palavra in texto_lower for palavra in ['polissonografia', 'sono', 'apneia']):
            return 'Polissonografia'
        
        # EXAMES ANATOMOPATOLÓGICOS
        elif any(palavra in texto_lower for palavra in ['biópsia', 'histopatológico', 'anatomopatológico', 'patologia']):
            return 'Laudo Anatomopatológico'
        elif any(palavra in texto_lower for palavra in ['citologia', 'citológico', 'papanicolau', 'células']):
            return 'Citologia Oncótica'
        elif any(palavra in texto_lower for palavra in ['imunohistoquímica', 'marcadores', 'anticorpos']):
            return 'Imunohistoquímica'
        
        # DOCUMENTOS CLÍNICOS E ASSISTENCIAIS
        elif any(palavra in texto_lower for palavra in ['anamnese', 'história clínica', 'queixa principal', 'hda']):
            return 'Anamnese'
        elif any(palavra in texto_lower for palavra in ['exame físico', 'inspeção', 'palpação', 'ausculta']):
            return 'Exame Físico'
        elif any(palavra in texto_lower for palavra in ['prontuário', 'internação', 'admissão hospitalar']):
            return 'Prontuário de Internação'
        elif any(palavra in texto_lower for palavra in ['evolução médica', 'evolução', 'seguimento']):
            return 'Evolução Médica'
        elif any(palavra in texto_lower for palavra in ['evolução de enfermagem', 'enfermagem', 'cuidados']):
            return 'Evolução de Enfermagem'
        elif any(palavra in texto_lower for palavra in ['consulta', 'avaliação', 'consultor', 'ambulatório']):
            return 'Relatório de Consulta'
        elif any(palavra in texto_lower for palavra in ['sumário de alta', 'alta hospitalar', 'discharge']):
            return 'Sumário de Alta Hospitalar'
        elif any(palavra in texto_lower for palavra in ['boletim médico', 'estado geral', 'condições clínicas']):
            return 'Boletim Médico'
        
        # RELATÓRIOS CIRÚRGICOS E PROCEDIMENTOS
        elif any(palavra in texto_lower for palavra in ['cirurgia', 'cirúrgico', 'operação', 'procedimento', 'incisão']):
            return 'Relatório Cirúrgico'
        elif any(palavra in texto_lower for palavra in ['anestesia', 'anestésico', 'sedação']):
            return 'Relatório Anestésico'
        elif any(palavra in texto_lower for palavra in ['parto', 'cesariana', 'obstétrico']):
            return 'Relatório Obstétrico'
        
        # PRESCRIÇÕES E RECEITUÁRIOS
        elif any(palavra in texto_lower for palavra in ['prescrição', 'receita', 'medicamento', 'posologia']):
            return 'Prescrição Médica'
        elif any(palavra in texto_lower for palavra in ['receituário', 'medicação', 'uso contínuo']):
            return 'Receituário'
        elif any(palavra in texto_lower for palavra in ['solicitação de exames', 'pedido médico', 'solicitação']):
            return 'Solicitação de Exames'
        
        # ATESTADOS E DECLARAÇÕES
        elif any(palavra in texto_lower for palavra in ['atestado médico', 'atestado', 'licença', 'afastamento']):
            return 'Atestado Médico'
        elif any(palavra in texto_lower for palavra in ['atestado de comparecimento', 'comparecimento']):
            return 'Atestado de Comparecimento'
        elif any(palavra in texto_lower for palavra in ['declaração de óbito', 'óbito', 'causa mortis']):
            return 'Declaração de Óbito'
        elif any(palavra in texto_lower for palavra in ['atestado de sanidade', 'sanidade mental', 'capacidade']):
            return 'Atestado de Sanidade'
        
        # PARECERES E AVALIAÇÕES
        elif any(palavra in texto_lower for palavra in ['parecer médico', 'parecer', 'avaliação médica']):
            return 'Parecer Médico'
        elif any(palavra in texto_lower for palavra in ['junta médica', 'perícia', 'avaliação pericial']):
            return 'Laudo de Junta Médica'
        elif any(palavra in texto_lower for palavra in ['relatório de perícia', 'perícia médica']):
            return 'Relatório de Perícia'
        
        # DOCUMENTOS ESPECIAIS
        elif any(palavra in texto_lower for palavra in ['termo de consentimento', 'consentimento', 'autorização']):
            return 'Termo de Consentimento'
        elif any(palavra in texto_lower for palavra in ['ficha de anamnese', 'questionário', 'história familiar']):
            return 'Ficha de Anamnese'
        elif any(palavra in texto_lower for palavra in ['cartão de vacina', 'vacinação', 'imunização']):
            return 'Cartão de Vacinação'
        
        # EXAMES ESPECIALIZADOS
        elif any(palavra in texto_lower for palavra in ['eletroencefalograma', 'eeg', 'atividade cerebral']):
            return 'Eletroencefalograma'
        elif any(palavra in texto_lower for palavra in ['eletromiografia', 'emg', 'condução nervosa']):
            return 'Eletromiografia'
        elif any(palavra in texto_lower for palavra in ['potencial evocado', 'sistema nervoso']):
            return 'Potencial Evocado'
        elif any(palavra in texto_lower for palavra in ['audiometria', 'audição', 'acuidade auditiva']):
            return 'Audiometria'
        elif any(palavra in texto_lower for palavra in ['campo visual', 'perimetria', 'glaucoma']):
            return 'Campo Visual'
        
        else:
            return 'Documento Médico'
    
    def _get_system_prompt(self, tipo_documento: str) -> str:
        """Retorna prompt do sistema baseado no tipo de documento"""
        
        # Para documentos médicos, manter sistema prompt médico
        if any(termo in tipo_documento for termo in ['Hemograma', 'Bioquímica', 'Urina', 'Hormonal', 'Tomografia', 
                                                      'Ressonância', 'Ultrassom', 'Radiografia', 'Mamografia',
                                                      'Endoscopia', 'Anatomopatológico', 'Citologia', 'Prontuário',
                                                      'Consulta', 'Cirúrgico', 'Alta', 'Prescrição', 'Atestado',
                                                      'Eletrocardiograma', 'Ecocardiograma', 'Espirometria', 'Médico']):
            return """Você é um assistente de extração e sistematização de dados para profissionais de saúde.
                      Analise documentos médicos de qualquer tipo (exames, laudos, prontuários, relatórios) e extraia informações clinicamente relevantes.
                      Para exames laboratoriais: foque APENAS em alterações.
                      Para outros documentos: documente diagnósticos, achados, procedimentos e informações clinicamente significativas.
                      Siga EXATAMENTE a estrutura fornecida no prompt.
                      SEMPRE termine com 'ANÁLISE DE DADOS FINALIZADA'.
                      Seja objetivo e factual, sem fazer interpretações além do documentado."""
        
        # Para documentos jurídicos
        elif 'Jurídico' in tipo_documento:
            return """Você é um assistente de análise documental para documentos jurídicos.
                      Extraia informações juridicamente relevantes: cláusulas, obrigações, prazos, penalidades.
                      Seja objetivo e neutro, sem emitir opinião jurídica.
                      Termine sempre com 'ANÁLISE FINALIZADA'."""
        
        # Para documentos financeiros
        elif 'Financeiro' in tipo_documento:
            return """Você é um assistente de análise documental para documentos financeiros.
                      Extraia informações financeiras relevantes: valores, indicadores, condições.
                      Seja objetivo e factual, sem fazer análises financeiras.
                      Termine sempre com 'ANÁLISE FINALIZADA'."""
        
        # Para outros tipos
        else:
            return """Você é um assistente de análise documental generalista.
                      Extraia informações relevantes de forma estruturada e objetiva.
                      Identifique pontos-chave e elementos importantes do conteúdo.
                      Termine sempre com 'ANÁLISE FINALIZADA'."""
    
    def _gerar_prompt_contextual(self, texto: str, nome_arquivo: str, tipo_documento: str, contexto_info: Dict = None) -> str:
        """Gera prompt específico baseado no tipo de documento"""
        
        # PROMPT MÉDICO ESPECÍFICO (seu prompt original EXATO)
        if any(termo in tipo_documento for termo in ['Hemograma', 'Bioquímica', 'Urina', 'Hormonal', 'Tomografia', 
                                                      'Ressonância', 'Ultrassom', 'Radiografia', 'Mamografia',
                                                      'Endoscopia', 'Anatomopatológico', 'Citologia', 'Prontuário',
                                                      'Consulta', 'Cirúrgico', 'Alta', 'Prescrição', 'Atestado',
                                                      'Eletrocardiograma', 'Ecocardiograma', 'Espirometria', 'Médico']):
            return f"""
INTERPRETAÇÃO DE DOCUMENTO MÉDICO

ARQUIVO: {nome_arquivo}
TEXTO EXTRAÍDO DO DOCUMENTO:
{texto}

INFORMAÇÕES DO PACIENTE:
{contexto_info.get('additional_info', 'Não informado') if contexto_info else 'Não informado'}

INSTRUÇÕES PARA INTERPRETAÇÃO:
## PAPEL E OBJETIVO
Você é um assistente de extração e sistematização de dados para um profissional de saúde. Sua função é analisar documentos médicos (exames laboratoriais, laudos de imagem, relatórios de consulta, prontuários, relatórios cirúrgicos, etc.) e organizar as informações clinicamente relevantes. O objetivo é fornecer um resumo organizado para que o profissional humano possa ter uma visão clara dos achados importantes.

## INSTRUÇÕES GERAIS
1. *FOCO EM ACHADOS RELEVANTES:* Documente alterações, achados anormais, diagnósticos, procedimentos realizados, medicações prescritas, e qualquer informação clinicamente significativa. Para exames laboratoriais, reporte APENAS valores fora da normalidade.
2. *NEUTRALIDADE E OBJETIVIDADE:* Descreva os achados de forma neutra e factual. Não use linguagem que sugira prognóstico ou gravidade além do que está documentado.
3. *NÃO FAZER (PROIBIÇÕES ABSOLUTAS):*
* NÃO faça recomendações clínicas, terapêuticas ou de exames adicionais além das já documentadas.
* NÃO sugira hipóteses diagnósticas além das já mencionadas no documento.
* NÃO emita juízo de valor sobre achados ("preocupante", "grave"). Apenas reporte objetivamente.
* NÃO compare com documentos anteriores, a menos que o documento atual faça essa comparação.
* NÃO preencha lacunas de informação não presentes no texto.
4. *CONFIDENCIALIDADE:* Trate toda informação como confidencial.
5. *FINALIZAÇÃO OBRIGATÓRIA:* Termine com "ANÁLISE DE DADOS FINALIZADA".

---
## ESTRUTURA DE RESPOSTA OBRIGATÓRIA

### 1. IDENTIFICAÇÃO DO DOCUMENTO
* *Tipo de Documento:* (Ex: Hemograma, Bioquímica Completa, Laudo de TC de Abdome, Ressonância Magnética de Crânio, Ultrassom Pélvico, Relatório de Consulta Cardiológica, Anamnese, Evolução de Enfermagem, Prontuário de Internação, Relatório Cirúrgico, Laudo Anatomopatológico, Citologia Oncótica, Eletrocardiograma, Ecocardiograma, Endoscopia Digestiva Alta, Colonoscopia, Espirometria, Teste Ergométrico, Holter 24h, MAPA, Mamografia, Densitometria Óssea, Cintilografia, Sumário de Alta Hospitalar, Prescrição Médica, Atestado Médico, Receituário, Solicitação de Exames, Parecer Médico, Laudo de Junta Médica, Relatório de Perícia, Ficha de Anamnese, História Clínica, Exame Físico, Evolução Médica, Boletim Médico, Termo de Consentimento, Declaração de Óbito, Atestado de Comparecimento)
* *Data do Documento:*
* *Profissional/Instituição:* (se mencionado)

### 2. ACHADOS PRINCIPAIS
Para EXAMES LABORATORIAIS:
* Liste APENAS valores fora dos parâmetros de referência
* Formato: Nome do exame: Valor (Referência)

Para LAUDOS DE IMAGEM:
* Descreva achados anormais ou patológicos identificados
* Inclua localização, características e medidas quando disponíveis

Para RELATÓRIOS CLÍNICOS/PRONTUÁRIOS:
* Diagnósticos estabelecidos
* Sintomas e sinais clínicos documentados
* Medicações prescritas ou alteradas
* Procedimentos realizados
* Evolução clínica relatada

### 3. INTERPRETAÇÃO TÉCNICA DOS ACHADOS
* Para cada achado relevante, explique seu significado clínico básico
* Formato: *[Achado]:* Explicação técnica objetiva
* Não correlacione achados entre si, apenas explique individualmente

### 4. PADRÕES IDENTIFICADOS
* Se houver múltiplos achados relacionados, descreva o padrão técnico sem fazer diagnósticos
* Exemplo: "Elevação concomitante de enzimas hepáticas" ou "Padrão radiológico de consolidação pulmonar"

### 5. LIMITAÇÕES DO DOCUMENTO
* Mencione informações ausentes que seriam clinicamente relevantes
* Problemas técnicos mencionados (qualidade do exame, artefatos, etc.)

### 6. RESUMO EXECUTIVO
* Sintetize em 1-2 frases os principais achados do documento
* Foque apenas no que foi objetivamente documentado

ANÁLISE DE DADOS FINALIZADA
"""
        
        # PROMPT PARA DOCUMENTOS JURÍDICOS
        elif 'Jurídico' in tipo_documento:
            return f"""
INTERPRETAÇÃO DE DOCUMENTO JURÍDICO

ARQUIVO: {nome_arquivo}
TEXTO EXTRAÍDO DO DOCUMENTO:
{texto}

CONTEXTO ADICIONAL:
{contexto_info.get('additional_info', 'Não informado') if contexto_info else 'Não informado'}

INSTRUÇÕES PARA INTERPRETAÇÃO:
## PAPEL E OBJETIVO
Você é um assistente de extração e sistematização de dados para um profissional jurídico. Sua função é analisar documentos jurídicos (contratos, petições, sentenças, pareceres, etc.) e organizar as informações legalmente relevantes.

## INSTRUÇÕES GERAIS
1. *FOCO EM ELEMENTOS JURÍDICOS RELEVANTES:* Documente cláusulas, obrigações, direitos, prazos, penalidades.
2. *NEUTRALIDADE E OBJETIVIDADE:* Descreva os elementos de forma neutra e factual.
3. *NÃO FAZER:*
* NÃO faça interpretações jurídicas além das já mencionadas no documento.
* NÃO sugira estratégias legais.
* NÃO emita juízo de valor sobre cláusulas.
4. *FINALIZAÇÃO OBRIGATÓRIA:* Termine com "ANÁLISE FINALIZADA".

---
## ESTRUTURA DE RESPOSTA OBRIGATÓRIA

### 1. IDENTIFICAÇÃO DO DOCUMENTO
* *Tipo de Documento:* 
* *Data do Documento:*
* *Partes Envolvidas:*

### 2. CLÁUSULAS PRINCIPAIS
* Liste as principais cláusulas e disposições
* Identifique obrigações de cada parte

### 3. PRAZOS E DATAS IMPORTANTES
* Liste todos os prazos mencionados
* Identifique datas críticas

### 4. PENALIDADES E CONSEQUÊNCIAS
* Documente multas, juros, penalidades

### 5. RESUMO EXECUTIVO
* Sintetize a natureza e principais termos do documento

ANÁLISE FINALIZADA
"""
        
        # PROMPT PARA DOCUMENTOS FINANCEIROS
        elif 'Financeiro' in tipo_documento:
            return f"""
INTERPRETAÇÃO DE DOCUMENTO FINANCEIRO

ARQUIVO: {nome_arquivo}
TEXTO EXTRAÍDO DO DOCUMENTO:
{texto}

CONTEXTO ADICIONAL:
{contexto_info.get('additional_info', 'Não informado') if contexto_info else 'Não informado'}

INSTRUÇÕES PARA INTERPRETAÇÃO:
## PAPEL E OBJETIVO
Você é um assistente de extração e sistematização de dados para um profissional financeiro. Sua função é analisar documentos financeiros e organizar as informações economicamente relevantes.

## INSTRUÇÕES GERAIS
1. *FOCO EM DADOS FINANCEIROS:* Documente valores, variações, indicadores.
2. *NEUTRALIDADE E OBJETIVIDADE:* Descreva os dados de forma neutra e factual.
3. *NÃO FAZER:*
* NÃO faça análises financeiras além das já mencionadas.
* NÃO sugira investimentos ou decisões financeiras.
4. *FINALIZAÇÃO OBRIGATÓRIA:* Termine com "ANÁLISE FINALIZADA".

---
## ESTRUTURA DE RESPOSTA OBRIGATÓRIA

### 1. IDENTIFICAÇÃO DO DOCUMENTO
* *Tipo de Documento:*
* *Período/Data:*
* *Entidade:*

### 2. VALORES PRINCIPAIS
* Liste os principais valores, receitas, despesas

### 3. INDICADORES E PERCENTUAIS
* Identifique percentuais, índices mencionados

### 4. RESUMO EXECUTIVO
* Sintetize a situação financeira documentada

ANÁLISE FINALIZADA
"""
        
        # PROMPT GENÉRICO PARA OUTROS TIPOS
        else:
            return f"""
INTERPRETAÇÃO DE DOCUMENTO

ARQUIVO: {nome_arquivo}
TIPO DETECTADO: {tipo_documento}
TEXTO EXTRAÍDO DO DOCUMENTO:
{texto}

CONTEXTO ADICIONAL:
{contexto_info.get('additional_info', 'Não informado') if contexto_info else 'Não informado'}

INSTRUÇÕES PARA INTERPRETAÇÃO:
## PAPEL E OBJETIVO
Você é um assistente de análise documental. Sua função é analisar documentos e organizar as informações mais relevantes de forma estruturada.

## INSTRUÇÕES GERAIS
1. *FOCO EM INFORMAÇÕES RELEVANTES:* Documente dados importantes, decisões, determinações.
2. *NEUTRALIDADE E OBJETIVIDADE:* Descreva as informações de forma neutra e factual.
3. *NÃO PREENCHA LACUNAS:* Documente apenas o que está explicitamente presente.
4. *FINALIZAÇÃO OBRIGATÓRIA:* Termine com "ANÁLISE FINALIZADA".

---
## ESTRUTURA DE RESPOSTA OBRIGATÓRIA

### 1. IDENTIFICAÇÃO DO DOCUMENTO
* *Tipo de Documento:*
* *Data/Período:*
* *Origem:*

### 2. CONTEÚDO PRINCIPAL
* Liste as principais informações e dados

### 3. PONTOS-CHAVE
* Destaque elementos mais importantes

### 4. RESUMO EXECUTIVO
* Sintetize o conteúdo principal do documento

ANÁLISE FINALIZADA
"""
    
    def _extrair_achados_principais(self, texto: str) -> list:
        """Extrai achados principais do texto focando em informações relevantes - MÉTODO ORIGINAL MANTIDO"""
        achados = []
        linhas = texto.split('\n')
        
        # Palavras que indicam achados relevantes
        indicadores_relevantes = [
            # Alterações laboratoriais
            'alterado', 'elevado', 'aumentado', 'diminuído', 'reduzido', 
            'baixo', 'alto', 'anormal', 'fora', 'acima', 'abaixo',
            # Achados de imagem
            'lesão', 'massa', 'nódulo', 'cisto', 'tumor', 'espessamento',
            'dilatação', 'estenose', 'obstrução', 'fratura', 'derrame',
            # Achados clínicos
            'diagnóstico', 'sintoma', 'sinal', 'queixa', 'dor', 'febre',
            'edema', 'dispneia', 'tosse', 'náusea', 'vômito',
            # Procedimentos e medicações
            'prescrito', 'administrado', 'cirurgia', 'procedimento',
            'medicamento', 'dose', 'tratamento',
            # Termos jurídicos e financeiros
            'cláusula', 'obrigação', 'prazo', 'valor', 'multa', 'juros',
            'receita', 'despesa', 'saldo', 'pagamento'
        ]
        
        for linha in linhas:
            linha = linha.strip()
            if len(linha) > 10:  # Linhas com conteúdo substancial
                # Verificar se linha contém indicadores relevantes
                if any(indicador in linha.lower() for indicador in indicadores_relevantes):
                    achados.append(linha)
                elif any(simbolo in linha for simbolo in ['*', '↑', '↓', '>', '<', '±', ':', '-']):
                    achados.append(linha)
                # Linhas que parecem diagnósticos ou conclusões
                elif any(palavra in linha.lower() for palavra in ['diagnóstico:', 'conclusão:', 'impressão:', 'parecer:']):
                    achados.append(linha)
                
                # Limitar a 15 achados mais relevantes
                if len(achados) >= 15:
                    break
        
        return achados
    
    def _gerar_status_geral(self, tipo_documento: str, interpretacao: str) -> str:
        """Gera status geral baseado no tipo de documento"""
        
        if any(termo in tipo_documento for termo in ['Hemograma', 'Bioquímica', 'Urina', 'Hormonal', 'Tomografia', 
                                                      'Ressonância', 'Ultrassom', 'Radiografia', 'Mamografia',
                                                      'Endoscopia', 'Anatomopatológico', 'Citologia', 'Prontuário',
                                                      'Consulta', 'Cirúrgico', 'Alta', 'Prescrição', 'Atestado',
                                                      'Eletrocardiograma', 'Ecocardiograma', 'Espirometria', 'Médico']):
            return 'Análise de documento médico realizada - Consultar profissional para avaliação completa'
        elif 'Jurídico' in tipo_documento:
            return 'Análise de documento jurídico realizada - Consultar advogado para orientação específica'
        elif 'Financeiro' in tipo_documento:
            return 'Análise de documento financeiro realizada - Dados extraídos para avaliação'
        else:
            return 'Análise documental realizada - Informações principais extraídas'