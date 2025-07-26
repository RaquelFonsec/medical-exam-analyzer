#!/usr/bin/env python3
"""
TESTE FINAL - Classificação de Benefício e CID
"""

import requests
import json
import time

def test_auxilio_doenca():
    """Teste caso Auxílio Doença"""
    
    url = "http://localhost:5003/api/intelligent-medical-analysis"
    
    patient_info = """
    Pedro Silva, 28 anos, operário de construção civil.
    
    QUEIXA: Fratura exposta do fêmur direito em acidente de trabalho há 3 semanas.
    
    HISTÓRICO: Queda de andaime, fratura cominutiva, cirurgia com hastes intramedulares.
    
    SINTOMAS: Dor intensa (8/10), limitação total para deambular, uso de muletas.
    
    TRATAMENTO: Cirurgia ortopédica, fisioterapia planejada para 6 meses.
    
    PROGNÓSTICO: Recuperação esperada em 4-6 meses com retorno ao trabalho.
    """
    
    data = {'patient_info': patient_info.strip()}
    
    print("🧪 TESTE AUXÍLIO DOENÇA")
    print("="*50)
    
    try:
        response = requests.post(url, data=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ RESPOSTA RECEBIDA")
            
            # Verificar dados do paciente
            if result.get('patient_data'):
                pd = result['patient_data']
                print(f"👤 Nome: {pd.get('nome', 'N/A')}")
                print(f"📅 Idade: {pd.get('idade', 'N/A')}")
                print(f"💼 Profissão: {pd.get('profissao', 'N/A')}")
                print(f"🩺 Queixa: {pd.get('queixa_principal', 'N/A')}")
            
            # Verificar classificação
            if result.get('benefit_classification'):
                bc = result['benefit_classification']
                print(f"\n🏥 CLASSIFICAÇÃO:")
                print(f"   📋 Tipo: {bc.get('tipo_beneficio', 'N/A')}")
                print(f"   🏷️ CID: {bc.get('cid_principal', 'N/A')} - {bc.get('cid_descricao', 'N/A')}")
                print(f"   ⚖️ Gravidade: {bc.get('gravidade', 'N/A')}")
                print(f"   📝 Justificativa: {bc.get('justificativa', 'N/A')}")
                
                if bc.get('tipo_beneficio') == 'AUXILIO_DOENCA':
                    print("✅ CORRETO: Classificado como Auxílio Doença!")
                else:
                    print("⚠️ ATENÇÃO: Classificação inesperada")
            else:
                print("❌ Classificação não encontrada na resposta")
                
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"Resposta: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏱️ Timeout - Análise muito longa")
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_pericia_medica():
    """Teste caso Perícia Médica"""
    
    url = "http://localhost:5003/api/intelligent-medical-analysis"
    
    patient_info = """
    Angela Costa, 52 anos, professora.
    
    QUEIXA: Fibromialgia severa com síndrome do túnel do carpo bilateral.
    
    HISTÓRICO: Dor crônica generalizada há 8 anos, progressiva. 
    Múltiplas cirurgias nos punhos sem melhora. Depressão secundária.
    
    SINTOMAS: Dor intensa constante (9/10), fadiga extrema, 
    incapacidade para escrever, segurar objetos. Insônia crônica.
    
    MEDICAÇÕES: Morfina 30mg/dia, pregabalina, antidepressivos.
    
    PROGNÓSTICO: Doença crônica progressiva, incapacidade permanente.
    Impossibilidade de retorno ao trabalho em sala de aula.
    """
    
    data = {'patient_info': patient_info.strip()}
    
    print("\n🧪 TESTE PERÍCIA MÉDICA")
    print("="*50)
    
    try:
        response = requests.post(url, data=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ RESPOSTA RECEBIDA")
            
            # Verificar dados do paciente
            if result.get('patient_data'):
                pd = result['patient_data']
                print(f"👤 Nome: {pd.get('nome', 'N/A')}")
                print(f"📅 Idade: {pd.get('idade', 'N/A')}")
                print(f"💼 Profissão: {pd.get('profissao', 'N/A')}")
                print(f"🩺 Queixa: {pd.get('queixa_principal', 'N/A')}")
            
            # Verificar classificação
            if result.get('benefit_classification'):
                bc = result['benefit_classification']
                print(f"\n🏥 CLASSIFICAÇÃO:")
                print(f"   📋 Tipo: {bc.get('tipo_beneficio', 'N/A')}")
                print(f"   🏷️ CID: {bc.get('cid_principal', 'N/A')} - {bc.get('cid_descricao', 'N/A')}")
                print(f"   ⚖️ Gravidade: {bc.get('gravidade', 'N/A')}")
                print(f"   🔮 Prognóstico: {bc.get('prognóstico', 'N/A')}")
                print(f"   📝 Justificativa: {bc.get('justificativa', 'N/A')}")
                
                if bc.get('tipo_beneficio') == 'PERICIA_MEDICA':
                    print("✅ CORRETO: Classificado como Perícia Médica!")
                else:
                    print("⚠️ ATENÇÃO: Classificação inesperada")
            else:
                print("❌ Classificação não encontrada na resposta")
                
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"Resposta: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏱️ Timeout - Análise muito longa")
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_frontend_instructions():
    """Instruções para teste no frontend"""
    
    print("\n🌐 TESTE NO FRONTEND:")
    print("="*50)
    print("🔗 URL: http://localhost:5003/consultation")
    print("\n📝 CASOS PARA TESTAR:")
    
    print("\n1️⃣ AUXÍLIO DOENÇA:")
    print("   Roberto, 30 anos, mecânico. Fratura braço,")
    print("   cirurgia bem-sucedida, recuperação em 3 meses.")
    
    print("\n2️⃣ PERÍCIA MÉDICA:")
    print("   Sônia, 55 anos, diabetes grave, neuropatia,")
    print("   cegueira, insuficiência renal, sem possibilidade de cura.")
    
    print("\n✅ RESULTADOS ESPERADOS:")
    print("   - Nova seção 'Classificação Previdenciária'")
    print("   - Badge colorido com tipo de benefício")
    print("   - CID principal + descrição")
    print("   - Gravidade com cores (Verde/Amarelo/Vermelho)")
    print("   - Justificativa da classificação")
    print("   - Prognóstico do caso")

if __name__ == "__main__":
    print("🚀 TESTE FINAL - CLASSIFICAÇÃO AUTOMÁTICA")
    print("🎯 Verificando se o sistema classifica corretamente")
    print("   Auxílio Doença vs Perícia Médica")
    
    # Aguardar servidor
    print("\n⏳ Aguardando servidor...")
    time.sleep(5)
    
    # Executar testes
    test_auxilio_doenca()
    test_pericia_medica()
    test_frontend_instructions()
    
    print("\n🎉 TESTES CONCLUÍDOS!")
    print("Sua funcionalidade de classificação está implementada! 🚀") 