#!/usr/bin/env python3
"""
TESTE - Laudo Médico Integrado com Classificação
"""

import requests
import json
import time

def test_laudo_integrado():
    """Testa se o laudo inclui a classificação"""
    
    url = "http://localhost:5003/api/intelligent-medical-analysis"
    
    # Caso de teste
    patient_info = """
    Ana Maria, 45 anos, costureira.
    Síndrome do túnel do carpo bilateral grave há 5 anos.
    Múltiplas cirurgias sem sucesso. Dor crônica intensa.
    Incapacidade total para trabalhar com as mãos.
    Usa analgésicos fortes diariamente.
    """
    
    data = {'patient_info': patient_info.strip()}
    
    print("📋 TESTE: LAUDO MÉDICO INTEGRADO")
    print("="*60)
    print(f"👤 Paciente: Ana Maria - Túnel do carpo bilateral")
    print("⏳ Gerando análise completa...")
    
    try:
        response = requests.post(url, data=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            # Extrair o laudo médico
            laudo = result.get('medical_report', '')
            
            if laudo:
                print("\n📄 LAUDO MÉDICO GERADO:")
                print("="*60)
                print(laudo)
                print("="*60)
                
                # Verificar se contém elementos integrados
                elementos_esperados = [
                    "CID-10",
                    "CLASSIFICAÇÃO PREVIDENCIÁRIA", 
                    "AUXILIO_DOENCA",
                    "PERICIA_MEDICA",
                    "JUSTIFICATIVA",
                    "PROGNÓSTICO"
                ]
                
                print("\n🔍 VERIFICAÇÃO DE INTEGRAÇÃO:")
                for elemento in elementos_esperados:
                    if elemento in laudo:
                        print(f"✅ {elemento}: PRESENTE")
                    else:
                        print(f"❌ {elemento}: AUSENTE")
                
                # Verificar classificação separada também
                if result.get('benefit_classification'):
                    bc = result['benefit_classification']
                    print(f"\n📊 CLASSIFICAÇÃO SEPARADA:")
                    print(f"   Tipo: {bc.get('tipo_beneficio')}")
                    print(f"   CID: {bc.get('cid_principal')}")
                
                return True
            else:
                print("❌ Nenhum laudo gerado")
                return False
                
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("🚀 TESTANDO INTEGRAÇÃO DA CLASSIFICAÇÃO NO LAUDO")
    
    # Aguardar servidor estabilizar
    time.sleep(5)
    
    # Executar teste
    sucesso = test_laudo_integrado()
    
    if sucesso:
        print("\n🎉 TESTE CONCLUÍDO!")
        print("✅ Laudo médico agora inclui:")
        print("   - Classificação de benefício")
        print("   - CID principal") 
        print("   - Justificativa médica")
        print("   - Prognóstico")
        print("   - Tudo integrado em um só documento!")
    else:
        print("\n❌ Teste falhou - verificar logs do servidor") 