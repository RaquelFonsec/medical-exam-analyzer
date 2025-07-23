from llama_index.core import VectorStoreIndex, Document, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.node_parser import SentenceSplitter
from typing import List, Dict, Any
import os

class MedicalRAGService:
    def __init__(self):
        print("📚 Inicializando MedicalRAGService...")
        self.setup_llama_index()
        self.load_medical_knowledge_base()
        print("✅ MedicalRAGService inicializado")
        
    def setup_llama_index(self):
        """Configura LlamaIndex com embeddings médicos"""
        try:
            # Configurar embeddings e LLM
            Settings.embed_model = OpenAIEmbedding(
                model="text-embedding-3-small",
                api_key=os.getenv("OPENAI_API_KEY")
            )
            
            Settings.llm = OpenAI(
                model="gpt-4o-mini",
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=0.1
            )
            
            # Parser para chunks menores e mais precisos
            Settings.node_parser = SentenceSplitter(
                chunk_size=512,
                chunk_overlap=50
            )
            
            print("✅ LlamaIndex configurado com embeddings OpenAI")
            
        except Exception as e:
            print(f"❌ Erro ao configurar LlamaIndex: {e}")
            print("⚠️ Funcionando sem RAG - usando conhecimento básico")
    
    def load_medical_knowledge_base(self):
        """Carrega base de conhecimento médico estruturada"""
        try:
            medical_documents = [
                # Documentos sobre BPC/LOAS
                Document(text="""
                CRITÉRIOS BPC/LOAS Lei 8.742/93:
                1. Impedimento de longo prazo (mínimo 2 anos)
                2. Natureza física, mental, intelectual ou sensorial
                3. Restrição para participação social plena
                4. Vida independente comprometida
                5. Necessidade de cuidador para atividades básicas
                
                Atividades Básicas de Vida Diária (ABVDs):
                - Alimentação: capacidade de levar alimento à boca
                - Higiene pessoal: banho, escovação, cuidados íntimos
                - Vestuário: vestir e despir roupas
                - Mobilidade: locomoção, transferências
                - Controle esfincteriano: controle de bexiga e intestino
                
                CRITÉRIOS DE AVALIAÇÃO BPC:
                - Impedimento deve ser de longo prazo (mínimo 2 anos)
                - Deve restringir participação social e autonomia
                - Foco em vida independente, não capacidade laboral
                - Necessidade de cuidador é indicativo importante
                """, metadata={"tipo": "bpc", "categoria": "criterios"}),
                
                # Documentos sobre Incapacidade Laboral
                Document(text="""
                INCAPACIDADE LABORAL INSS:
                1. Incapacidade para função habitual
                2. Correlação com atividade profissional específica
                3. Limitações biomecânicas documentadas
                4. Impossibilidade de adaptação
                
                Classificação:
                - Temporária: possibilidade de recuperação
                - Permanente: sequelas definitivas
                - Parcial: algumas funções preservadas
                - Total: impossibilidade completa
                
                Profissões de risco:
                - Pedreiro: levantamento peso, posturas forçadas, trabalho em altura
                - Operador máquinas: movimentos repetitivos, posturas fixas
                - Auxiliar produção: esforço físico moderado/pesado
                - Secretária: movimentos repetitivos, postura sentada prolongada
                - Motorista: postura fixa, vibração, estresse
                
                AVALIAÇÃO FUNCIONAL PARA TRABALHO:
                - Capacidade de carregar peso
                - Posturas prolongadas (em pé, sentado)
                - Movimentos repetitivos
                - Alcance de membros superiores
                - Coordenação motora
                """, metadata={"tipo": "incapacidade", "categoria": "criterios"}),
                
                # Documentos sobre sintomas e limitações
                Document(text="""
                CORRELAÇÃO SINTOMAS-LIMITAÇÕES:
                
                Dor no ombro/braço:
                - Limitação: levantamento acima da cabeça
                - Impacto: carregar peso, alcançar objetos altos
                - Profissões afetadas: pedreiro, pintor, eletricista
                
                Sequelas AVC:
                - Hemiparesia: fraqueza um lado do corpo
                - Limitações AVDs: vestir, banho, alimentação
                - Dependência: necessita cuidador
                - Impacto BPC: vida independente comprometida
                
                Síndrome manguito rotador:
                - Dor e limitação movimento ombro
                - Impossibilidade carregar peso
                - Atividades comprometidas: trabalho braços elevados
                - CID-10: M75.1
                
                Dor lombar crônica:
                - Limitação: flexão, rotação do tronco
                - Impacto: levantar peso, permanecer em pé
                - Profissões afetadas: pedreiro, operário, faxineira
                
                Lesões de punho/mão:
                - Limitação: preensão, força de pinça
                - Impacto: digitação, uso de ferramentas
                - Profissões afetadas: secretária, operador
                """, metadata={"tipo": "sintomas", "categoria": "correlacoes"}),
                
                # Documentos sobre Isenção IR
                Document(text="""
                ISENÇÃO IMPOSTO DE RENDA - Lei 7.713/88:
                
                Doenças graves elegíveis:
                - Neoplasia maligna (câncer)
                - Cardiopatia grave
                - Doença de Parkinson
                - Esclerose múltipla
                - Nefropatia grave
                - Hepatopatia grave
                - Cegueira
                - Hanseníase
                - Paralisia irreversível e incapacitante
                - Tuberculose ativa
                - AIDS/HIV
                - Fibrose cística
                
                CRITÉRIOS:
                - Diagnóstico confirmado por médico
                - Doença deve estar na lista legal
                - Tempo da doença documentado
                - Corresponder ao rol de doenças graves
                """, metadata={"tipo": "isencao_ir", "categoria": "criterios"}),
                
                # Documentos sobre Auxílio-Acidente
                Document(text="""
                AUXÍLIO-ACIDENTE PREVIDENCIÁRIO:
                
                Características:
                - Redução da capacidade laborativa
                - Não é incapacidade total
                - Permite exercício parcial da atividade
                - Impacto econômico na capacidade produtiva
                
                Critérios:
                - Sequela definitiva de acidente de trabalho
                - Redução permanente da capacidade
                - Capacidade residual para trabalho
                - Necessidade de adaptações
                
                Avaliação:
                - Percentual de redução da capacidade
                - Tipo de limitação funcional
                - Possibilidade de readaptação
                - Impacto na produtividade
                """, metadata={"tipo": "auxilio_acidente", "categoria": "criterios"})
            ]
            
            # Criar índice vetorial
            self.index = VectorStoreIndex.from_documents(medical_documents)
            self.query_engine = self.index.as_query_engine(
                similarity_top_k=3,
                response_mode="compact"
            )
            
            print("✅ Base de conhecimento médico carregada (5 tipos de perícia)")
            
        except Exception as e:
            print(f"❌ Erro ao carregar base de conhecimento: {e}")
            # Fallback: funcionamento sem RAG
            self.index = None
            self.query_engine = None
            print("⚠️ Funcionando sem RAG - usando extração direta")
    
    def retrieve_relevant_medical_info(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Recupera informações médicas relevantes baseadas nas entidades extraídas"""
        
        if not self.query_engine:
            return self._fallback_knowledge_retrieval(entities)
        
        try:
            # Construir query baseada nas entidades
            query_parts = []
            
            if entities.get('sintomas_relatados'):
                sintomas = [s.get('sintoma', '') for s in entities['sintomas_relatados'] if isinstance(s, dict)]
                if sintomas:
                    query_parts.append(f"sintomas: {', '.join(sintomas)}")
            
            if entities.get('limitacoes_funcionais'):
                limitacoes = [l.get('atividade_limitada', '') for l in entities['limitacoes_funcionais'] if isinstance(l, dict)]
                if limitacoes:
                    query_parts.append(f"limitações: {', '.join(limitacoes)}")
            
            if entities.get('dados_pessoais', {}).get('profissao'):
                profissao = entities['dados_pessoais']['profissao']
                query_parts.append(f"profissão: {profissao}")
            
            # Query estruturada
            if query_parts:
                query = f"Informações médicas sobre: {' | '.join(query_parts)}"
            else:
                query = "Critérios médicos gerais para perícia"
            
            # Recuperar conhecimento relevante
            response = self.query_engine.query(query)
            
            # Extrair documentos fonte
            source_nodes = response.source_nodes if hasattr(response, 'source_nodes') else []
            
            return {
                'retrieved_knowledge': str(response),
                'source_documents': [node.node.text for node in source_nodes],
                'relevance_score': self._calculate_relevance_score(entities, str(response)),
                'query_used': query,
                'rag_available': True
            }
            
        except Exception as e:
            print(f"❌ Erro na recuperação RAG: {e}")
            return self._fallback_knowledge_retrieval(entities)
    
    def _fallback_knowledge_retrieval(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback quando RAG não está disponível"""
        
        # Conhecimento básico sem RAG
        basic_knowledge = """
        Critérios básicos para avaliação médica:
        
        BPC/LOAS: Impedimento de longo prazo que compromete vida independente
        Incapacidade Laboral: Impossibilidade de exercer função habitual
        Isenção IR: Doenças graves conforme Lei 7.713/88
        Auxílio-Acidente: Redução permanente da capacidade laborativa
        
        Avaliação sempre deve considerar:
        - Limitações funcionais específicas
        - Correlação com atividade profissional
        - Necessidade de cuidador (para BPC)
        - Capacidade de trabalho (para INSS)
        """
        
        return {
            'retrieved_knowledge': basic_knowledge,
            'source_documents': ['Conhecimento médico básico'],
            'relevance_score': 0.5,
            'query_used': 'Fallback - conhecimento básico',
            'rag_available': False
        }
    
    def _calculate_relevance_score(self, entities: Dict, retrieved_text: str) -> float:
        """Calcula score de relevância entre entidades e conhecimento recuperado"""
        entity_terms = []
        
        # Extrair termos das entidades
        if entities.get('sintomas_relatados'):
            for sintoma in entities['sintomas_relatados']:
                if isinstance(sintoma, dict) and 'sintoma' in sintoma:
                    entity_terms.append(sintoma['sintoma'])
        
        if entities.get('limitacoes_funcionais'):
            for limitacao in entities['limitacoes_funcionais']:
                if isinstance(limitacao, dict) and 'atividade_limitada' in limitacao:
                    entity_terms.append(limitacao['atividade_limitada'])
        
        if entities.get('dados_pessoais', {}).get('profissao'):
            entity_terms.append(entities['dados_pessoais']['profissao'])
        
        # Calcular matches
        if not entity_terms:
            return 0.5  # Score neutro se não há termos
        
        retrieved_lower = retrieved_text.lower()
        matches = sum(1 for term in entity_terms if term.lower() in retrieved_lower)
        
        relevance = matches / len(entity_terms)
        
        # Bonus por termos médicos específicos no texto recuperado
        medical_terms = ['limitação', 'incapacidade', 'diagnóstico', 'tratamento', 'sintoma']
        medical_matches = sum(1 for term in medical_terms if term in retrieved_lower)
        medical_bonus = min(0.3, medical_matches * 0.1)
        
        return min(1.0, relevance + medical_bonus)
    
    def get_context_specific_knowledge(self, context_type: str) -> str:
        """Retorna conhecimento específico para cada contexto"""
        
        context_knowledge = {
            'bpc': """
            BPC/LOAS - Critérios Lei 8.742/93:
            - Impedimento de longo prazo (mínimo 2 anos)
            - Natureza física, mental, intelectual ou sensorial
            - Restrição para participação social e vida independente
            - Necessidade de cuidador para atividades básicas
            - Foco: autonomia e participação social
            """,
            
            'incapacidade': """
            Incapacidade Laboral INSS:
            - Impossibilidade para função habitual
            - Correlação com atividade profissional específica
            - Limitações biomecânicas documentadas
            - Avaliação de capacidade residual
            - Foco: capacidade para o trabalho
            """,
            
            'isencao_ir': """
            Isenção Imposto de Renda - Lei 7.713/88:
            - Doenças graves específicas da legislação
            - Diagnóstico confirmado por médico
            - Tempo da doença documentado
            - Correspondência com rol legal
            - Foco: doença grave comprovada
            """,
            
            'auxilio_acidente': """
            Auxílio-Acidente:
            - Redução permanente da capacidade laborativa
            - Sequela de acidente de trabalho
            - Capacidade residual preservada
            - Possibilidade de exercício parcial
            - Foco: redução, não incapacidade total
            """,
            
            'pericia': """
            Perícia Médica Legal:
            - Nexo causal entre evento e sequela
            - Grau de comprometimento
            - Análise de documentos médicos
            - Avaliação funcional objetiva
            - Foco: relação causal e dano
            """
        }
        
        return context_knowledge.get(context_type, context_knowledge['incapacidade'])

# Instância global
medical_rag = MedicalRAGService()
