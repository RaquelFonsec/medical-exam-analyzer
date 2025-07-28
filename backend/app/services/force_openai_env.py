"""
Script para garantir que a API key do OpenAI esteja disponível
"""

import os
from dotenv import load_dotenv

def setup_openai_env():
    """Configura a variável de ambiente OPENAI_API_KEY"""
    
    # Carregar do .env
    load_dotenv()
    
    # Se não estiver definida, tentar ler do arquivo .env diretamente
    if not os.getenv('OPENAI_API_KEY'):
        try:
            env_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
            if os.path.exists(env_file_path):
                with open(env_file_path, 'r') as f:
                    for line in f:
                        if line.startswith('OPENAI_API_KEY='):
                            key = line.split('=', 1)[1].strip().strip('"').strip("'")
                            os.environ['OPENAI_API_KEY'] = key
                            print(f"✅ OPENAI_API_KEY configurada do arquivo .env")
                            return key
            
            # Tentar do diretório app
            app_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
            if os.path.exists(app_env_path):
                with open(app_env_path, 'r') as f:
                    for line in f:
                        if line.startswith('OPENAI_API_KEY='):
                            key = line.split('=', 1)[1].strip().strip('"').strip("'")
                            os.environ['OPENAI_API_KEY'] = key
                            print(f"✅ OPENAI_API_KEY configurada do app/.env")
                            return key
                            
        except Exception as e:
            print(f"❌ Erro ao ler .env: {e}")
    
    current_key = os.getenv('OPENAI_API_KEY')
    if current_key:
        print(f"✅ OPENAI_API_KEY já configurada: {current_key[:20]}...")
        return current_key
    else:
        print("❌ OPENAI_API_KEY não encontrada")
        return None

if __name__ == "__main__":
    setup_openai_env() 