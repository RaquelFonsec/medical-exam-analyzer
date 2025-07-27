#!/usr/bin/env python3
"""
Script para ativar OpenAI API key no ambiente
"""
import os
import sys

def activate_openai():
    """Ativa API key do OpenAI"""
    
    # Verificar se já está configurada
    if os.getenv("OPENAI_API_KEY"):
        print("✅ OPENAI_API_KEY já configurada")
        return True
    
    # Procurar por arquivo .env
    env_files = [".env", "../.env", "../../.env", ".env.local"]
    
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"📋 Carregando {env_file}")
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith("OPENAI_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        os.environ["OPENAI_API_KEY"] = key
                        print("✅ API key carregada do arquivo .env")
                        return True
    
    # Procurar em variáveis conhecidas
    possible_vars = ["OPENAI_KEY", "OPENAI", "API_KEY"]
    for var in possible_vars:
        if os.getenv(var):
            os.environ["OPENAI_API_KEY"] = os.getenv(var)
            print(f"✅ API key carregada de {var}")
            return True
    
    print("❌ API key não encontrada")
    print("🔧 Configure manualmente:")
    print("export OPENAI_API_KEY=your_key_here")
    return False

if __name__ == "__main__":
    activate_openai() 