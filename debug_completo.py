#!/usr/bin/env python3
"""
DEBUG COMPLETO - Identificar exatamente onde está o problema
"""

import requests
import json
import time

def test_servidor_status():
    """Teste 1: Status do servidor"""
    print("🔍 TESTE 1: STATUS DO SERVIDOR")
    print("="*50)
    
    try:
        response = requests.get("http://localhost:5003/api/health", timeout=10)
        if response.status_code == 200:
            print("✅ Servidor ONLINE")
            data = response.json()
            print(f"✅ Services: {len(data.get('services', {}))}")
            return True
        else:
            print(f"❌ Servidor erro: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Servidor OFFLINE: {e}")
        return False

def test_api_completa():
    """Teste 2: API completa com todos os dados"""
    print("\n🧪 TESTE 2: API COMPLETA")
    print("="*50)
    
    url = "http://localhost:5003/api/intelligent-medical-analysis"
    
    # Caso bem específico
    patient_info = """
    PACIENTE: José Silva, 35 anos, mecânico
    
    QUEIXA PRINCIPAL: Fratura do punho direito
    
    HISTÓRIA: Acidente de trabalho há 2 semanas, queda de altura.
    
    SINTOMAS: Dor intensa, inchaço, limitação de movimento
    
    EXAME FÍSICO: Deformidade óssea visível, crepitação
    
    TRATAMENTO: Cirurgia com fixação interna realizada
    
    PROGNÓSTICO: Recuperação esperada em 8-12 semanas
    """
    
    data = {'patient_info': patient_info.strip()}
    
    try:
        print("📤 Enviando requisição...")
        response = requests.post(url, data=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ RESPOSTA RECEBIDA")
            print(f"📊 Chaves na resposta: {list(result.keys())}")
            
            # Verificar cada componente
            if 'patient_data' in result:
                print("✅ patient_data: PRESENTE")
                pd = result['patient_data']
                print(f"   Nome: {pd.get('nome', 'FALTANDO')}")
                print(f"   Idade: {pd.get('idade', 'FALTANDO')}")
                print(f"   Profissão: {pd.get('profissao', 'FALTANDO')}")
            else:
                print("❌ patient_data: AUSENTE")
                
            if 'benefit_classification' in result:
                print("✅ benefit_classification: PRESENTE")
                bc = result['benefit_classification']
                print(f"   Tipo: {bc.get('tipo_beneficio', 'FALTANDO')}")
                print(f"   CID: {bc.get('cid_principal', 'FALTANDO')}")
                print(f"   Gravidade: {bc.get('gravidade', 'FALTANDO')}")
                print(f"   Justificativa: {bc.get('justificativa', 'FALTANDO')[:50]}...")
            else:
                print("❌ benefit_classification: AUSENTE")
                
            if 'medical_report' in result:
                print("✅ medical_report: PRESENTE")
                report = result.get('medical_report', '')
                print(f"   Tamanho: {len(report)} caracteres")
            else:
                print("❌ medical_report: AUSENTE")
                
            return True
            
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"Resposta: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("⏱️ TIMEOUT - Servidor muito lento")
        return False
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        return False

def test_frontend_acesso():
    """Teste 3: Acesso ao frontend"""
    print("\n🌐 TESTE 3: FRONTEND")
    print("="*50)
    
    try:
        response = requests.get("http://localhost:5003/consultation", timeout=10)
        if response.status_code == 200:
            html = response.text
            
            # Verificar elementos essenciais
            if "Classificação Previdenciária" in html:
                print("✅ Seção de classificação: PRESENTE")
            else:
                print("❌ Seção de classificação: AUSENTE")
                
            if "benefit_classification" in html:
                print("✅ JavaScript para classificação: PRESENTE")
            else:
                print("❌ JavaScript para classificação: AUSENTE")
                
            if "analisarHibridaInteligente" in html:
                print("✅ Função de análise: PRESENTE")
            else:
                print("❌ Função de análise: AUSENTE")
                
            return True
        else:
            print(f"❌ Frontend erro: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend inacessível: {e}")
        return False

def test_caso_real():
    """Teste 4: Caso real como usuário faria"""
    print("\n👤 TESTE 4: SIMULAÇÃO USUÁRIO REAL")
    print("="*50)
    
    casos = [
        {
            "nome": "Auxílio Doença",
            "texto": "Carlos, 40 anos, soldador. Fratura na perna, cirurgia, recuperação 3 meses.",
            "esperado": "AUXILIO_DOENCA"
        },
        {
            "nome": "Perícia Médica", 
            "texto": "Ana, 60 anos, diabetes grave, cegueira, insuficiência renal, sem cura.",
            "esperado": "PERICIA_MEDICA"
        }
    ]
    
    url = "http://localhost:5003/api/intelligent-medical-analysis"
    
    for caso in casos:
        print(f"\n📋 Testando: {caso['nome']}")
        data = {'patient_info': caso['texto']}
        
        try:
            response = requests.post(url, data=data, timeout=45)
            
            if response.status_code == 200:
                result = response.json()
                
                if 'benefit_classification' in result:
                    bc = result['benefit_classification']
                    tipo = bc.get('tipo_beneficio', 'ERRO')
                    
                    if tipo == caso['esperado']:
                        print(f"✅ {caso['nome']}: CORRETO ({tipo})")
                    else:
                        print(f"⚠️ {caso['nome']}: INCORRETO (esperado {caso['esperado']}, obtido {tipo})")
                else:
                    print(f"❌ {caso['nome']}: SEM CLASSIFICAÇÃO")
            else:
                print(f"❌ {caso['nome']}: ERRO HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {caso['nome']}: ERRO {e}")

def diagnostico_completo():
    """Diagnóstico completo do sistema"""
    print("🚨 DIAGNÓSTICO COMPLETO DO SISTEMA")
    print("="*60)
    
    # Aguardar servidor
    print("⏳ Aguardando servidor estabilizar...")
    time.sleep(10)
    
    # Executar todos os testes
    servidor_ok = test_servidor_status()
    
    if servidor_ok:
        api_ok = test_api_completa()
        frontend_ok = test_frontend_acesso()
        
        if api_ok and frontend_ok:
            test_caso_real()
        
    print("\n🎯 RESUMO DO DIAGNÓSTICO:")
    print("="*40)
    
    if servidor_ok:
        print("✅ Servidor: FUNCIONANDO")
    else:
        print("❌ Servidor: PROBLEMA")
        print("   💡 Solução: cd backend/app && python main.py")
        
    print("\n📋 INSTRUÇÕES DE TESTE MANUAL:")
    print("1. Abra: http://localhost:5003/consultation")
    print("2. Cole: 'Pedro, 30 anos, fratura braço, recuperação 2 meses'")
    print("3. Clique 'Análise Híbrida Inteligente'")
    print("4. Verifique se aparece seção 'Classificação Previdenciária'")
    
if __name__ == "__main__":
    diagnostico_completo() 