from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from datetime import datetime

Base = declarative_base()

class MedicalConsultation(Base):
    __tablename__ = "medical_consultations"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_info = Column(Text, nullable=False)
    audio_transcription = Column(Text)
    medical_report = Column(Text)
    patient_hash = Column(String(64), index=True)  # Hash para auditoria LGPD
    confidence = Column(Float)
    model_used = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Configurar banco
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://medical_user:MedicalApp2024!@localhost:5432/medical_exams")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Criar tabelas
Base.metadata.create_all(bind=engine)
