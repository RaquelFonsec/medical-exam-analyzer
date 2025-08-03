# ============================================================================
# RAG FAISS INTEGRATION SETUP
# Configuração e inicialização da base de conhecimento médico
# ============================================================================

import os
import json
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class RAGMedicalSetup:
    """Setup e configuração do RAG FAISS para laudos médicos"""
    
    def __init__(self, base_path: str = "./rag"):
        self.base_path = Path(base_path)
        self.ensure_directories()
    
    def ensure_directories(self):
        """Cria diretórios necessários"""
        directories = [
            self.base_path,
            self.base_path / "data",
            self.base_path / "indices", 
            self.base_path / "embeddings"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Diretório garantido: {directory}")
    
    def create_sample_medical_cases(self) -> List[Dict[str, Any]]:
        """Cria casos médicos de exemplo para a base FAISS"""
        
        sample_cases = [
            {
                "id": "caso_001",
                "tipo": "diabetes_hipertensao",
                "cid_principal": "E11.3",
                "cids_secundarios": ["I10", "F32.1"],
                "beneficio": "AUXÍLIO-DOENÇA",
                "content": """
                Paciente masculino, 45 anos, cozinheiro, apresenta diabetes mellitus tipo 2 com complicações oftálmicas (E11.3).
                Relata visão embaçada, mal estar no trabalho devido ao calor da cozinha, tontura frequente.
                Medicamentos: metformina 850mg 2x/dia, losartana 50mg 1x/dia.
                Pressão arterial: 18x12 mmHg (descompensada). Também apresenta episódio depressivo moderado (F32.1).
                Incapacidade temporária para atividades laborais habituais devido à exposição ao calor e esforço físico.
                Indicação: AUXÍLIO-DOENÇA por 90 dias com reavaliação.
                """,
                "gravidade": "MODERADA",
                "duration_months": 3,
                "keywords": ["diabetes", "hipertensão", "cozinheiro", "calor", "visão embaçada", "metformina", "losartana"]
            },
            
            {
                "id": "caso_002", 
                "tipo": "sindrome_tunel_carpo",
                "cid_principal": "G56.0",
                "cids_secundarios": ["M70.1"],
                "beneficio": "AUXÍLIO-DOENÇA",
                "content": """
                Paciente feminina, 38 anos, digitadora, síndrome do túnel do carpo bilateral (G56.0).
                Formigamento e dormência nas mãos, principalmente à noite. Bursite da mão direita (M70.1).
                Atividade repetitiva por 12 horas diárias há 8 anos. 
                Tratamento: anti-inflamatórios, fisioterapia, órteses noturnas.
                Resposta parcial ao tratamento. Limitação funcional significativa para digitação.
                Indicação: AUXÍLIO-DOENÇA por 60 dias com readaptação funcional posterior.
                """,
                "gravidade": "MODERADA",
                "duration_months": 2,
                "keywords": ["túnel do carpo", "digitadora", "formigamento", "dormência", "repetitivo", "fisioterapia"]
            },
            
            {
                "id": "caso_003",
                "tipo": "depressao_grave_ansiedade", 
                "cid_principal": "F32.2",
                "cids_secundarios": ["F41.1"],
                "beneficio": "AUXÍLIO-DOENÇA",
                "content": """
                Paciente masculino, 52 anos, professor, episódio depressivo grave sem sintomas psicóticos (F32.2).
                Transtorno de ansiedade generalizada (F41.1). Início há 8 meses após sobrecarga de trabalho.
                Sintomas: tristeza profunda, anedonia, insônia, fadiga, dificuldade de concentração.
                Medicamentos: sertralina 100mg, clonazepam 2mg, escitalopram 10mg.
                Tentativas de retorno ao trabalho falharam. Incapacidade total atual.
                Indicação: AUXÍLIO-DOENÇA por 120 dias com acompanhamento psiquiátrico intensivo.
                """,
                "gravidade": "GRAVE",
                "duration_months": 4,
                "keywords": ["depressão grave", "ansiedade", "professor", "sobrecarga", "sertralina", "insônia"]
            },
            
            {
                "id": "caso_004",
                "tipo": "lombalgia_cronica",
                "cid_principal": "M54.5", 
                "cids_secundarios": ["M51.1"],
                "beneficio": "AUXÍLIO-DOENÇA", 
                "content": """
                Paciente masculino, 41 anos, pedreiro, lombalgia crônica (M54.5).
                Transtorno de disco intervertebral lombar (M51.1). Dor constante há 2 anos.
                Limitação severa para carregar peso, subir escadas, flexão do tronco.
                Tratamento: anti-inflamatórios, relaxantes musculares, fisioterapia, RPG.
                Resposta insuficiente. Impossibilidade de continuar atividade de pedreiro.
                Indicação: AUXÍLIO-DOENÇA por 90 dias com avaliação para readaptação.
                """,
                "gravidade": "GRAVE",
                "duration_months": 3,
                "keywords": ["lombalgia", "pedreiro", "disco intervertebral", "carregar peso", "fisioterapia"]
            },
            
            {
                "id": "caso_005",
                "tipo": "hipertensao_diabetes_crianca",
                "cid_principal": "E10.3",
                "cids_secundarios": ["I10"],
                "beneficio": "BPC/LOAS",
                "content": """
                Paciente pediátrico, 12 anos, diabetes mellitus tipo 1 com complicações oftálmicas (E10.3).
                Hipertensão arterial secundária (I10). Família de baixa renda.
                Controle glicêmico difícil, múltiplas internações por cetoacidose.
                Tratamento: insulina NPH + regular, medicação anti-hipertensiva.
                Necessidades educacionais especiais, acompanhamento multidisciplinar.
                Limitações permanentes. Indicação: BPC/LOAS por deficiência permanente.
                """,
                "gravidade": "GRAVE",
                "duration_months": 999,  # Permanente
                "keywords": ["diabetes tipo 1", "criança", "cetoacidose", "insulina", "BPC", "baixa renda"]
            },
            
            {
                "id": "caso_006",
                "tipo": "infarto_recent_hipertensao",
                "cid_principal": "I21.9",
                "cids_secundarios": ["I10", "E78.5"],
                "beneficio": "AUXÍLIO-DOENÇA",
                "content": """
                Paciente masculino, 58 anos, motorista, infarto agudo do miocárdio (I21.9).
                Hipertensão arterial (I10), hiperlipidemia (E78.5). Evento há 3 semanas.
                Angioplastia primária com stent. Fração de ejeção 45%.
                Medicamentos: AAS, clopidogrel, atenolol, sinvastatina, enalapril.
                Restrição absoluta para dirigir veículos de carga por 6 meses.
                Indicação: AUXÍLIO-DOENÇA por 180 dias com reabilitação cardíaca.
                """,
                "gravidade": "GRAVE",
                "duration_months": 6,
                "keywords": ["infarto", "motorista", "angioplastia", "stent", "dirigir", "reabilitação cardíaca"]
            }
        ]
        
        return sample_cases
    
    def save_sample_cases(self, cases: List[Dict[str, Any]]):
        """Salva casos de exemplo em arquivo JSON"""
        
        cases_file = self.base_path / "data" / "medical_cases.json"
        
        with open(cases_file, 'w', encoding='utf-8') as f:
            json.dump(cases, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 {len(cases)} casos médicos salvos em: {cases_file}")
    
    def create_cid_knowledge_base(self) -> List[Dict[str, Any]]:
        """Cria base de conhecimento de CIDs"""
        
        cid_knowledge = [
            {
                "cid": "E11.3",
                "description": "Diabetes mellitus tipo 2 com complicações oftálmicas",
                "categoria": "Endócrino",
                "gravidade_usual": "MODERADA",
                "content": """
                CID E11.3 - Diabetes mellitus tipo 2 com complicações oftálmicas.
                Características: retinopatia diabética, edema macular, glaucoma secundário.
                Sintomas: visão embaçada, perda visual progressiva, dificuldade para enxergar à noite.
                Tratamento: controle glicêmico rigoroso, acompanhamento oftalmológico.
                Prognóstico: progressivo se não controlado adequadamente.
                Incapacidade: limitações visuais podem impedir atividades de precisão.
                """
            },
            
            {
                "cid": "G56.0", 
                "description": "Síndrome do túnel do carpo",
                "categoria": "Neurológico",
                "gravidade_usual": "MODERADA",
                "content": """
                CID G56.0 - Síndrome do túnel do carpo.
                Compressão do nervo mediano no punho. Comum em atividades repetitivas.
                Sintomas: formigamento, dormência, dor no polegar, indicador e médio.
                Piora noturna típica. Pode evoluir para fraqueza e atrofia tenar.
                Tratamento: órteses, anti-inflamatórios, fisioterapia, cirurgia.
                Incapacidade: limitação funcional para atividades manuais finas.
                """
            },
            
            {
                "cid": "F32.2",
                "description": "Episódio depressivo grave sem sintomas psicóticos", 
                "categoria": "Psiquiátrico",
                "gravidade_usual": "GRAVE",
                "content": """
                CID F32.2 - Episódio depressivo grave sem sintomas psicóticos.
                Sintomas severos: humor deprimido, anedonia, fadiga, culpa excessiva.
                Perda significativa de interesse, alterações do sono e apetite.
                Ideação suicida possível. Comprometimento funcional importante.
                Tratamento: antidepressivos, psicoterapia, às vezes hospitalização.
                Incapacidade: total temporária, com possibilidade de recuperação.
                """
            },
            
            {
                "cid": "I21.9",
                "description": "Infarto agudo do miocárdio não especificado",
                "categoria": "Cardiovascular", 
                "gravidade_usual": "GRAVE",
                "content": """
                CID I21.9 - Infarto agudo do miocárdio não especificado.
                Necrose do músculo cardíaco por oclusão coronariana aguda.
                Sintomas: dor torácica intensa, dispneia, sudorese, náuseas.
                Emergência médica. Tratamento: revascularização urgente.
                Complicações: insuficiência cardíaca, arritmias, morte súbita.
                Incapacidade: absoluta inicialmente, reabilitação gradual necessária.
                """
            }
        ]
        
        return cid_knowledge
    
    def save_cid_knowledge(self, cid_data: List[Dict[str, Any]]):
        """Salva base de conhecimento de CIDs"""
        
        cid_file = self.base_path / "data" / "cid_knowledge.json" 
        
        with open(cid_file, 'w', encoding='utf-8') as f:
            json.dump(cid_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 {len(cid_data)} CIDs salvos em: {cid_file}")
    
    def setup_complete_rag_base(self):
        """Setup completo da base RAG FAISS"""
        
        print("🔧 Configurando base RAG FAISS...")
        
        # 1. Criar casos médicos de exemplo
        medical_cases = self.create_sample_medical_cases()
        self.save_sample_cases(medical_cases)
        
        # 2. Criar base de conhecimento de CIDs
        cid_knowledge = self.create_cid_knowledge_base()
        self.save_cid_knowledge(cid_knowledge)
        
        # 3. Criar arquivo de configuração
        config = {
            "vector_dimension": 1536,  # OpenAI embeddings
            "index_type": "HNSW",
            "distance_metric": "cosine",
            "max_candidates": 100,
            "ef_search": 50,
            "medical_specialties": [
                "Endocrinologia", "Cardiologia", "Neurologia", 
                "Psiquiatria", "Ortopedia", "Medicina do Trabalho"
            ],
            "supported_benefits": [
                "AUXÍLIO-DOENÇA", "AUXÍLIO-ACIDENTE", 
                "BPC/LOAS", "APOSENTADORIA POR INVALIDEZ"
            ]
        }
        
        config_file = self.base_path / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Base RAG configurada em: {self.base_path}")
        print(f"📊 {len(medical_cases)} casos médicos")
        print(f"🏥 {len(cid_knowledge)} CIDs na base")
        print("🚀 Pronto para integração com Pydantic AI!")
        
        return {
            "base_path": str(self.base_path),
            "medical_cases_count": len(medical_cases),
            "cid_knowledge_count": len(cid_knowledge),
            "config": config
        }

# ============================================================================
# SCRIPT DE INICIALIZAÇÃO
# ============================================================================

def initialize_rag_system():
    """Inicializa sistema RAG FAISS"""
    
    print("🚀 Inicializando sistema RAG FAISS...")
    
    setup = RAGMedicalSetup()
    result = setup.setup_complete_rag_base()
    
    print("\n📋 RESUMO DA CONFIGURAÇÃO:")
    print(f"   📁 Diretório base: {result['base_path']}")
    print(f"   📊 Casos médicos: {result['medical_cases_count']}")
    print(f"   🏥 CIDs na base: {result['cid_knowledge_count']}")
    
    print("\n🔗 PRÓXIMOS PASSOS:")
    print("   1. Certifique-se de que pydantic_medical_service.py pode importar os dados")
    print("   2. Configure OPENAI_API_KEY para embeddings")
    print("   3. Execute o sistema principal integrado")
    
    return result

if __name__ == "__main__":
    initialize_rag_system()