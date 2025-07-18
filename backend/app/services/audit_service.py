import json
import logging
from datetime import datetime
from typing import Dict, Any

class AuditService:
    def __init__(self):
        # Configurar logger LGPD
        logging.basicConfig(
            filename='logs/lgpd_audit.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger('lgpd_audit')
        print("✅ Serviço de auditoria LGPD inicializado")
    
    def log_patient_access(self, doctor_crm: str, patient_hash: str, action: str, details: Dict = None):
        """Registrar acesso a dados do paciente"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "doctor_crm": doctor_crm,
            "patient_hash": patient_hash,  # Hash do paciente (não dados reais)
            "action": action,
            "details": details or {},
            "compliance": "LGPD"
        }
        self.logger.info(json.dumps(audit_entry, ensure_ascii=False))
    
    def log_consent(self, patient_hash: str, consent_given: bool, consent_type: str):
        """Registrar consentimento do paciente"""
        self.log_patient_access(
            doctor_crm="system",
            patient_hash=patient_hash,
            action="consent_recorded",
            details={
                "consent_given": consent_given,
                "consent_type": consent_type
            }
        )
    
    def log_data_processing(self, doctor_crm: str, patient_hash: str, processing_type: str):
        """Registrar processamento de dados"""
        self.log_patient_access(
            doctor_crm=doctor_crm,
            patient_hash=patient_hash,
            action="data_processing",
            details={"processing_type": processing_type}
        )

# Instância global
audit_service = AuditService()
