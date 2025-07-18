from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from sqlalchemy.sql import func
from ..database import Base

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    exam_type = Column(String, nullable=False)
    extracted_text = Column(Text)
    report = Column(Text)
    confidence = Column(Float)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    file_path = Column(String)
    file_size = Column(Integer)
    is_encrypted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Exam(id={self.id}, filename='{self.filename}', exam_type='{self.exam_type}')>"
