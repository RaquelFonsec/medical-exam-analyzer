#!/usr/bin/env python3
"""
Teste de transcrição com áudio em formato correto
"""

import requests
import json
from io import BytesIO

def test_webm_audio():
    """Testa transcrição com dados de áudio WebM simulados"""
    
    url = "http://localhost:5003/api/intelligent-medical-analysis"
    
    # Dados do paciente
    patient_info = "Helena, 45 anos, dentista, dor articulações mãos, dificuldade trabalhar"
    
    # Simular início de arquivo WebM (header básico)
    webm_header = b'\x1a\x45\xdf\xa3'  # EBML header
    fake_webm_data = webm_header + b'\x00' * 200  # Dados simulados
    
    # Preparar requisição
    files = {
        'audio_data': ('consulta_teste.webm', BytesIO(fake_webm_data), 'audio/webm')
    }
    
    data = {
        'patient_info': patient_info
    }
    
    print("🧪 Testando transcrição com formato WebM...")
    print(f"📤 Dados: {patient_info}")
    print(f"🎤 Tamanho áudio: {len(fake_webm_data)} bytes")
    print(f"🔍 Tipo MIME: audio/webm")
    
    try:
        response = requests.post(url, data=data, files=files, timeout=30)
        
        print(f"📨 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Requisição bem-sucedida!")
            print(f"🔍 Success: {result.get('success')}")
            print(f"📝 Transcription: '{result.get('transcription', 'VAZIO')}'")
            
            # Verificar se transcrição está funcionando
            transcription = result.get('transcription', '')
            if transcription and transcription.strip() and 'Erro' not in transcription:
                print("✅ TRANSCRIÇÃO FUNCIONANDO!")
            else:
                print(f"⚠️ Problema na transcrição: '{transcription}'")
                
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"📄 Response: {response.text[:300]}...")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_frontend_access():
    """Testa se o frontend está acessível"""
    
    print("\n🌐 Testando acesso ao frontend...")
    
    try:
        response = requests.get("http://localhost:5003/consultation", timeout=10)
        
        if response.status_code == 200:
            print("✅ Frontend acessível!")
            print(f"📄 Tamanho da página: {len(response.text)} chars")
            
            # Verificar se tem os elementos de áudio
            content = response.text
            if 'mediaRecorder' in content and 'audioChunks' in content:
                print("✅ Código de gravação de áudio presente!")
            else:
                print("⚠️ Código de áudio pode estar ausente")
                
        else:
            print(f"❌ Frontend inacessível: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro ao acessar frontend: {e}")

if __name__ == "__main__":
    print("🚀 Testando sistema de transcrição corrigido...")
    
    # Testar acesso ao frontend
    test_frontend_access()
    
    # Testar transcrição
    test_webm_audio()
    
    print("\n📋 INSTRUÇÕES PARA TESTE MANUAL:")
    print("1. Abra: http://localhost:5003/consultation")
    print("2. Clique no botão de gravar (microfone)")
    print("3. Fale algo por 3-5 segundos")
    print("4. Pare a gravação")
    print("5. Clique em 'Análise Híbrida Inteligente'")
    print("6. Observe o console do navegador (F12) para logs de áudio")
    print("7. Verifique se a transcrição aparece na seção de resultados")
    
    print("\n�� Teste concluído!") 