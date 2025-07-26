#!/usr/bin/env python3
"""
Script para povoar a base RAG com casos específicos de benefícios previdenciários
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend/app'))

# Casos específicos para cada tipo de benefício
casos_beneficios = [
    # AUXÍLIO-DOENÇA
    {
        "tipo": "AUXÍLIO-DOENÇA",
        "cid": "S72.0",
        "caso": """João Silva, 32 anos, pedreiro.
        DIAGNÓSTICO: Fratura do fêmur direito em acidente de trabalho.
        SINTOMAS: Dor intensa, limitação de movimento, edema.
        TRATAMENTO: Cirurgia com haste intramedular, fisioterapia.
        PROGNÓSTICO: Recuperação esperada em 3-4 meses.
        CAPACIDADE: Incapacidade temporária para trabalho pesado.
        CLASSIFICAÇÃO: AUXÍLIO-DOENÇA por incapacidade temporária com recuperação prevista."""
    },
    {
        "tipo": "AUXÍLIO-DOENÇA",
        "cid": "J18.9", 
        "caso": """Maria Santos, 28 anos, enfermeira.
        DIAGNÓSTICO: Pneumonia bilateral adquirida na comunidade.
        SINTOMAS: Febre alta, tosse com expectoração, dispneia.
        TRATAMENTO: Antibioticoterapia, suporte respiratório.
        PROGNÓSTICO: Recuperação completa esperada em 4-6 semanas.
        CAPACIDADE: Afastamento temporário por risco de contágio.
        CLASSIFICAÇÃO: AUXÍLIO-DOENÇA por doença aguda tratável."""
    },
    {
        "tipo": "AUXÍLIO-DOENÇA",
        "cid": "F32.0",
        "caso": """Carlos Oliveira, 35 anos, contador.
        DIAGNÓSTICO: Episódio depressivo leve relacionado ao trabalho.
        SINTOMAS: Humor deprimido, fadiga, dificuldade concentração.
        TRATAMENTO: Psicoterapia, antidepressivo, afastamento.
        PROGNÓSTICO: Melhora esperada em 3-6 meses com tratamento.
        CAPACIDADE: Incapacidade temporária para atividades laborais.
        CLASSIFICAÇÃO: AUXÍLIO-DOENÇA por transtorno mental leve com prognóstico favorável."""
    },

    # APOSENTADORIA POR INVALIDEZ
    {
        "tipo": "APOSENTADORIA POR INVALIDEZ",
        "cid": "E11.4",
        "caso": """Ana Costa, 52 anos, professora.
        DIAGNÓSTICO: Diabetes mellitus com neuropatia diabética severa.
        SINTOMAS: Perda visão, neuropatia, nefropatia, úlceras.
        EVOLUÇÃO: Progressiva há 15 anos, múltiplas complicações.
        PROGNÓSTICO: Degenerativo, incapacidade total irreversível.
        CAPACIDADE: Impossibilidade para qualquer atividade laboral.
        CLASSIFICAÇÃO: APOSENTADORIA POR INVALIDEZ por incapacidade total e permanente."""
    },
    {
        "tipo": "APOSENTADORIA POR INVALIDEZ", 
        "cid": "C78.1",
        "caso": """Roberto Lima, 58 anos, motorista.
        DIAGNÓSTICO: Neoplasia maligna de pulmão com metástases.
        SINTOMAS: Dispneia severa, dor torácica, perda ponderal.
        TRATAMENTO: Quimioterapia paliativa, cuidados paliativos.
        PROGNÓSTICO: Reservado, incapacidade total progressiva.
        CAPACIDADE: Impossibilidade total para trabalho.
        CLASSIFICAÇÃO: APOSENTADORIA POR INVALIDEZ por doença oncológica terminal."""
    },
    {
        "tipo": "APOSENTADORIA POR INVALIDEZ",
        "cid": "F20.0", 
        "caso": """Sandra Alves, 45 anos, auxiliar administrativo.
        DIAGNÓSTICO: Esquizofrenia paranoide com episódios psicóticos.
        SINTOMAS: Delírios, alucinações, desorganização do pensamento.
        EVOLUÇÃO: Múltiplas internações, resistência ao tratamento.
        PROGNÓSTICO: Crônico, deterioração funcional progressiva.
        CAPACIDADE: Incapacidade total e permanente para trabalho.
        CLASSIFICAÇÃO: APOSENTADORIA POR INVALIDEZ por transtorno mental grave."""
    },

    # BPC/LOAS
    {
        "tipo": "BPC/LOAS",
        "cid": "Q90.9",
        "caso": """Pedro Santos, 25 anos, síndrome de Down.
        DIAGNÓSTICO: Síndrome de Down com deficiência intelectual severa.
        LIMITAÇÕES: Dependência para atividades básicas, comunicação limitada.
        SOCIAL: Família de baixa renda, renda per capita R$ 200,00.
        AUTONOMIA: Necessita cuidador para vida independente.
        CAPACIDADE: Incapacidade para vida independente e trabalho.
        CLASSIFICAÇÃO: BPC/LOAS por deficiência com impedimento de longo prazo e vulnerabilidade social."""
    },
    {
        "tipo": "BPC/LOAS",
        "cid": "G80.0",
        "caso": """Julia Ferreira, 12 anos, paralisia cerebral.
        DIAGNÓSTICO: Paralisia cerebral espástica quadriplégica.
        LIMITAÇÕES: Dependência total, cadeira de rodas, gastrostomia.
        SOCIAL: Mãe desempregada, sem renda familiar.
        CUIDADOS: Necessita cuidados integrais 24 horas.
        CAPACIDADE: Incapacidade total para vida independente.
        CLASSIFICAÇÃO: BPC/LOAS por deficiência grave em menor com vulnerabilidade extrema."""
    },
    {
        "tipo": "BPC/LOAS",
        "cid": "Z99.2",
        "caso": """Antônio Silva, 68 anos, aposentado.
        DIAGNÓSTICO: Dependência de diálise renal crônica.
        LIMITAÇÕES: Hemodiálise 3x/semana, fadiga extrema, mobilidade reduzida.
        SOCIAL: Aposentadoria de 1 salário mínimo, gastos altos com tratamento.
        AUTONOMIA: Limitação severa para atividades cotidianas.
        CAPACIDADE: Incapacidade para vida autônoma.
        CLASSIFICAÇÃO: BPC/LOAS por deficiência em idoso com limitação funcional severa."""
    },

    # AUXÍLIO-ACIDENTE
    {
        "tipo": "AUXÍLIO-ACIDENTE",
        "cid": "S68.1",
        "caso": """Marcos Oliveira, 40 anos, operador de máquinas.
        DIAGNÓSTICO: Amputação traumática de 2 dedos em acidente trabalho.
        SEQUELA: Perda funcional permanente da mão direita.
        CAPACIDADE: Redução da capacidade laboral para função específica.
        REABILITAÇÃO: Adaptação para outras funções possível.
        CONSOLIDAÇÃO: Sequela permanente estabelecida.
        CLASSIFICAÇÃO: AUXÍLIO-ACIDENTE por sequela de acidente de trabalho com redução da capacidade."""
    },
    {
        "tipo": "AUXÍLIO-ACIDENTE",
        "cid": "M75.3",
        "caso": """Lucia Santos, 45 anos, faxineira.
        DIAGNÓSTICO: Tendinite crônica ombro por esforço repetitivo.
        NEXO: Doença ocupacional por atividade laboral repetitiva.
        SEQUELA: Limitação permanente para movimentos do braço.
        CAPACIDADE: Redução para atividades que exigem esforço braços.
        CONSOLIDAÇÃO: Sequela com redução da capacidade estabelecida.
        CLASSIFICAÇÃO: AUXÍLIO-ACIDENTE por doença ocupacional com sequela."""
    },

    # ISENÇÃO IMPOSTO DE RENDA
    {
        "tipo": "ISENÇÃO IMPOSTO DE RENDA",
        "cid": "C50.9",
        "caso": """Carmen Costa, 55 anos, servidora pública aposentada.
        DIAGNÓSTICO: Neoplasia maligna de mama com metástases.
        SITUAÇÃO: Aposentada por invalidez após diagnóstico oncológico.
        TRATAMENTO: Quimioterapia, radioterapia, cirurgia radical.
        PROGNÓSTICO: Doença grave com tratamento prolongado.
        DIREITO: Isenção IR por doença grave especificada em lei.
        CLASSIFICAÇÃO: ISENÇÃO IMPOSTO DE RENDA por neoplasia maligna."""
    },
    {
        "tipo": "ISENÇÃO IMPOSTO DE RENDA", 
        "cid": "N18.6",
        "caso": """José Pereira, 62 anos, engenheiro aposentado.
        DIAGNÓSTICO: Insuficiência renal crônica terminal.
        SITUAÇÃO: Aposentado por invalidez, dependente de hemodiálise.
        TRATAMENTO: Hemodiálise 3x por semana, medicação complexa.
        LIMITAÇÕES: Incapacidade total para atividades laborais.
        DIREITO: Isenção IR por doença grave e aposentadoria invalidez.
        CLASSIFICAÇÃO: ISENÇÃO IMPOSTO DE RENDA por doença renal grave."""
    }
]

def adicionar_casos_rag():
    """Adiciona casos específicos de benefícios à base RAG"""
    try:
        from services.multimodal_ai_service import MultimodalAIService
        
        print("🚀 POVOANDO BASE RAG COM CASOS ESPECÍFICOS DE BENEFÍCIOS")
        print("=" * 60)
        
        # Inicializar serviço 
        service = MultimodalAIService()
        rag = service.rag_service
        
        print(f"📊 Base atual: {rag.get_vector_count()} vetores")
        
        # Adicionar cada caso
        for i, caso in enumerate(casos_beneficios, 1):
            print(f"\n📝 Adicionando caso {i}/{len(casos_beneficios)}")
            print(f"   🏷️ Tipo: {caso['tipo']}")
            print(f"   🩺 CID: {caso['cid']}")
            
            try:
                # Criar texto estruturado para indexação
                texto_indexacao = f"""
