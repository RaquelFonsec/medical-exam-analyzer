from cryptography.fernet import Fernet
import os
import hashlib

class EncryptionService:
    def __init__(self):
        # Carregar chave de criptografia
        key_file = os.getenv("ENCRYPTION_KEY_FILE", "keys/encryption.key")
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
