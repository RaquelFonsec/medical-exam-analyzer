from app.database import engine
from app.models.exam import Exam
from app.database import Base

def create_tables():
    """Criar todas as tabelas no banco"""
    print("Criando tabelas no banco de dados...")
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso!")

if __name__ == "__main__":
    create_tables()
