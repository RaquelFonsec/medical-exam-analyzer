import jwt
import bcrypt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict

class AuthService:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET")
        self.algorithm = "HS256"
        print("✅ Serviço de autenticação inicializado")
    
    def create_doctor_account(self, crm: str, name: str, password: str) -> bool:
        """Criar conta de médico (demo)"""
        # TODO: Salvar no banco de dados
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        print(f"👨‍⚕️ Conta criada para Dr. {name} (CRM: {crm})")
        return True
    
    def authenticate_doctor(self, crm: str, password: str) -> Optional[Dict]:
        """Autenticar médico"""
        # Demo: aceitar CRM 12345 com senha "senha123"
        if crm == "12345" and password == "senha123":
            return {
                "crm": crm,
                "name": "Dr. João Silva",
                "specialty": "Clínica Geral"
            }
        return None
    
    def generate_token(self, doctor_data: Dict) -> str:
        """Gerar token JWT"""
        payload = {
            "crm": doctor_data["crm"],
            "name": doctor_data["name"],
            "exp": datetime.utcnow() + timedelta(hours=8)
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verificar token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except:
            return None

# Instância global
auth_service = AuthService()