TIPO DE BENEFÍCIO: {caso['tipo']}
CID: {caso['cid']}
{caso['caso']}
"""
                
                # Adicionar ao índice
                rag.add_document_to_index(
                    texto_indexacao,
                    metadata={
                        'tipo_beneficio': caso['tipo'],
                        'cid': caso['cid'],
                        'case_id': f"benefit_{i:03d}"
                    }
                )
                print(f"   ✅ Caso adicionado com sucesso")
                
            except Exception as e:
                print(f"   ❌ Erro no caso {i}: {e}")
        
        # Salvar índice atualizado
        rag.save_index()
        
        print(f"\n🎉 BASE RAG ATUALIZADA!")
        print(f"   📈 Total de vetores: {rag.get_vector_count()}")
        print(f"   📋 Novos casos: {len(casos_beneficios)}")
        print(f"   🏥 Tipos de benefício: 5")
        
        # Mostrar estatísticas por tipo
        tipos = {}
        for caso in casos_beneficios:
            tipo = caso['tipo']
            tipos[tipo] = tipos.get(tipo, 0) + 1
        
        print(f"\n📊 DISTRIBUIÇÃO POR BENEFÍCIO:")
        for tipo, count in tipos.items():
            print(f"   • {tipo}: {count} casos")
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        
if __name__ == "__main__":
    adicionar_casos_rag() 