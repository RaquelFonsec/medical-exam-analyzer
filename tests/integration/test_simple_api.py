"""
Testes de integração simplificados para a API
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Adicionar o diretório backend ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.main import app

class TestSimpleAPI:
    """Testes de integração simplificados"""
    
    @pytest.fixture
    def client(self):
        """Cliente de teste para a API"""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Testa endpoint de saúde"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Testa endpoint raiz"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_docs_endpoint(self, client):
        """Testa endpoint de documentação"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_endpoint(self, client):
        """Testa endpoint OpenAPI"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
    
    def test_process_exams_no_files(self, client):
        """Testa requisição sem arquivos"""
        response = client.post("/api/process-exams")
        # Deve retornar erro de validação
        assert response.status_code in [400, 422]
    
    def test_process_exams_invalid_method(self, client):
        """Testa método HTTP inválido"""
        response = client.get("/api/process-exams")
        assert response.status_code == 405  # Method Not Allowed
    
    def test_nonexistent_endpoint(self, client):
        """Testa endpoint inexistente"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
