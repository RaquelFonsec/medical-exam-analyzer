
"""
Sistema Integrado de Análise Médica - Exemplo Principal
Demonstra o uso completo do sistema com LangGraph + RAG + Pydantic
"""

import asyncio
import os
import sys
from typing import Dict, Any
from datetime import datetime

# Adicionar path do sistema médico
sys.path.append('.')

# Importações do sistema médico
from medical_system.config.system_config import (
    MedicalSystemConfiguration,
    load_system_config,
    validate_system_setup
)
from medical_system.utils.validators import (
    validate_medical_analysis_result,
    validate_patient_data,
    calculate_analysis_quality_score
)

# Mock do serviço RAG para demonstração
class MockRAGService:
    """Serviço RAG mock para demonstração (substitua pela sua implementação)"""
    
    def __init__(self):
        # Base de conhecimento mock
        self.knowledge_base = [
            "Auxílio-doença é concedido ao segurado incapacitado temporariamente para o trabalho.",
            "BPC/LOAS é destinado a pessoas com deficiência ou idosos acima de 65 anos em situação de vulnerabilidade.",
            "Aposentadoria por invalidez é para incapacidade total e permanente para qualquer atividade laborativa.",
            "Dor lombar crônica pode causar limitação funcional significativa para atividades laborativas.",
            "Transtornos mentais graves podem gerar incapacidade para o trabalho e convívio social.",
            "Cardiopatias graves limitam a capacidade para esforços físicos e atividades laborativas.",
            "Deficiência visual severa impacta significativamente as atividades da vida diária.",
            "Artrose avançada causa dor e limitação de movimento, afetando a capacidade laborativa."
        ]
    
    def search_similar_documents(self, query: str, k: int = 3):
        """Mock de busca em documentos similares"""
        # Simular busca por palavras-chave
        query_lower = query.lower()
        scores = []
        
        for i, doc in enumerate(self.knowledge_base):
            doc_lower = doc.lower()
            score = 0.5  # Score base
            
            # Aumentar score por palavras-chave encontradas
            keywords = query_lower.split()[:3]  # Primeiras 3 palavras
            for keyword in keywords:
                if keyword in doc_lower:
                    score += 0.2
            
            scores.append((doc, min(score, 1.0)))
        
        # Ordenar por score e retornar top k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

