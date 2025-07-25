#!/usr/bin/env python3
# ============================================================================
# ATIVAR OPENAI NO SISTEMA RAG
# ============================================================================

import os
import sys
from dotenv import load_dotenv

# Adicionar caminho do projeto
sys.path.append('/home/raquel/medical-exam-analyzer/backend')

def check_env_variables():
    """Verificar variáveis de ambiente"""
    
    print("🔍 Verificando variáveis de ambiente...")
    
    # Carregar .env explicitamente
    env_path = '/home/raquel/medical-exam-analyzer/backend/.env'
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"✅ Arquivo .env carregado: {env_path}")
    else:
        print(f"❌ Arquivo .env não encontrado: {env_path}")
        return False
    
    # Verificar OPENAI_API_KEY
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        # Mostrar apenas os primeiros e últimos caracteres por segurança
        masked_key = f"{openai_key[:8]}...{openai_key[-8:]}"
        print(f"✅ OPENAI_API_KEY encontrada: {masked_key}")
        return True
    else:
        print("❌ OPENAI_API_KEY não encontrada")
        return False

def test_openai_connection():
    """Testar conexão com OpenAI"""
    
    print("\n🧪 Testando conexão OpenAI...")
    
    try:
        import openai
        
        # Carregar chave
        load_dotenv('/home/raquel/medical-exam-analyzer/backend/.env')
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            print("❌ Chave OpenAI não encontrada")
            return False
        
        # Criar cliente
        client = openai.OpenAI(api_key=api_key)
        
        # Teste simples
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Responda apenas 'OK' se você consegue me ouvir"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ OpenAI respondeu: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar OpenAI: {e}")
        return False

def update_main_app():
    """Atualizar app principal para carregar .env"""
    
    print("\n🔧 Atualizando app principal...")
    
    main_app_path = '/home/raquel/medical-exam-analyzer/backend/app/main.py'
    
    try:
        with open(main_app_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar se já tem load_dotenv
        if 'from dotenv import load_dotenv' not in content:
            print("📝 Adicionando load_dotenv ao main.py...")
            
            # Adicionar imports no topo
            lines = content.split('\n')
            import_added = False
            
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    if not import_added:
                        lines.insert(i, 'from dotenv import load_dotenv')
                        import_added = True
                        break
            
            # Adicionar load_dotenv antes da criação do app
            for i, line in enumerate(lines):
                if 'app = FastAPI' in line:
                    lines.insert(i, '# Carregar variáveis de ambiente')
                    lines.insert(i+1, 'load_dotenv()')
                    lines.insert(i+2, '')
                    break
            
            # Salvar arquivo atualizado
            with open(main_app_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            print("✅ main.py atualizado para carregar .env")
        else:
            print("✅ main.py já carrega .env")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao atualizar main.py: {e}")
        return False

def test_rag_with_openai():
    """Testar sistema RAG com OpenAI"""
    
    print("\n🎯 Testando RAG com OpenAI...")
    
    try:
        # Carregar .env
        load_dotenv('/home/raquel/medical-exam-analyzer/backend/.env')
        
        # Importar serviço RAG
        from app.services.rag.medical_rag_service import medical_rag_service
        
        # Testar geração com OpenAI
        patient_info = "helena 45"
        transcription = "Sou Helena, tenho 45 anos, trabalho como pedreira há 20 anos. Machuquei a coluna carregando peso na obra e não consigo mais trabalhar."
        
        print("🔄 Gerando laudo com OpenAI...")
        rag_response = medical_rag_service.generate_rag_response(patient_info, transcription)
        
        if rag_response.get('success'):
            response_text = rag_response.get('response', '')
            print("✅ Laudo gerado com OpenAI!")
            print(f"   Casos encontrados: {rag_response.get('similar_cases_count', 0)}")
            print(f"   Score: {rag_response.get('top_similarity_score', 0):.3f}")
            print(f"   Tamanho: {len(response_text)} chars")
            print(f"   Preview: {response_text[:200]}...")
            
            # Verificar se realmente usou OpenAI (resposta mais elaborada)
            if len(response_text) > 800 and 'IDENTIFICAÇÃO' in response_text:
                print("🎉 OpenAI está funcionando perfeitamente!")
                return True
            else:
                print("⚠️ Pode estar usando template em vez de OpenAI")
                return False
        else:
            print(f"❌ Erro na geração: {rag_response.get('error', 'Desconhecido')}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste RAG: {e}")
        return False

def install_dotenv():
    """Instalar python-dotenv se necessário"""
    
    try:
        import dotenv
        print("✅ python-dotenv já instalado")
        return True
    except ImportError:
        print("📦 Instalando python-dotenv...")
        import subprocess
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', 'python-dotenv'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ python-dotenv instalado")
            return True
        else:
            print(f"❌ Erro ao instalar python-dotenv: {result.stderr}")
            return False

def main():
    """Função principal para ativar OpenAI"""
    
    print("🚀 ATIVANDO OPENAI NO SISTEMA RAG")
    print("="*50)
    
    try:
        # 1. Instalar dependências
        print("1️⃣ Verificando dependências...")
        if not install_dotenv():
            return
        
        # 2. Verificar variáveis de ambiente
        print("\n2️⃣ Verificando configuração...")
        if not check_env_variables():
            return
        
        # 3. Testar conexão OpenAI
        print("\n3️⃣ Testando OpenAI...")
        if not test_openai_connection():
            return
        
        # 4. Atualizar app principal
        print("\n4️⃣ Atualizando aplicação...")
        if not update_main_app():
            return
        
        # 5. Testar RAG com OpenAI
        print("\n5️⃣ Testando integração...")
        if test_rag_with_openai():
            print("\n🎉 OPENAI ATIVADO COM SUCESSO!")
            
            print("\n📋 PRÓXIMOS PASSOS:")
            print("1. Reiniciar servidor:")
            print("   uvicorn app.main:app --host 0.0.0.0 --port 5003 --reload")
            
            print("\n2. Testar endpoint (deve usar OpenAI agora):")
            print("   curl -X POST 'http://localhost:5003/api/intelligent-medical-analysis' \\")
            print("        -F 'patient_info=helena 45' \\")
            print("        -F 'transcription=machuquei a coluna carregando peso'")
            
            print("\n✅ Sistema agora vai gerar laudos mais inteligentes com OpenAI!")
        else:
            print("\n❌ Problema na integração OpenAI")
        
    except Exception as e:
        print(f"\n❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
