# # gerar_chave.py
# from cryptography.fernet import Fernet
# import os
# 
# base_dir = os.path.dirname(os.path.abspath(__file__))
# key_path = os.path.join(base_dir, "services", "keys", "encryption.key")
# 
# os.makedirs(os.path.dirname(key_path), exist_ok=True)
# 
# key = Fernet.generate_key()
# 
# with open(key_path, 'wb') as f:
#     f.write(key)
# 
# print(f"🔐 Chave gerada com sucesso em: {key_path}")