async def process_medical_consultation(
    transcription_text: str,
    openai_api_key: str,
    rag_service = None,
    faiss_index = None,
    custom_config: Dict = None
) -> Dict[str, Any]:
    """
    Função principal para processar consulta médica
    
    Args:
        transcription_text: Texto da transcrição da consulta médica
        openai_api_key: Chave da API OpenAI
        rag_service: Serviço RAG (opcional, usa mock se não fornecido)
        faiss_index: Índice FAISS (opcional)
        custom_config: Configurações personalizadas (opcional)
        
    Returns:
        Dict com resultado completo da análise
    """
    
    print(f"🏥 INICIANDO PROCESSAMENTO MÉDICO")
    print(f"📄 Texto: {len(transcription_text)} caracteres")
    print("=" * 60)
    
    # Usar RAG mock se não fornecido
    if rag_service is None:
        rag_service = MockRAGService()
        print("🔧 Usando RAG mock para demonstração")
    
    try:
        # Criar sistema integrado com configurações
        medical_system, config = MedicalSystemConfiguration.create_complete_system(
            openai_api_key=openai_api_key,
            rag_service=rag_service,
            faiss_index=faiss_index,
            custom_config=custom_config
        )
        
        # Processar transcrição médica
        print("⚡ Executando pipeline de análise...")
        result = await medical_system.process_medical_transcription(transcription_text)
        
        # Validar resultado
        validation = validate_medical_analysis_result(result)
        result["validation"] = validation
        
        print(f"✅ Análise concluída!")
        return result
        
    except Exception as e:
        print(f"❌ Erro durante processamento: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def display_analysis_results(result: Dict[str, Any]):
    """Exibe resultados da análise de forma organizada"""
    
    print("\n🏥 RESULTADO DA ANÁLISE MÉDICA")
    print("=" * 60)
    
    # Status geral
    status = result.get('status', 'unknown')
    status_icon = "✅" if status == "success" else "❌"
    print(f"{status_icon} Status: {status.upper()}")
    
    if status == "error":
        print(f"❌ Erro: {result.get('error', 'Erro desconhecido')}")
        return
    
    # Dados do paciente
    paciente = result.get('paciente', {})
    identificacao = paciente.get('identificacao', {})
    
    print(f"\n👤 DADOS DO PACIENTE:")
    print(f"   Nome: {identificacao.get('nome', 'Não informado')}")
    print(f"   Idade: {paciente.get('idade_anos', 'Não informada')} anos")
    print(f"   Profissão: {paciente.get('profissao', 'Não informada')}")
    
    # Análise médica
    analise = result.get('analise_medica', {})
    print(f"\n🔬 ANÁLISE MÉDICA:")
    print(f"   Especialidade: {analise.get('especialidade_principal', 'Não identificada').title()}")
    print(f"   CID Principal: {analise.get('cid_principal', 'Não informado')}")
    print(f"   Descrição: {analise.get('cid_descricao', 'Não informada')}")
    print(f"   Gravidade: {analise.get('gravidade', 'Não avaliada').title()}")
    print(f"   Prognóstico: {analise.get('prognostico', 'Não informado').title()}")
    
    # Classificação do benefício
    beneficio = result.get('beneficio_classificado', 'NÃO_CLASSIFICADO')
    print(f"\n🎯 CLASSIFICAÇÃO DO BENEFÍCIO:")
    print(f"   Tipo: {beneficio}")
    print(f"   Justificativa: {result.get('justificativa_beneficio', 'Não disponível')[:100]}...")
    
    # Capacidade funcional
    print(f"\n⚕️  CAPACIDADE FUNCIONAL:")
    print(f"   Capacidade Laborativa: {result.get('capacidade_laborativa', 'Não avaliada').title()}")
    
    limitacoes = result.get('limitacoes_funcionais', [])
    if limitacoes:
        print(f"   Limitações: {', '.join(limitacoes)}")
    
    auxilio_terceiros = result.get('necessita_auxilio_terceiros', False)
    print(f"   Necessita Auxílio de Terceiros: {'Sim' if auxilio_terceiros else 'Não'}")
    
    # Nexo ocupacional
    nexo = result.get('nexo_ocupacional', {})
    print(f"\n🏭 NEXO OCUPACIONAL:")
    print(f"   Identificado: {'Sim' if nexo.get('identificado', False) else 'Não'}")
    print(f"   Observação: {nexo.get('observacao', 'Nenhuma')}")
    
    # Recomendações
    recomendacoes = result.get('recomendacoes', {})
    print(f"\n💡 RECOMENDAÇÕES:")
    print(f"   Especialidade Indicada: {recomendacoes.get('especialidade_indicada', 'Não especificada').title()}")
    
    exames = recomendacoes.get('exames_complementares', [])
    if exames:
        print(f"   Exames Complementares:")
        for exame in exames[:3]:  # Mostrar até 3 exames
            print(f"     • {exame}")
    
    # Validação e qualidade
    validation = result.get('validation', {})
    if validation:
        print(f"\n📊 QUALIDADE DA ANÁLISE:")
        print(f"   Válida: {'Sim' if validation.get('valid', False) else 'Não'}")
        print(f"   Score de Qualidade: {validation.get('score', 0):.1f}/100")
        
        if validation.get('warnings'):
            print(f"   Avisos: {len(validation['warnings'])} encontrado(s)")
        
        if validation.get('errors'):
            print(f"   Erros: {len(validation['errors'])} encontrado(s)")
    
    # Metadados
    metadados = result.get('metadados', {})
    print(f"\n📋 METADADOS:")
    print(f"   Método: {metadados.get('metodo_analise', 'Desconhecido')}")
    print(f"   Confiabilidade: {metadados.get('confiabilidade', 'Não avaliada').title()}")
    print(f"   Caracteres Processados: {metadados.get('texto_original_caracteres', 0)}")
    
    # Métricas do pipeline (se disponível)
    pipeline_metrics = metadados.get('pipeline_metrics', {})
    if pipeline_metrics:
        print(f"   Taxa de Sucesso: {pipeline_metrics.get('success_rate', 0):.1f}%")
        print(f"   Tempo Médio: {pipeline_metrics.get('average_processing_time', 0):.2f}s")

def display_medical_report(result: Dict[str, Any]):
    """Exibe o laudo médico completo"""
    
    laudo = result.get('laudo_medico', '')
    if not laudo:
        print("\n❌ Laudo médico não disponível")
        return
    
    print("\n📄 LAUDO MÉDICO COMPLETO")
    print("=" * 60)
    print(laudo)
    print("=" * 60)

async def demo_analysis():
    """Demonstração completa do sistema"""
    
    print("🏥 SISTEMA INTEGRADO DE ANÁLISE MÉDICA")
    print("🚀 Demonstração Completa")
    print("=" * 60)
    
    # Verificar configuração
    if not validate_system_setup():
        print("❌ Sistema não está configurado corretamente")
        requirements = MedicalSystemConfiguration.validate_system_requirements()
        
        if requirements['critical_issues']:
            print("\n💥 Problemas críticos:")
            for issue in requirements['critical_issues']:
                print(f"   • {issue}")
        
        print("\n💡 Configure o sistema antes de continuar")
        return None
    
    # Verificar API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ Configure a variável de ambiente OPENAI_API_KEY")
        print("   Exemplo: export OPENAI_API_KEY='sua-chave-aqui'")
        return None
    
    # Casos de teste
    test_cases = [
        {
            "name": "Caso 1: Dor Lombar - Carpinteiro",
            "transcription": """
            Paciente João Silva, 45 anos, trabalha há 20 anos como carpinteiro.
            Refere dor lombar intensa há 6 meses, com irradiação para perna direita.
            Dor piora com movimento e melhora com repouso. Não consegue mais carregar peso.
            Trabalha 8 horas diárias em pé, carregando materiais pesados.
            Radiografia mostra artrose L4-L5. Fez fisioterapia sem melhora significativa.
            Não consegue mais exercer sua função devido à dor e limitação de movimento.
            Solicita auxílio-doença para afastamento do trabalho.
            """
        },
        {
            "name": "Caso 2: Depressão - Aposentado",
            "transcription": """
            Paciente Maria Santos, 68 anos, aposentada há 3 anos.
            Apresenta quadro depressivo grave há 1 ano, com ideação suicida.
            Isolamento social, perda de interesse em atividades, insônia.
            Faz uso de sertralina 100mg e clonazepam 2mg.
            Histórico de internação psiquiátrica recente por tentativa de suicídio.
            Mora sozinha, sem renda além da aposentadoria de 1 salário mínimo.
            Filha solicita BPC para complemento de renda devido às despesas médicas.
            """
        },
        {
            "name": "Caso 3: Deficiência Visual - Jovem",
            "transcription": """
            Paciente Pedro Costa, 28 anos, desenvolvedor de software.
            Cegueira progressiva por glaucoma há 2 anos, já com perda visual bilateral severa.
            Acuidade visual 20/400 em ambos os olhos, não corrigível.
            Fazia uso de computador 10 horas/dia, agora impossível trabalhar.
            Nunca contribuiu para INSS por trabalhar como autônomo informal.
            Mora com os pais, família com renda per capita de R$ 200,00.
            Solicita BPC/LOAS por deficiência visual e vulnerabilidade social.
            """
        }
    ]
    
    # Configurações personalizadas para demo
    custom_config = {
        "pipeline_timeout_seconds": 180,  # 3 minutos para demo
        "validation_quality_threshold": 60.0,  # Threshold mais baixo para demo
        "system_enable_audit_log": False  # Desabilitar logs extensos na demo
    }
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔬 PROCESSANDO {test_case['name'].upper()}")
        print("-" * 50)
        
        try:
            # Processar caso
            result = await process_medical_consultation(
                transcription_text=test_case['transcription'],
                openai_api_key=openai_api_key,
                custom_config=custom_config
            )
            
            # Exibir resultados
            display_analysis_results(result)
            
            # Perguntar se quer ver o laudo completo
            print(f"\n📄 Deseja ver o laudo médico completo do {test_case['name']}?")
            print("   (Pressione Enter para continuar ou 'l' + Enter para ver laudo)")
            
            user_input = input().strip().lower()
            if user_input == 'l':
                display_medical_report(result)
            
            results.append({
                "case": test_case['name'],
                "result": result,
                "success": result.get('status') == 'success'
            })
            
            # Pausa entre casos
            if i < len(test_cases):
                print(f"\n⏸️  Pressione Enter para processar próximo caso...")
                input()
        
        except Exception as e:
            print(f"❌ Erro no caso {test_case['name']}: {str(e)}")
            results.append({
                "case": test_case['name'],
                "result": {"status": "error", "error": str(e)},
                "success": False
            })
    
    # Resumo final
    print(f"\n📊 RESUMO DA DEMONSTRAÇÃO")
    print("=" * 60)
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"✅ Casos processados com sucesso: {successful}/{total}")
    print(f"📈 Taxa de sucesso: {(successful/total)*100:.1f}%")
    
    # Detalhes por caso
    for result in results:
        status_icon = "✅" if result['success'] else "❌"
        case_result = result['result']
        
        print(f"\n{status_icon} {result['case']}:")
        
        if result['success']:
            beneficio = case_result.get('beneficio_classificado', 'NÃO_CLASSIFICADO')
            quality = case_result.get('validation', {}).get('score', 0)
            print(f"   Benefício: {beneficio}")
            print(f"   Qualidade: {quality:.1f}/100")
        else:
            print(f"   Erro: {case_result.get('error', 'Erro desconhecido')}")
    
    print(f"\n🎉 Demonstração concluída!")
    print(f"💡 Para usar em produção:")
    print(f"   1. Configure seu próprio serviço RAG")
    print(f"   2. Ajuste as configurações conforme necessário")
    print(f"   3. Implemente validações adicionais específicas")
    print(f"   4. Configure monitoramento e logs")
    
    return results

