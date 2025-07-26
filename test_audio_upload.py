#!/usr/bin/env python3
"""
Script de teste para verificar upload e transcrição de áudio
"""

import requests
import sys
import json
from io import BytesIO

def test_audio_upload():
    """Testa o upload de áudio com dados simulados"""
    
    # URL do endpoint
    url = "http://localhost:5003/api/intelligent-medical-analysis"
    
    # Dados do paciente de teste
    patient_info = "Helena, 45 anos, dentista, dor nas articulações das mãos, dificuldade para trabalhar"
    
    # Criar um arquivo de áudio simulado (alguns bytes)
    fake_audio_data = b"RIFF" + b"\x00" * 100  # Simula um arquivo WAV básico
    
    # Preparar dados do formulário
    files = {
        'audio_data': ('test_audio.wav', BytesIO(fake_audio_data), 'audio/wav')
    }
    
    data = {
        'patient_info': patient_info
    }
    
    print("🧪 Testando upload de áudio...")
    print(f"📤 Patient info: {patient_info}")
    print(f"🎤 Audio size: {len(fake_audio_data)} bytes")
    
    try:
        response = requests.post(url, data=data, files=files, timeout=30)
        
        print(f"📨 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Requisição bem-sucedida!")
            print(f"🔍 Success: {result.get('success', 'N/A')}")
            print(f"📝 Transcription: {result.get('transcription', 'N/A')[:100]}...")
            print(f"👤 Patient data: {result.get('patient_data', {})}")
            
            if result.get('transcription'):
                print("✅ Transcrição funcionando!")
            else:
                print("⚠️ Transcrição vazia ou com problemas")
                
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"📄 Response: {response.text[:500]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão: {e}")
    except Exception as e:
        print(f"💥 Erro inesperado: {e}")

def test_rag_stats():
    """Testa se as estatísticas RAG estão funcionando"""
    
    url = "http://localhost:5003/api/rag/stats"
    
    print("\n🧪 Testando estatísticas RAG...")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            print("✅ RAG Stats funcionando!")
            print(f"📊 Stats: {json.dumps(stats, indent=2)}")
            
            # Verificar se tem vetores carregados
            total_vectors = stats.get('statistics', {}).get('total_vectors', 0)
            if total_vectors > 0:
                print(f"✅ RAG com {total_vectors} vetores carregados!")
            else:
                print("⚠️ RAG sem vetores carregados")
                
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando testes do sistema médico...")
    
    # Aguardar servidor estar pronto
    import time
    print("⏳ Aguardando servidor (10s)...")
    time.sleep(10)
    
    # Testar RAG stats primeiro
    test_rag_stats()
    
    # Testar upload de áudio
    test_audio_upload()
    
    print("\n🏁 Testes concluídos!") 