#!/usr/bin/env python3
"""
EXEMPLO PRÁTICO - Como usar o Sistema de Análise Médica
"""

import requests
import json
import time

def exemplo_auxilio_doenca():
    """Exemplo: Caso que será classificado como Auxílio Doença"""
    
    print("🧪 EXEMPLO 1: AUXÍLIO DOENÇA")
    print("="*50)
    
    # Dados do paciente
    caso = {
        "titulo": "Mecânico com fratura",
        "texto": """
        Roberto Silva, 32 anos, mecânico automotivo.
        
        QUEIXA: Fratura do punho esquerdo em acidente de trabalho há 1 semana.
        
        HISTÓRIA: Queda de veículo durante reparo, trauma direto no punho.
        
        SINTOMAS: Dor intensa (8/10), edema, limitação total de movimento.
        
        EXAME: Deformidade visível, crepitação óssea.
        
        TRATAMENTO: Cirurgia de fixação interna realizada com sucesso.
        
        PROGNÓSTICO: Recuperação esperada em 6-8 semanas com fisioterapia.
        """
    }
    
    return testar_caso(caso, "AUXILIO_DOENCA")

def exemplo_pericia_medica():
    """Exemplo: Caso que será classificado como Perícia Médica"""
    
    print("\n🧪 EXEMPLO 2: PERÍCIA MÉDICA")
    print("="*50)
    
    # Dados do paciente
    caso = {
        "titulo": "Professora com fibromialgia",
        "texto": """
        Sandra Costa, 48 anos, professora de ensino fundamental.
        
        QUEIXA: Fibromialgia severa há 8 anos, progressiva.
        
        HISTÓRIA: Dor generalizada crônica, fadiga extrema, múltiplas consultas.
        
        SINTOMAS: Dor difusa (9/10), rigidez matinal por horas, insônia severa,
        depressão secundária, incapacidade para permanecer em pé por períodos prolongados.
        
        MEDICAÇÕES: Pregabalina 300mg/dia, tramadol, antidepressivos.
        
        EVOLUÇÃO: Piora progressiva, múltiplas licenças médicas.
        
        PROGNÓSTICO: Doença crônica sem cura, incapacidade laboral permanente.
        """
    }
    
    return testar_caso(caso, "PERICIA_MEDICA")

def testar_caso(caso, esperado):
    """Testa um caso específico"""
    
    url = "http://localhost:5003/api/intelligent-medical-analysis"
    
    print(f"📋 Caso: {caso['titulo']}")
    print(f"⏳ Enviando para análise...")
    
    try:
        # Enviar requisição
        data = {'patient_info': caso['texto'].strip()}
        response = requests.post(url, data=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            # Extrair informações principais
            patient_data = result.get('patient_data', {})
            classification = result.get('benefit_classification', {})
            report = result.get('medical_report', '')
            
            # Exibir resultado resumido
            print(f"\n✅ ANÁLISE CONCLUÍDA:")
            print(f"   👤 Paciente: {patient_data.get('nome', 'N/A')}")
            print(f"   📅 Idade: {patient_data.get('idade', 'N/A')}")
            print(f"   💼 Profissão: {patient_data.get('profissao', 'N/A')}")
            
            if classification:
                tipo = classification.get('tipo_beneficio', 'N/A')
                cid = classification.get('cid_principal', 'N/A')
                descricao = classification.get('cid_descricao', 'N/A')
                
                print(f"\n🏥 CLASSIFICAÇÃO:")
                print(f"   📋 Tipo: {tipo}")
                print(f"   🏷️ CID: {cid} - {descricao}")
                print(f"   ⚖️ Gravidade: {classification.get('gravidade', 'N/A')}")
                
                # Verificar se classificação está correta
                if tipo == esperado:
                    print(f"   ✅ CORRETO: Classificado como {esperado}")
                else:
                    print(f"   ⚠️ INESPERADO: Esperado {esperado}, obtido {tipo}")
            
            # Mostrar trecho do laudo
            if report:
                print(f"\n📄 TRECHO DO LAUDO:")
                linhas = report.split('\n')[:10]  # Primeiras 10 linhas
                for linha in linhas:
                    if linha.strip():
                        print(f"   {linha}")
                if len(report.split('\n')) > 10:
                    print("   ...")
                    
            return True
            
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Servidor não está rodando!")
        print("💡 Solução: cd backend/app && python main.py")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def verificar_servidor():
    """Verifica se o servidor está rodando"""
    
    print("🔍 VERIFICANDO SERVIDOR...")
    
    try:
        response = requests.get("http://localhost:5003/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Servidor ONLINE - {data.get('version', 'N/A')}")
            print(f"✅ Services: {len(data.get('services', {}))}")
            return True
        else:
            print(f"❌ Servidor com problema: HTTP {response.status_code}")
            return False
    except:
        print("❌ Servidor OFFLINE")
        print("\n💡 COMO INICIAR:")
        print("1. cd /home/raquel/medical-exam-analyzer")
        print("2. cd backend/app")
        print("3. python main.py")
        return False

def main():
    """Função principal - executa todos os exemplos"""
    
    print("🚀 EXEMPLOS PRÁTICOS - SISTEMA DE ANÁLISE MÉDICA")
    print("="*60)
    print("📌 Este script demonstra como usar o sistema via API")
    print("")
    
    # Verificar se servidor está rodando
    if not verificar_servidor():
        return
    
    print("\n⏳ Aguardando sistema estabilizar...")
    time.sleep(3)
    
    # Executar exemplos
    exemplo1_ok = exemplo_auxilio_doenca()
    exemplo2_ok = exemplo_pericia_medica()
    
    # Resumo final
    print("\n🎯 RESUMO DOS TESTES:")
    print("="*40)
    
    if exemplo1_ok:
        print("✅ Auxílio Doença: FUNCIONANDO")
    else:
        print("❌ Auxílio Doença: ERRO")
        
    if exemplo2_ok:
        print("✅ Perícia Médica: FUNCIONANDO")
    else:
        print("❌ Perícia Médica: ERRO")
    
    if exemplo1_ok and exemplo2_ok:
        print("\n🎉 SISTEMA FUNCIONANDO PERFEITAMENTE!")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Use a interface web: http://localhost:5003/consultation")
        print("2. Teste seus próprios casos médicos")
        print("3. Veja o laudo completo gerado")
    else:
        print("\n⚠️ Alguns testes falharam - verificar configuração")

if __name__ == "__main__":
    main() 