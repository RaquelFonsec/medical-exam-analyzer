from cryptography.fernet import Fernet
import os
import hashlib


class EncryptionService:
    def __init__(self):
        # Carregar chave de criptografia
        encrypt_key_file = os.getenv("ENCRYPTION_KEY_FILE", "keys/encryption.key")
        # Caminho absoluto garantido
        current_dir = os.path.dirname(os.path.abspath(__file__))  # Pega o diretório do arquivo atual
        key_file = os.path.join(current_dir, encrypt_key_file)  # Monta o caminho correto
        
        print(f"Procurando chave em: {key_file}")  # Debug
        
        if not os.path.exists(key_file):
            print("Arquivo de chave não encontrado. Verifique o caminho.")
            raise FileNotFoundError(f"Arquivo de chave não encontrado em: {key_file}")
        
        with open(key_file, 'rb') as f:
            self.key = f.read()
        self.cipher = Fernet(self.key)
        print("✅ Serviço de criptografia inicializado")
    
    def encrypt_patient_data(self, data: str) -> str:
        """Criptografar dados sensíveis do paciente"""
        if not data:
            return ""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_patient_data(self, encrypted_data: str) -> str:
        """Descriptografar dados do paciente"""
        if not encrypted_data:
            return ""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def hash_patient_id(self, patient_info: str) -> str:
        """Gerar ID único para auditoria (sem expor dados)"""
        return hashlib.sha256(patient_info.encode()).hexdigest()[:16]

# Instância global
encryption_service = EncryptionService()
