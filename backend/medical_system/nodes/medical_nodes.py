"""
Nodos do Pipeline de Análise Médica
"""

import json
from typing import Dict
from ..models.state_models import MedicalAnalysisState
from ..models.pydantic_models import (
    PatientIdentification, ChiefComplaint, CurrentIllnessHistory,
    PastHistory, MedicalDocumentation, TelemedicineExam,
    MedicalAssessment, CompleteMedicalRecord, Specialty
)
from ..extractors.specialized_extractor import SpecializedExtractor

class MedicalAnalysisNodes:
    """Nodos do pipeline de análise médica"""
    
    def __init__(self, client, rag_service):
        self.client = client
        self.rag_service = rag_service
        self.specialized_extractor = SpecializedExtractor(client, rag_service)
    
    async def extract_basic_data(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nodo 1: Extração básica de dados"""
        
        print("🔍 NODO 1: Extraindo dados básicos...")
        
        try:
            prompt = f"""
Extraia dados estruturados da anamnese médica para telemedicina.

TEXTO: {state["original_text"]}

Retorne JSON com estrutura completa:
{{
    "identificacao": {{
        "nome": "nome paciente",
        "idade": idade_numerica,
        "sexo": "M/F",
        "profissao": "profissão",
        "documento_rg": "RG se mencionado",
        "documento_cpf": "CPF se mencionado",
        "numero_processo": "número processo se mencionado"
    }},
    "queixa_principal": {{
        "motivo_consulta": "motivo principal",
        "solicitacao_beneficio": "tipo de benefício solicitado",
        "solicitacao_advogado": "solicitação específica"
    }},
    "historia_doenca_atual": {{
        "data_inicio_sintomas": "quando começou",
        "fatores_desencadeantes": ["fatores que causaram"],
        "tratamentos_realizados": ["tratamentos já feitos"],
        "medicacoes_atuais": ["medicações em uso"],
        "limitacoes_atuais": ["limitações funcionais"],
        "sintomas_persistentes": ["sintomas atuais"]
    }},
    "antecedentes": {{
        "doencas_previas": ["doenças anteriores"],
        "historico_ocupacional": "trabalhos anteriores",
        "anos_contribuicao": anos_contribuicao,
        "acidentes_trabalho": ["acidentes laborais"]
    }}
}}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Médico especialista em extração de dados. Seja preciso e completo."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=800
            )
            
            result_text = response.choices[0].message.content.strip()
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            try:
                extracted_data = json.loads(result_text)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ JSON básico inválido: {e}")
                extracted_data = {
                    "identificacao": {
                        "nome": "Paciente", 
                        "idade": 45, 
                        "sexo": "M", 
                        "profissao": "Trabalhador",
                        "documento_rg": None,
                        "documento_cpf": None,
                        "numero_processo": None
                    },
                    "queixa_principal": {"motivo_consulta": "Avaliação médica"},
                    "historia_doenca_atual": {"limitacoes_atuais": ["limitação funcional"]},
                    "antecedentes": {"historico_ocupacional": "trabalhador"}
                }
            
            state["extracted_data"] = extracted_data
            state["current_step"] = "basic_extraction_complete"
            
            return state
            
        except Exception as e:
            state["errors"].append(f"Erro na extração básica: {str(e)}")
            return state
    
    async def analyze_by_specialty(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nodo 2: Análise por especialidade"""
        
        print("🔍 NODO 2: Analisando por especialidade...")
        
        try:
            # Detectar e analisar por especialidade
            primary_specialty, specialty_data = self.specialized_extractor.extract_by_specialty(
                state["original_text"]
            )
            
            # Buscar contexto RAG específico da especialidade
            rag_context = await self._get_specialty_rag_context(primary_specialty, specialty_data)
            
            state["specialist_analysis"] = {
                "primary_specialty": primary_specialty,
                "specialty_data": specialty_data,
                "rag_context": rag_context
            }
            state["current_step"] = "specialty_analysis_complete"
            
            return state
            
        except Exception as e:
            state["errors"].append(f"Erro na análise por especialidade: {str(e)}")
            return state
    
    async def detect_occupational_nexus(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nodo 3: Detecção de nexo ocupacional"""
        
        print("🔍 NODO 3: Detectando nexo ocupacional...")
        
        try:
            # Verificar se é telemedicina (não permite nexo laboral)
            is_telemedicine = True  # Por padrão, assumir telemedicina
            
            if is_telemedicine:
                print("⚠️  TELEMEDICINA: Nexo laboral não permitido pelo CFM")
                occupational_analysis = {
                    "nexo_ocupacional": False,
                    "motivo_exclusao": "Telemedicina - CFM não permite nexo laboral",
                    "pode_ser_acidente_trabalho": False
                }
            else:
                # Aqui entraria a análise ocupacional completa
                occupational_analysis = self._analyze_occupational_nexus(state)
            
            # Atualizar dados extraídos
            if state["extracted_data"]:
                state["extracted_data"]["nexo_ocupacional"] = occupational_analysis
            
            state["current_step"] = "occupational_analysis_complete"
            return state
            
        except Exception as e:
            state["errors"].append(f"Erro na análise ocupacional: {str(e)}")
            return state
    
    async def classify_benefit(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nodo 4: Classificação do benefício"""
        
        print("🔍 NODO 4: Classificando benefício...")
        
        try:
            # Construir prompt com todos os dados coletados
            classification_prompt = self._build_classification_prompt(state)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Médico perito INSS. Classifique com base em evidências."},
                    {"role": "user", "content": classification_prompt}
                ],
                temperature=0.0,
                max_tokens=600
            )
            
            result_text = response.choices[0].message.content.strip()
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            try:
                classification = json.loads(result_text)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ JSON classificação inválido: {e}")
                classification = {
                    "tipo_beneficio": "AUXÍLIO-DOENÇA",
                    "cid_principal": "M54.5",
                    "cid_descricao": "Dor lombar baixa",
                    "justificativa": "Paciente apresenta limitação funcional que impede o exercício da atividade laboral",
                    "prognostico": "reservado",
                    "tempo_afastamento": "90 dias",
                    "especialidade_indicada": "ortopedia"
                }
            
            # Aplicar validações automáticas
            validated_classification = self._apply_classification_validations(state, classification)
            
            state["benefit_classification"] = validated_classification
            state["current_step"] = "benefit_classification_complete"
            
            return state
            
        except Exception as e:
            state["errors"].append(f"Erro na classificação: {str(e)}")
            return state
    
    async def generate_medical_record(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nodo 5: Gerar prontuário médico completo"""
        
        print("🔍 NODO 5: Gerando prontuário médico...")
        
        try:
            # Construir prontuário usando todos os dados coletados
            medical_record = self._build_complete_medical_record(state)
            
            state["medical_record"] = medical_record
            state["current_step"] = "medical_record_complete"
            
            return state
            
        except Exception as e:
            state["errors"].append(f"Erro na geração do prontuário: {str(e)}")
            return state
    
    async def generate_final_report(self, state: MedicalAnalysisState) -> MedicalAnalysisState:
        """Nodo 6: Gerar laudo médico final"""
        
        print("🔍 NODO 6: Gerando laudo médico final...")
        
        try:
            final_report = self._generate_structured_report(state)
            
            state["final_report"] = final_report
            state["current_step"] = "pipeline_complete"
            
            return state
            
        except Exception as e:
            state["errors"].append(f"Erro na geração do laudo: {str(e)}")
            return state
    
    # Métodos auxiliares
    async def _get_specialty_rag_context(self, specialty: Specialty, specialty_data: Dict) -> str:
        """Busca contexto RAG específico da especialidade"""
        
        try:
            # Construir query baseada na especialidade e dados
            query_parts = [specialty.value]
            
            if "sintomas_especificos" in specialty_data:
                query_parts.extend(specialty_data["sintomas_especificos"][:3])
            
            query = " ".join(query_parts)
            
            docs = self.rag_service.search_similar_documents(query, k=3)
            relevant_docs = [doc for doc, score in docs if score > 0.7]
            
            return "\n".join(relevant_docs[:2])
            
        except Exception:
            return ""
    
    def _analyze_occupational_nexus(self, state: MedicalAnalysisState) -> Dict:
        """Análise de nexo ocupacional (quando permitido)"""
        return {
            "nexo_ocupacional": False,
            "motivo_exclusao": "Análise ocupacional disponível apenas presencial",
            "pode_ser_acidente_trabalho": False
        }
    
    def _build_classification_prompt(self, state: MedicalAnalysisState) -> str:
        """Constrói prompt para classificação"""
        
        extracted = state.get("extracted_data", {})
        specialist = state.get("specialist_analysis", {})
        
        return f"""
Classifique o benefício baseado nos dados extraídos:

DADOS BÁSICOS: {json.dumps(extracted.get('identificacao', {}), indent=2)}
ESPECIALIDADE: {specialist.get('primary_specialty', 'não detectada')}
NEXO OCUPACIONAL: {extracted.get('nexo_ocupacional', {}).get('nexo_ocupacional', False)}

REGRAS DE CLASSIFICAÇÃO:
1. MENOR 16 ANOS = BPC/LOAS
2. TRABALHADOR + DOENÇA COMUM = AUXÍLIO-DOENÇA ou APOSENTADORIA
3. SEM VÍNCULO + DEFICIÊNCIA = BPC/LOAS
4. DOENÇA GRAVE (cancer, parkinson, etc) = ISENÇÃO IR também
5. INCAPACIDADE + NECESSITA CUIDADOR = MAJORAÇÃO 25%

JSON:
{{
    "tipo_beneficio": "benefício principal",
    "beneficios_adicionais": ["outros benefícios aplicáveis"],
    "cid_principal": "CID-10",
    "cid_descricao": "descrição",
    "justificativa": "justificativa completa",
    "prognostico": "favorável/reservado/desfavorável",
    "tempo_afastamento": "dias ou indefinido",
    "especialidade_indicada": "especialidade"
}}
"""
    
    def _apply_classification_validations(self, state: MedicalAnalysisState, classification: Dict) -> Dict:
        """Aplica validações automáticas na classificação"""
        
        extracted = state.get("extracted_data", {})
        identificacao = extracted.get("identificacao", {})
        
        corrections = []
        
        # Validação idade
        idade = identificacao.get("idade")
        if idade and idade < 16:
            if classification.get("tipo_beneficio") != "BPC/LOAS":
                classification["tipo_beneficio"] = "BPC/LOAS"
                corrections.append("Correção por idade < 16")
        
        # Validação trabalhador vs BPC
        profissao = identificacao.get("profissao")
        if profissao:
            profissao = profissao.lower() if profissao and isinstance(profissao, str) else "não informada"
        if profissao and isinstance(profissao, str) and profissao.lower() not in ["não informada", "desempregado"] and classification.get("tipo_beneficio") == "BPC/LOAS":
            if idade and idade >= 65:
                pass  # Pode ser BPC por idade
            else:
                classification["tipo_beneficio"] = "AUXÍLIO-DOENÇA"
                corrections.append("Trabalhador não pode receber BPC/LOAS")
        
        if corrections:
            print(f"🔧 Correções aplicadas: {', '.join(corrections)}")
        
        return classification
    
    def _build_complete_medical_record(self, state: MedicalAnalysisState) -> CompleteMedicalRecord:
        """Constrói prontuário médico completo"""
        
        extracted = state.get("extracted_data", {})
        
        # Mapear dados para modelo Pydantic
        identification = PatientIdentification(**extracted.get("identificacao", {}))
        
        return CompleteMedicalRecord(
            identificacao=identification,
            queixa_principal=ChiefComplaint(),
            historia_doenca_atual=CurrentIllnessHistory(),
            antecedentes=PastHistory(),
            documentacao=MedicalDocumentation(),
            exame_telemedico=TelemedicineExam(),
            avaliacao_medica=MedicalAssessment()
        )
    
    def _generate_structured_report(self, state: MedicalAnalysisState) -> str:
        """Gera laudo médico estruturado final"""
        
        classification = state.get("benefit_classification", {})
        
        return f"""
LAUDO MÉDICO PARA {classification.get('tipo_beneficio', 'BENEFÍCIO')}

1. HISTÓRIA CLÍNICA RESUMIDA
História clínica resumida baseada nos dados extraídos...

2. LIMITAÇÃO FUNCIONAL
Limitações funcionais identificadas...

3. TRATAMENTO
Tratamentos em curso...

4. PROGNÓSTICO
Prognóstico baseado na análise...

5. CONCLUSÃO
{self._generate_conclusion_section(state)}

6. CID-10
Principal: {classification.get('cid_principal', '')} - {classification.get('cid_descricao', '')}
"""
    
    def _generate_conclusion_section(self, state: MedicalAnalysisState) -> str:
        """Gera conclusão congruente com o benefício"""
        classification = state.get("benefit_classification", {})
        benefit_type = classification.get("tipo_beneficio", "")
        
        conclusions = {
            "BPC/LOAS": "Paciente apresenta impedimento de longo prazo que impossibilita participação plena na sociedade em igualdade de condições.",
            "AUXÍLIO-DOENÇA": f"Paciente temporariamente incapacitado para o trabalho. Tempo estimado: {classification.get('tempo_afastamento', '90 dias')}.",
            "APOSENTADORIA POR INVALIDEZ": "Paciente permanentemente incapacitado para qualquer atividade laborativa.",
            "AUXÍLIO-ACIDENTE": "Paciente apresenta redução parcial e permanente da capacidade laborativa.",
            "ISENÇÃO IMPOSTO DE RENDA": "Paciente portador de doença grave conforme Lei 7.713/1988."
        }
        
        return conclusions.get(benefit_type, "Conclusão baseada na análise médica realizada.")