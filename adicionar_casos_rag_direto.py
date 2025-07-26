#!/usr/bin/env python3
"""
Script para adicionar casos de benefícios à base RAG usando a API do sistema
"""

import requests
import json
import time

BASE_URL = "http://localhost:5003"

# Casos específicos para cada benefício (simulando consultas reais)
casos_para_rag = [
    {
        "tipo": "AUXÍLIO-DOENÇA",
        "caso": """João Silva, 28 anos, pedreiro. Fratura do braço direito em queda no trabalho. 
        Dor intensa, fez cirurgia com placa. Fisioterapia por 3 meses. 
        Médico disse que vai ficar 100% bom. Volta ao trabalho em março."""
    },
    {
        "tipo": "AUXÍLIO-DOENÇA", 
        "caso": """Maria Santos, 32 anos, cozinheira. Pneumonia bilateral grave. 
        Internada 10 dias, agora em casa tomando antibiótico. 
        Tosse, cansaço, mas melhorando. Retorna trabalho em 6 semanas."""
    },
    {
        "tipo": "APOSENTADORIA POR INVALIDEZ",
        "caso": """Pedro Costa, 55 anos, motorista. Diabetes há 15 anos, agora com cegueira.
        Perdeu visão dos dois olhos, não consegue mais dirigir. 
        Médico disse que é irreversível. Nunca mais vai poder trabalhar."""
    },
    {
        "tipo": "APOSENTADORIA POR INVALIDEZ",
        "caso": """Ana Oliveira, 48 anos, professora. Esquizofrenia com surtos frequentes.
        Múltiplas internações psiquiátricas. Não consegue mais dar aula.
        Doença crônica sem cura, incapacidade total para trabalho."""
    },
    {
        "tipo": "BPC/LOAS",
        "caso": """Carlos Mendes, 8 anos, paralisia cerebral. Não anda, não fala.
        Família muito pobre, mãe desempregada. Renda R$ 200 por mês.
        Precisa cuidados 24 horas. Deficiência grave permanente."""
    },
    {
        "tipo": "BPC/LOAS",
        "caso": """Sebastiana Silva, 72 anos, viúva. Demência severa, não reconhece família.
        Filha cuidadora, renda familiar R$ 300. Perdeu autonomia total.
        Precisa ajuda para comer, tomar banho, tudo."""
    },
    {
        "tipo": "AUXÍLIO-ACIDENTE",
        "caso": """Roberto Santos, 40 anos, operário. Acidente máquina, perdeu 2 dedos.
        CAT emitida pela empresa. Sequela permanente na mão direita.
        Pode trabalhar em outras funções com adaptação."""
    },
    {
        "tipo": "AUXÍLIO-ACIDENTE",
        "caso": """Lucia Ferreira, 35 anos, faxineira. LER por esforço repetitivo.
        Tendinite crônica no braço direito. Doença do trabalho.
        Limitação permanente para atividades de limpeza."""
    },
    {
        "tipo": "ISENÇÃO IMPOSTO DE RENDA",
        "caso": """Carmen Costa, 60 anos, aposentada por invalidez. Câncer de mama.
        Fez quimioterapia, cirurgia. Aposentadoria do INSS.
        Doença grave na lista da Receita Federal."""
    },
    {
        "tipo": "ISENÇÃO IMPOSTO DE RENDA",
        "caso": """José Pereira, 58 anos, aposentado invalidez. Insuficiência renal crônica.
        Hemodiálise 3x por semana. Aposentadoria por doença renal.
        Direito à isenção por doença grave."""
    }
]

def adicionar_casos_via_api():
    """Adiciona casos à base RAG via API"""
    print("🚀 ADICIONANDO CASOS À BASE RAG VIA API")
    print("=" * 50)
    
    # Verificar se servidor está funcionando
    try:
        health = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if health.status_code != 200:
            print("❌ Servidor não está funcionando!")
            return
    except:
        print("❌ Servidor não acessível!")
        return
    
    print("✅ Servidor funcionando")
    
    casos_adicionados = 0
    for i, caso in enumerate(casos_para_rag, 1):
        print(f"\n📝 Processando caso {i}/{len(casos_para_rag)}: {caso['tipo']}")
        
        try:
            # Enviar caso para análise (isso adiciona automaticamente ao RAG)
            response = requests.post(
                f"{BASE_URL}/api/intelligent-medical-analysis",
                data={"patient_info": caso['caso']},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                classificacao = result.get('benefit_classification', {})
                beneficio = classificacao.get('tipo_beneficio', 'N/A')
                
                print(f"   ✅ Processado - Classificação: {beneficio}")
                casos_adicionados += 1
            else:
                print(f"   ❌ Erro HTTP: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        
        # Pausa entre casos
        time.sleep(2)
    
    print(f"\n🎉 CASES PROCESSADOS!")
    print(f"   📈 Total processados: {casos_adicionados}/{len(casos_para_rag)}")
    print(f"   📊 Base RAG expandida com casos reais")
    
    # Verificar estatísticas RAG
    try:
        stats = requests.get(f"{BASE_URL}/api/rag/stats", timeout=5)
        if stats.status_code == 200:
            rag_stats = stats.json()
            print(f"\n📊 ESTATÍSTICAS RAG ATUALIZADAS:")
            print(f"   🔢 Vetores: {rag_stats['statistics']['vector_count']}")
            print(f"   📄 Documentos: {rag_stats['statistics']['documents_loaded']}")
    except:
        print("   ⚠️ Não foi possível obter estatísticas RAG")

if __name__ == "__main__":
    adicionar_casos_via_api() 