def main():
    """Função principal do sistema"""
    
    print("🏥 SISTEMA INTEGRADO DE ANÁLISE MÉDICA")
    print("⚕️  Análise Automatizada de Benefícios Previdenciários")
    print("🤖 Powered by LangGraph + RAG + Pydantic")
    print("=" * 60)
    
    # Menu de opções
    while True:
        print(f"\n📋 MENU PRINCIPAL:")
        print(f"   1. 🚀 Executar Demonstração Completa")
        print(f"   2. 🔧 Validar Configuração do Sistema")
        print(f"   3. ⚙️  Gerar Template de Configuração")
        print(f"   4. 📊 Processar Caso Individual")
        print(f"   5. ❌ Sair")
        
        try:
            choice = input(f"\n👉 Escolha uma opção (1-5): ").strip()
            
            if choice == '1':
                print(f"\n🚀 Iniciando demonstração...")
                asyncio.run(demo_analysis())
                
            elif choice == '2':
                print(f"\n🔧 Validando sistema...")
                requirements = MedicalSystemConfiguration.validate_system_requirements()
                
                if requirements['system_ready']:
                    print("✅ Sistema configurado corretamente!")
                else:
                    print("❌ Problemas encontrados:")
                    for issue in requirements['critical_issues']:
                        print(f"   • {issue}")
                
                if requirements['warnings']:
                    print("\n⚠️  Avisos:")
                    for warning in requirements['warnings']:
                        print(f"   • {warning}")
                        
            elif choice == '3':
                print(f"\n⚙️  Gerando template...")
                success = MedicalSystemConfiguration.generate_config_template()
                if success:
                    print("✅ Template criado: medical_system_config.json")
                    
            elif choice == '4':
                print(f"\n📊 Processamento individual:")
                transcription = input("Digite a transcrição médica: ").strip()
                
                if transcription:
                    openai_api_key = os.getenv("OPENAI_API_KEY")
                    if openai_api_key:
                        print("⚡ Processando...")
                        result = asyncio.run(process_medical_consultation(transcription, openai_api_key))
                        display_analysis_results(result)
                    else:
                        print("❌ Configure OPENAI_API_KEY")
                else:
                    print("❌ Transcrição não pode estar vazia")
                    
            elif choice == '5':
                print(f"\n👋 Obrigado por usar o Sistema de Análise Médica!")
                break
                
            else:
                print(f"❌ Opção inválida. Escolha entre 1-5.")
                
        except KeyboardInterrupt:
            print(f"\n\n👋 Sistema interrompido pelo usuário. Até logo!")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")

if __name__ == "__main__":
    main()