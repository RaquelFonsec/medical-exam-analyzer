from .fact_extractor_service import fact_extractor
from .output_validator_service import output_validator
from typing import Dict, Any
import openai
import os
from datetime import datetime

class AntiHallucinationPipeline:
    """Pipeline médico anti-alucinação com precisão cirúrgica"""
    
    def __init__(self):
        print("🏥 Inicializando AntiHallucinationPipeline - Precisão Médica Máxima")
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Templates seguros para casos de baixa completude
        self.safe_templates = self._load_safe_templates()
        
    def _load_safe_templates(self):
        """Templates médicos seguros para dados incompletos"""
        return {
            'anamnese_minima': """
## 📋 1. IDENTIFICAÇÃO DO PACIENTE
- Nome: {nome}
- Idade: {idade}
- Profissão: {profissao}
- Data da consulta: {data}

## 🗣️ 2. QUEIXA PRINCIPAL
{queixa_principal}

## 📖 3. HISTÓRIA DA DOENÇA ATUAL (HDA)
{historia_atual}

## 🏥 4. ANTECEDENTES PESSOAIS E FAMILIARES RELEVANTES
[Não coletados na consulta de telemedicina]

## 📄 5. DOCUMENTAÇÃO APRESENTADA
[Conforme documentação apresentada pelo paciente]

## 🎥 6. EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)
[Consulta realizada por telemedicina - limitações inerentes à modalidade]

## ⚕️ 7. AVALIAÇÃO MÉDICA (ASSESSMENT)
{avaliacao_contexto}

**MODALIDADE:** Telemedicina
**DATA:** {data}
**OBSERVAÇÃO:** Anamnese baseada exclusivamente no relato do paciente
""",
            
            'laudo_minimo': """
## 🏥 LAUDO MÉDICO - {contexto}

### 📋 IDENTIFICAÇÃO
- Paciente: {nome}
- Data: {data}
- Modalidade: Telemedicina

### 1. 📖 HISTÓRIA CLÍNICA
{historia_clinica_resumida}

### 2. 🚫 LIMITAÇÃO FUNCIONAL
{limitacoes_relatadas}

### 3. 🔬 EXAMES (Quando Houver)
{exames_mencionados}

### 4. 💊 TRATAMENTO
{tratamentos_citados}

### 5. 🔮 PROGNÓSTICO
{prognostico_contextual}

### 6. ⚖️ CONCLUSÃO - {contexto}
{conclusao_especifica}

**OBSERVAÇÃO:** Laudo baseado exclusivamente em consulta de telemedicina e relato do paciente
**DATA:** {data}
"""
        }
    
    async def analyze_with_maximum_precision(self, patient_info: str, transcription: str, context_type: str) -> Dict[str, Any]:
        """Análise médica com precisão máxima - Pipeline completo"""
        
        pipeline_result = {
            'stage': 'initialization',
            'safety_level': 'UNKNOWN',
            'precision_score': 0.0,
            'pipeline_path': []
        }
        
        try:
            # ETAPA 1: EXTRAÇÃO FACTUAL RIGOROSA
            print("🔍 ETAPA 1: Extração de fatos explícitos...")
            explicit_facts = fact_extractor.extract_explicit_facts_only(transcription, patient_info)
            pipeline_result['stage'] = 'fact_extraction'
            pipeline_result['pipeline_path'].append('fact_extraction_completed')
            
            # ETAPA 2: AVALIAÇÃO DE COMPLETUDE
            print("📊 ETAPA 2: Avaliando completude dos dados...")
            completeness = explicit_facts['completude_dados']
            pipeline_result['data_completeness'] = completeness
            
            if completeness['level'] == 'BAIXA':
                # CAMINHO SEGURO: Template fixo
                print("🛡️ DADOS INSUFICIENTES: Usando template seguro")
                result = await self._generate_safe_template_based(explicit_facts, context_type)
                pipeline_result['pipeline_path'].append('safe_template_used')
                pipeline_result['safety_level'] = 'MAXIMUM_SAFE'
                
            else:
                # CAMINHO INTELIGENTE: IA controlada + validação
                print("🧠 DADOS SUFICIENTES: Usando IA controlada + validação")
                
                # ETAPA 3: GERAÇÃO CONTROLADA
                initial_generation = await self._generate_controlled_content(
                    explicit_facts, context_type
                )
                pipeline_result['pipeline_path'].append('controlled_generation_completed')
                
                # ETAPA 4: VALIDAÇÃO RIGOROSA
                print("🛡️ ETAPA 4: Validação anti-alucinação...")
                validation_result = await output_validator.validate_against_source_comprehensive(
                    initial_generation['anamnese'], explicit_facts, transcription
                )
                
                pipeline_result['validation_result'] = validation_result
                
                if validation_result['has_hallucinations']:
                    # CORREÇÃO AUTOMÁTICA
                    print("⚠️ ALUCINAÇÕES DETECTADAS: Aplicando correções...")
                    corrected_result = await self._apply_automatic_corrections(
                        initial_generation, validation_result, explicit_facts, context_type
                    )
                    pipeline_result['pipeline_path'].append('corrections_applied')
                    pipeline_result['safety_level'] = 'CORRECTED_SAFE'
                    result = corrected_result
                    
                else:
                    # APROVADO NA VALIDAÇÃO
                    print("✅ VALIDAÇÃO APROVADA: Conteúdo seguro")
                    pipeline_result['pipeline_path'].append('validation_passed')
                    pipeline_result['safety_level'] = 'VALIDATED_SAFE'
                    result = initial_generation
            
            # ETAPA 5: CÁLCULO DE PRECISÃO FINAL
            pipeline_result['precision_score'] = self._calculate_precision_score(
                pipeline_result, explicit_facts
            )
            
            # ETAPA 6: COMPILAÇÃO FINAL
            final_result = {
                'success': True,
                'anamnese': result['anamnese'],
                'laudo_medico': result['laudo'],
                'transcription': transcription,
                'context_analysis': {'main_context': context_type, 'confidence': 0.9},
                
                # METADADOS DE PRECISÃO
                'precision_metrics': {
                    'safety_level': pipeline_result['safety_level'],
                    'precision_score': pipeline_result['precision_score'],
                    'data_completeness': completeness['level'],
                    'pipeline_path': ' → '.join(pipeline_result['pipeline_path']),
                    'facts_extracted': len(explicit_facts['sintomas_textualmente_relatados']),
                    'hallucination_flags': pipeline_result.get('validation_result', {}).get('hallucination_flags', [])
                },
                
                # AUDITORIA MÉDICA
                'medical_audit': {
                    'explicit_facts_used': explicit_facts,
                    'missing_critical_info': explicit_facts['informacoes_ausentes'],
                    'source_traceability': True,
                    'medical_safety_certified': pipeline_result['safety_level'] in ['MAXIMUM_SAFE', 'VALIDATED_SAFE', 'CORRECTED_SAFE']
                },
                
                'model': f"Pipeline Anti-Alucinação Médica - {pipeline_result['safety_level']}",
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"✅ PIPELINE CONCLUÍDO: {pipeline_result['safety_level']} - Precisão: {pipeline_result['precision_score']:.2f}")
            return final_result
            
        except Exception as e:
            print(f"❌ Erro no pipeline: {e}")
            # FALLBACK ULTRA-SEGURO
            return await self._emergency_safe_fallback(patient_info, transcription, context_type, str(e))
    
    async def _generate_controlled_content(self, explicit_facts: Dict, context_type: str) -> Dict[str, Any]:
        """Gera conteúdo usando IA com controle máximo"""
        
        # Construir prompt ultra-restritivo
        facts_summary = self._build_facts_summary(explicit_facts)
        
        controlled_prompt = f"""
INSTRUÇÃO MÉDICA CRÍTICA: Você é um ASSISTENTE DE DOCUMENTAÇÃO MÉDICA que APENAS transcreve informações EXPLICITAMENTE fornecidas.

PROIBIÇÕES ABSOLUTAS:
❌ NÃO inferir sintomas não mencionados
❌ NÃO assumir diagnósticos  
❌ NÃO citar exames não relatados
❌ NÃO mencionar medicamentos não citados
❌ NÃO especular sobre causas
❌ NÃO usar conhecimento médico geral

FATOS EXPLÍCITOS EXTRAÍDOS:
{facts_summary}

CONTEXTO MÉDICO: {context_type.upper()}

REGRAS DE DOCUMENTAÇÃO:
✅ Use APENAS informações acima
✅ Cite textualmente: "Paciente relatou: '[frase exata]'"
✅ Para informações ausentes: "[Não relatado na consulta]"
✅ Mantenha estrutura médica formal
✅ Foque no contexto {context_type}

Gere anamnese estruturada baseada EXCLUSIVAMENTE nos fatos fornecidos:
"""
        
        try:
            # GERAÇÃO DE ANAMNESE
            anamnese_response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"Você é um assistente de documentação médica para {context_type}. Use APENAS informações fornecidas explicitamente."
                    },
                    {
                        "role": "user",
                        "content": controlled_prompt
                    }
                ],
                temperature=0.1,  # Mínima criatividade
                max_tokens=1500
            )
            
            anamnese = anamnese_response.choices[0].message.content
            
            # GERAÇÃO DE LAUDO
            laudo_prompt = self._build_laudo_prompt(explicit_facts, anamnese, context_type)
            
            laudo_response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"Você é um médico perito em {context_type} que gera laudos baseados APENAS em informações documentadas."
                    },
                    {
                        "role": "user",
                        "content": laudo_prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            laudo = laudo_response.choices[0].message.content
            
            return {
                'anamnese': anamnese,
                'laudo': laudo,
                'generation_method': 'controlled_ai'
            }
            
        except Exception as e:
            print(f"❌ Erro na geração controlada: {e}")
            # Fallback para template
            return await self._generate_safe_template_based(explicit_facts, context_type)
    
    def _build_facts_summary(self, explicit_facts: Dict) -> str:
        """Constrói resumo estruturado dos fatos"""
        summary_parts = []
        
        # Dados pessoais confirmados
        personal_data = explicit_facts['dados_pessoais_confirmados']
        if personal_data:
            summary_parts.append("DADOS PESSOAIS CONFIRMADOS:")
            for field, data in personal_data.items():
                summary_parts.append(f"- {field}: {data['valor']} (frase original: '{data['frase_original']}')")
        
        # Sintomas textualmente relatados
        symptoms = explicit_facts['sintomas_textualmente_relatados']
        if symptoms:
            summary_parts.append("\nSINTOMAS TEXTUALMENTE RELATADOS:")
            for symptom in symptoms:
                summary_parts.append(f"- {symptom['sintoma_exato']} (frase completa: '{symptom['frase_completa_original']}')")
        
        # Timeline especificada
        timeline = explicit_facts['timeline_especificada']
        if timeline:
            summary_parts.append("\nTIMELINE ESPECIFICADA:")
            for time_type, data in timeline.items():
                summary_parts.append(f"- {time_type}: {data['periodo']} (frase: '{data['frase_original']}')")
        
        # Tratamentos citados
        treatments = explicit_facts['tratamentos_citados']
        if treatments:
            summary_parts.append("\nTRATAMENTOS CITADOS:")
            for treatment in treatments:
                summary_parts.append(f"- {treatment['tratamento']} (frase: '{treatment['frase_original']}')")
        
        # Informações ausentes
        missing = explicit_facts['informacoes_ausentes']
        if missing:
            summary_parts.append(f"\nINFORMAÇÕES NÃO FORNECIDAS: {', '.join(missing)}")
        
        return "\n".join(summary_parts) if summary_parts else "NENHUMA INFORMAÇÃO ESPECÍFICA EXTRAÍDA"
    
    def _build_laudo_prompt(self, explicit_facts: Dict, anamnese: str, context_type: str) -> str:
        """Constrói prompt para geração de laudo"""
        
        context_specific_instructions = {
            'bpc': 'Foque em limitações para vida independente e necessidade de cuidador',
            'incapacidade': 'Foque na impossibilidade de exercer a função laboral habitual',
            'auxilio_acidente': 'Foque na redução da capacidade laborativa sem incapacidade total',
            'isencao_ir': 'Foque na comprovação de doença grave conforme legislação'
        }
        
        instruction = context_specific_instructions.get(context_type, 'Análise médica geral')
        
        return f"""
GERAÇÃO DE LAUDO MÉDICO PARA {context_type.upper()}

ANAMNESE BASE:
{anamnese}

FATOS EXPLÍCITOS:
{self._build_facts_summary(explicit_facts)}

INSTRUÇÕES ESPECÍFICAS:
- {instruction}
- Use APENAS informações da anamnese e fatos explícitos
- Mantenha estrutura de laudo médico formal
- Inclua CID-10 quando apropriado
- Para informações não disponíveis: "[Não avaliado na consulta]"

Gere laudo médico estruturado:
"""
    
    async def _generate_safe_template_based(self, explicit_facts: Dict, context_type: str) -> Dict[str, Any]:
        """Gera documentos usando templates seguros"""
        
        # Extrair dados seguros
        personal_data = explicit_facts['dados_pessoais_confirmados']
        nome = personal_data.get('nome_exato', {}).get('valor', '[Nome não informado]')
        idade = personal_data.get('idade_exata', {}).get('valor', '[Idade não informada]')
        profissao = personal_data.get('profissao_exata', {}).get('valor', '[Profissão não informada]')
        
        # Construir queixa principal segura
        symptoms = explicit_facts['sintomas_textualmente_relatados']
        if symptoms:
            queixa_parts = []
            for symptom in symptoms[:3]:  # Limitar a 3 sintomas principais
                queixa_parts.append(f"Relatou textualmente: '{symptom['sintoma_exato']}'")
            queixa_principal = ". ".join(queixa_parts)
        else:
            queixa_principal = "[Sintomas específicos não detalhados na consulta]"
        
        # Timeline segura
        timeline = explicit_facts['timeline_especificada']
        historia_atual = "Baseado no relato da consulta de telemedicina."
        if timeline:
            for time_info in timeline.values():
                historia_atual += f" Mencionou: '{time_info['frase_original']}'."
        
        # Avaliação contextual
        context_evaluations = {
            'bpc': f"Consulta para avaliação de BPC/LOAS. Avaliação baseada no relato do paciente.",
            'incapacidade': f"Consulta para avaliação de incapacidade laboral. Análise baseada no relato profissional.",
            'auxilio_acidente': f"Consulta para avaliação de auxílio-acidente. Baseado no relato de sequelas.",
            'isencao_ir': f"Consulta para avaliação de isenção IR. Baseado no relato médico."
        }
        
        # Preencher template de anamnese
        anamnese = self.safe_templates['anamnese_minima'].format(
            nome=nome,
            idade=f"{idade} anos" if idade != '[Idade não informada]' else idade,
            profissao=profissao,
            data=datetime.now().strftime('%d/%m/%Y'),
            queixa_principal=queixa_principal,
            historia_atual=historia_atual,
            avaliacao_contexto=context_evaluations.get(context_type, 'Consulta médica geral.')
        )
        
        # Preencher template de laudo
        laudo = self.safe_templates['laudo_minimo'].format(
            contexto=context_type.upper(),
            nome=nome,
            data=datetime.now().strftime('%d/%m/%Y'),
            historia_clinica_resumida="Conforme relato na consulta de telemedicina.",
            limitacoes_relatadas="Conforme relatado pelo paciente na consulta." if symptoms else "[Não especificadas na consulta]",
            exames_mencionados="[Não apresentados na consulta]",
            tratamentos_citados="Conforme relatado pelo paciente." if explicit_facts['tratamentos_citados'] else "[Não especificados]",
            prognostico_contextual=f"A ser avaliado conforme evolução e contexto de {context_type}.",
            conclusao_especifica=f"Consulta realizada para fins de {context_type}, baseada exclusivamente no relato do paciente."
        )
        
        return {
            'anamnese': anamnese,
            'laudo': laudo,
            'generation_method': 'safe_template'
        }
    
    async def _apply_automatic_corrections(self, initial_generation: Dict, validation_result: Dict, explicit_facts: Dict, context_type: str) -> Dict[str, Any]:
        """Aplica correções automáticas baseadas na validação"""
        
        corrections = validation_result.get('corrections', {})
        corrected_anamnese = corrections.get('corrected_text', initial_generation['anamnese'])
        
        # Se muitas correções foram necessárias, reverter para template seguro
        if len(validation_result['hallucination_flags']) > 3:
            print("🛡️ MUITAS ALUCINAÇÕES: Revertendo para template ultra-seguro")
            return await self._generate_safe_template_based(explicit_facts, context_type)
        
        # Aplicar correções menores
        return {
            'anamnese': corrected_anamnese,
            'laudo': initial_generation['laudo'],  # TODO: Aplicar correções no laudo também
            'generation_method': 'corrected_ai',
            'corrections_applied': corrections.get('modifications_made', [])
        }
    
    def _calculate_precision_score(self, pipeline_result: Dict, explicit_facts: Dict) -> float:
        """Calcula score de precisão final"""
        
        base_score = 0.5
        
        # Bonus por caminho seguro
        if pipeline_result['safety_level'] == 'MAXIMUM_SAFE':
            base_score += 0.3
        elif pipeline_result['safety_level'] == 'VALIDATED_SAFE':
            base_score += 0.4
        elif pipeline_result['safety_level'] == 'CORRECTED_SAFE':
            base_score += 0.2
        
        # Bonus por completude dos dados
        completeness = explicit_facts['completude_dados']['score']
        base_score += completeness * 0.3
        
        # Penalidade por alucinações detectadas
        validation_result = pipeline_result.get('validation_result', {})
        hallucination_count = len(validation_result.get('hallucination_flags', []))
        base_score -= hallucination_count * 0.1
        
        return max(0.0, min(1.0, base_score))
    
    async def _emergency_safe_fallback(self, patient_info: str, transcription: str, context_type: str, error: str) -> Dict[str, Any]:
        """Fallback ultra-seguro em caso de erro crítico"""
        
        return {
            'success': True,
            'anamnese': f"""
## 📋 ANAMNESE - MODO SEGURO DE EMERGÊNCIA

### IDENTIFICAÇÃO
Paciente: {patient_info}
Data: {datetime.now().strftime('%d/%m/%Y')}
Modalidade: Telemedicina

### OBSERVAÇÕES
- Sistema executado em modo de segurança devido a erro técnico
- Transcrição disponível mas processamento limitado
- Recomenda-se revisão médica manual
- Contexto identificado: {context_type}

**ERRO TÉCNICO:** {error}
**TRANSCRIÇÃO ORIGINAL:** [Disponível para revisão médica]
""",
            'laudo_medico': f"""
## 🏥 LAUDO MÉDICO - MODO SEGURO

### IDENTIFICAÇÃO
Data: {datetime.now().strftime('%d/%m/%Y')}
Contexto: {context_type.upper()}

### OBSERVAÇÃO CRÍTICA
Documento gerado em modo de segurança devido a limitações técnicas.
Requer revisão e elaboração médica manual.

**RECOMENDAÇÃO:** Revisão médica presencial ou nova consulta de telemedicina.
""",
            'transcription': transcription,
            'precision_metrics': {
                'safety_level': 'EMERGENCY_SAFE',
                'precision_score': 0.3,
                'pipeline_path': 'emergency_fallback',
                'requires_manual_review': True
            },
            'model': 'Pipeline Seguro de Emergência',
            'timestamp': datetime.now().isoformat()
        }

# Instância global
anti_hallucination_pipeline = AntiHallucinationPipeline()
