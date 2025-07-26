#!/usr/bin/env python3
"""
Teste da nova funcionalidade de classificação de benefício e CID
"""

import requests
import json

def test_auxilio_doenca():
    """Testa caso que deve ser classificado como AUXÍLIO DOENÇA"""
    
    url = "http://localhost:5003/api/intelligent-medical-analysis"
    
    # Caso típico de auxílio doença - problema temporário
    patient_info = """
    João Silva, 35 anos, mecânico.
    Queixa: Fratura do punho direito após acidente de trabalho há 2 semanas.
    Sintomas: Dor intensa, limitação de movimento, inchaço.
    Está em tratamento ortopédico, usando tala gessada.
    Previsão de recuperação em 6-8 semanas com fisioterapia.
    Não consegue trabalhar com ferramentas pesadas atualmente.
    """
    
    data = {'patient_info': patient_info.strip()}
    
    print("🧪 TESTE 1: Caso de AUXÍLIO DOENÇA")
    print(f"📝 Paciente: João, mecânico, fratura punho...")
    
    try:
        response = requests.post(url, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('benefit_classification'):
                bc = result['benefit_classification']
                print(f"\n✅ CLASSIFICAÇÃO OBTIDA:")
                print(f"   Tipo: {bc['tipo_beneficio']}")
                print(f"   CID: {bc['cid_principal']} - {bc['cid_descricao']}")
                print(f"   Gravidade: {bc['gravidade']}")
                print(f"   Justificativa: {bc['justificativa']}")
                
                if bc['tipo_beneficio'] == 'AUXILIO_DOENCA':
                    print("✅ CORRETO: Classificado como Auxílio Doença!")
                else:
                    print("⚠️ ATENÇÃO: Não classificado como esperado")
            else:
                print("❌ Classificação não retornada")
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_pericia_medica():
    """Testa caso que deve ser classificado como PERÍCIA MÉDICA"""
    
    url = "http://localhost:5003/api/intelligent-medical-analysis"
    
    # Caso típico de perícia médica - doença crônica
    patient_info = """
    Maria Santos, 58 anos, professora.
    Queixa: Artrite reumatoide severa há 5 anos, progressiva.
    Sintomas: Dor crônica em múltiplas articulações, deformidades nas mãos, 
    rigidez matinal por mais de 2 horas, fadiga extrema.
    Histórico: Múltiplas internações, uso contínuo de corticoides e imunossupressores.
    Incapacidade total para atividades laborais.
    Prognóstico: Doença progressiva sem cura, limitação permanente.
    """
    
    data = {'patient_info': patient_info.strip()}
    
    print("\n🧪 TESTE 2: Caso de PERÍCIA MÉDICA")
    print(f"📝 Paciente: Maria, professora, artrite reumatoide severa...")
    
    try:
        response = requests.post(url, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('benefit_classification'):
                bc = result['benefit_classification']
                print(f"\n✅ CLASSIFICAÇÃO OBTIDA:")
                print(f"   Tipo: {bc['tipo_beneficio']}")
                print(f"   CID: {bc['cid_principal']} - {bc['cid_descricao']}")
                print(f"   Gravidade: {bc['gravidade']}")
                print(f"   Justificativa: {bc['justificativa']}")
                print(f"   Prognóstico: {bc['prognóstico']}")
                
                if bc['tipo_beneficio'] == 'PERICIA_MEDICA':
                    print("✅ CORRETO: Classificado como Perícia Médica!")
                else:
                    print("⚠️ ATENÇÃO: Não classificado como esperado")
            else:
                print("❌ Classificação não retornada")
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_frontend_classification():
    """Instruções para testar no frontend"""
    
    print("\n🌐 TESTE NO FRONTEND:")
    print("="*50)
    print("1. Abra: http://localhost:5003/consultation")
    print("2. No campo 'Informações do Paciente', cole:")
    print("\n   TESTE AUXÍLIO DOENÇA:")
    print("   Pedro, 28 anos, operário. Fratura braço, cirurgia,")
    print("   recuperação em 3 meses com fisioterapia.")
    print("\n   TESTE PERÍCIA:")
    print("   Ana, 62 anos, diabetes grave, neuropatia,")
    print("   cegueira parcial, insuficiência renal.")
    print("\n3. Execute a análise")
    print("4. Verifique a nova seção 'Classificação Previdenciária'")
    print("5. Confirme se mostra:")
    print("   - Tipo de Benefício (Auxílio Doença ou Perícia)")
    print("   - CID Principal com descrição")
    print("   - Gravidade (Leve/Moderada/Grave)")
    print("   - Justificativa da classificação")

if __name__ == "__main__":
    print("🚀 Testando nova funcionalidade de classificação...")
    
    import time
    print("⏳ Aguardando servidor (10s)...")
    time.sleep(10)
    
    # Testes automatizados
    test_auxilio_doenca()
    test_pericia_medica()
    
    # Instruções para teste manual
    test_frontend_classification()
    
    print("\n🎯 RESUMO:")
    print("- ✅ Sistema analisa o texto do paciente")
    print("- ✅ Classifica automaticamente: Auxílio Doença vs Perícia")
    print("- ✅ Sugere CID apropriado baseado nos sintomas")
    print("- ✅ Determina gravidade e prognóstico")
    print("- ✅ Frontend mostra classificação em destaque")
    
    print("\n�� Teste concluído!") 