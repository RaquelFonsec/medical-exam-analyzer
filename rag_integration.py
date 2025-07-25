#!/usr/bin/env python3
"""Script para integrar RAG ao sistema médico existente"""

import os
import sys
import asyncio
from typing import List, Dict, Any

# Adicionar o diretório do backend ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Imports do RAG
from app.services.rag.medical_rag_service import MedicalRAGService

class MedicalRAGIntegrator:
    """Integrador RAG para o sistema médico existente"""
    
    def __init__(self):
        self.rag_service = MedicalRAGService(
            faiss_index_path="data/medical_knowledge.faiss",
            chunks_path="data/medical_chunks.pkl"
        )
        
        # Criar diretório de dados se não existir
        os.makedirs("data", exist_ok=True)
        os.makedirs("training_data", exist_ok=True)
        
        print("✅ RAG Integrator inicializado")
    
    def load_pdf_examples_from_directory(self, pdf_directory: str) -> List[str]:
        """Carregar exemplos de PDFs de um diretório"""
        examples = []
        
        if not os.path.exists(pdf_directory):
            print(f"⚠️ Diretório não encontrado: {pdf_directory}")
            return examples
        
        for filename in os.listdir(pdf_directory):
            if filename.endswith('.txt'):
                filepath = os.path.join(pdf_directory, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if len(content.strip()) > 100:
                            examples.append(content)
                            print(f"📄 Carregado: {filename}")
                except Exception as e:
                    print(f"❌ Erro ao carregar {filename}: {e}")
        
        print(f"✅ {len(examples)} documentos carregados")
        return examples
    
    def setup_knowledge_base(self, pdf_directory: str = None, manual_examples: List[str] = None):
        """Configurar base de conhecimento com exemplos"""
        examples = []
        
        if pdf_directory:
            examples.extend(self.load_pdf_examples_from_directory(pdf_directory))
        
        if manual_examples:
            examples.extend(manual_examples)
        
        if not examples:
            examples = self._get_default_examples()
            print("📚 Usando exemplos padrão")
        
        if examples:
            print("🔄 Construindo base de conhecimento...")
            self.rag_service.add_documents_to_knowledge_base(examples)
            print("✅ Base de conhecimento configurada")
        else:
            print("⚠️ Nenhum exemplo disponível")
    
    def _get_default_examples(self) -> List[str]:
        """Exemplos padrão se não houver PDFs"""
        return [
            """LAUDO MÉDICO ORTOPÉDICO

IDENTIFICAÇÃO:
Paciente: João da Silva, 45 anos, masculino
Profissão: Pedreiro
Data: 15/07/2024

HISTÓRIA CLÍNICA:
Paciente relata acidente de trabalho há 2 anos, quando caiu de andaime durante construção.
Sofreu fratura de vértebra lombar L3-L4, com sequelas funcionais.
Refere dor lombar crônica e limitação para levantamento de peso.

LIMITAÇÕES FUNCIONAIS:
- Incapacidade para levantamento de peso superior a 10kg
- Dificuldade para trabalhar em posições incômodas
- Limitação para trabalho em altura
- Claudicação após caminhadas prolongadas

DIAGNÓSTICO:
Sequelas de fratura de coluna vertebral lombar com limitação funcional
CID-10: S22.1 - Fratura de vértebra torácica

CONCLUSÃO:
Paciente apresenta limitações funcionais decorrentes de sequelas traumáticas que o impossibilitam 
para o exercício da profissão de pedreiro. As limitações são incompatíveis com as exigências 
da função, caracterizando incapacidade laboral.

RECOMENDAÇÕES:
- Acompanhamento ortopédico especializado
- Fisioterapia para manutenção da capacidade funcional
- Avaliação para reabilitação profissional

Dr. Carlos Mendes - CRM 12345-SP
Especialista em Ortopedia""",

            """LAUDO PSIQUIÁTRICO

IDENTIFICAÇÃO:
Paciente: Maria Santos, 38 anos, feminino
Profissão: Professora
Data: 20/07/2024

HISTÓRIA CLÍNICA:
Paciente professora há 15 anos, apresenta quadro depressivo iniciado há 8 meses.
Refere sobrecarga de trabalho, estresse constante e deterioração do ambiente escolar.
Sintomas incluem tristeza persistente, fadiga, insônia, diminuição da concentração.

AVALIAÇÃO MENTAL:
- Humor deprimido
- Anedonia significativa
- Fadiga e perda de energia
- Dificuldade de concentração
- Sentimentos de inutilidade
- Ideação de incapacidade laboral

LIMITAÇÕES FUNCIONAIS:
- Comprometimento da capacidade de concentração para atividades pedagógicas
- Dificuldade para lidar com estresse do ambiente escolar
- Fadiga excessiva interferindo na qualidade do ensino
- Comprometimento das relações interpessoais com alunos

DIAGNÓSTICO:
Episódio Depressivo Maior, grave, sem sintomas psicóticos
CID-10: F32.2

CONCLUSÃO:
Paciente apresenta transtorno mental que compromete significativamente sua capacidade
para exercer atividades docentes. O quadro atual é incompatível com as demandas
emocionais e cognitivas do magistério.

TRATAMENTO:
Em uso de antidepressivo e acompanhamento psicoterapêutico.

Dra. Ana Silva - CRM 67890-SP
Especialista em Psiquiatria""",

            """LAUDO OTORRINOLARINGOLÓGICO

IDENTIFICAÇÃO:
Paciente: Carlos Oliveira, 52 anos, masculino
Profissão: Operador de telemarketing
Data: 25/07/2024

HISTÓRIA CLÍNICA:
Paciente operador de telemarketing há 12 anos, com uso intensivo de headset.
Desenvolveu perda auditiva progressiva bilateral nos últimos 5 anos.
Refere dificuldade crescente para compreensão telefônica e zumbido constante.

EXAME OTORRINOLARINGOLÓGICO:
- Otoscopia: condutos auditivos externos livres bilateralmente
- Audiometria tonal: perda auditiva neurossensorial bilateral
- Logoaudiometria: comprometimento do reconhecimento de fala
- Timpanometria: curvas tipo A bilateral

RESULTADOS AUDIOMÉTRICOS:
- Orelha direita: perda moderada a severa (60-70 dB)
- Orelha esquerda: perda moderada (50-60 dB)
- Discriminação vocal comprometida bilateralmente

LIMITAÇÕES FUNCIONAIS:
- Incapacidade para comunicação telefônica eficaz
- Dificuldade para compreensão de fala em ambiente ruidoso
- Necessidade de amplificação sonora
- Comprometimento da qualidade do atendimento ao cliente

DIAGNÓSTICO:
Perda auditiva neurossensorial bilateral, relacionada ao trabalho
CID-10: H90.3 - Perda auditiva neurossensorial bilateral

NEXO CAUSAL:
Perda auditiva compatível com exposição ocupacional a ruído
através do uso prolongado de equipamentos de áudio.

CONCLUSÃO:
Paciente apresenta perda auditiva ocupacional que o impossibilita para
o exercício da função de operador de telemarketing, atividade que
exige acuidade auditiva preservada.

Dr. Roberto Lima - CRM 13579-SP
Especialista em Otorrinolaringologia"""
        ]
    
    def test_rag_system(self, patient_info: str = "João Silva, 45", 
                       transcription: str = "Sou pedreiro há 15 anos, sofri acidente e fraturei a coluna"):
        """Testar sistema RAG com exemplo"""
        
        print("\n=== TESTE DO SISTEMA RAG ===\n")
        
        print("🔍 Buscando casos similares...")
        similar_cases = self.rag_service.search_similar_cases(f"{patient_info} {transcription}", top_k=3)
        
        print(f"📊 Encontrados {len(similar_cases)} casos similares:")
        for i, case in enumerate(similar_cases, 1):
            print(f"{i}. Score: {case['similarity_score']:.3f} | Tipo: {case['type']}")
            print(f"   Texto: {case['text'][:100]}...")
            print()
        
        print("📋 Gerando laudo com RAG...")
        rag_response = self.rag_service.generate_rag_response(patient_info, transcription)
        
        if rag_response['success']:
            print("✅ Laudo gerado com sucesso!")
            print("\n" + "="*50)
            print(rag_response['response'])
            print("="*50)
            print(f"\nCasos similares utilizados: {rag_response['similar_cases_count']}")
            print(f"Score de similaridade máximo: {rag_response['top_similarity_score']:.3f}")
        else:
            print(f"❌ Erro na geração: {rag_response['error']}")

def main():
    """Função principal de configuração"""
    
    print("🚀 CONFIGURANDO SISTEMA RAG PARA ANÁLISE MÉDICA")
    print("="*60)
    
    integrator = MedicalRAGIntegrator()
    
    pdf_directory = "training_data"
    
    if os.path.exists(pdf_directory):
        print(f"📁 Usando PDFs do diretório: {pdf_directory}")
        integrator.setup_knowledge_base(pdf_directory=pdf_directory)
    else:
        print("📚 Usando exemplos padrão (PDF directory não encontrado)")
        integrator.setup_knowledge_base()
    
    integrator.test_rag_system()
    
    print("\n✅ SISTEMA RAG CONFIGURADO COM SUCESSO!")
    print("\nPara usar no seu sistema existente:")
    print("1. from rag_integration import MedicalRAGIntegrator")
    print("2. integrator = MedicalRAGIntegrator()")
    print("3. integrator.rag_service.generate_rag_response(patient_info, transcription)")
    
    return integrator

async def test_integration():
    """Testar integração completa"""
    
    print("\n🧪 TESTE DE INTEGRAÇÃO COMPLETA")
    print("="*50)
    
    integrator = main()
    
    patient_info = "Maria Santos, 38"
    transcription = "Sou professora há 15 anos, desenvolvi depressão e não consigo mais dar aulas"
    
    print(f"\n📝 Testando análise para: {patient_info}")
    print(f"💬 Transcrição: {transcription}")
    
    rag_response = integrator.rag_service.generate_rag_response(patient_info, transcription)
    
    print("\n📋 RESULTADO DA ANÁLISE COM RAG:")
    print("="*50)
    
    if rag_response.get('success'):
        print(f"✅ Status: Sucesso")
        print(f"📊 Score de Similaridade: {rag_response.get('top_similarity_score', 0):.3f}")
        print(f"📚 Casos Utilizados: {rag_response.get('similar_cases_count', 0)}")
        
        print(f"\n📋 LAUDO GERADO:")
        print("-" * 50)
        print(rag_response.get('response', 'Não disponível'))
    else:
        print(f"❌ Erro: {rag_response.get('error', 'Desconhecido')}")

if __name__ == "__main__":
    integrator = main()
    
    print("\n" + "="*60)
    asyncio.run(test_integration())
    
    print("\n🎉 CONFIGURAÇÃO COMPLETA!")
    print("\nPróximos passos:")
    print("1. Adicione seus PDFs convertidos em training_data/")
    print("2. Execute: python rag_integration.py para reconfigurar")
    print("3. O sistema estará pronto para usar RAG nas análises médicas")
