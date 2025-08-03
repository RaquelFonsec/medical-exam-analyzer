from cryptography.fernet import Fernet
import os
import hashlib

class EncryptionService:
    def __init__(self):
        # Carregar chave de criptografia (com fallback)
        encrypt_key_file = os.getenv("ENCRYPTION_KEY_FILE", "keys/encryption.key")
        
        # Caminho absoluto garantido
        current_dir = os.path.dirname(os.path.abspath(__file__))
        key_file = os.path.join(current_dir, encrypt_key_file)
        
        self.encryption_enabled = False
        self.cipher = None
        
        try:
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    self.key = f.read()
                self.cipher = Fernet(self.key)
                self.encryption_enabled = True
                print("✅ Serviço de criptografia ativado")
            else:
                print("⚠️ Criptografia desabilitada (chave não encontrada)")
                print(f"   Procurou em: {key_file}")
        except Exception as e:
            print(f"⚠️ Erro ao inicializar criptografia: {e}")
            print("   Funcionando sem criptografia")
    
    def encrypt_patient_data(self, data: str) -> str:
        """Criptografar dados sensíveis do paciente"""
        if not data:
            return ""
        
        if self.encryption_enabled and self.cipher:
            try:
                return self.cipher.encrypt(data.encode()).decode()
            except Exception as e:
                print(f"⚠️ Erro na criptografia: {e}")
                return data  # Retorna sem criptografar
        
        # Se não tem criptografia, retorna o dado original
        return data
    
    def decrypt_patient_data(self, encrypted_data: str) -> str:
        """Descriptografar dados do paciente"""
        if not encrypted_data:
            return ""
        
        if self.encryption_enabled and self.cipher:
            try:
                return self.cipher.decrypt(encrypted_data.encode()).decode()
            except Exception as e:
                print(f"⚠️ Erro na descriptografia: {e}")
                return encrypted_data  # Retorna como está
        
        # Se não tem criptografia, retorna como está
        return encrypted_data
    
    def hash_patient_id(self, patient_info: str) -> str:
        """Gerar ID único para auditoria (sem expor dados)"""
        return hashlib.sha256(patient_info.encode()).hexdigest()[:16]

# Instância global (com tratamento de erro)
try:
    encryption_service = EncryptionService()
except Exception as e:
    print(f"⚠️ Falha ao inicializar encryption_service: {e}")
    encryption_service = None
