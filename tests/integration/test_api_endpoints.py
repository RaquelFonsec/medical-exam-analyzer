"""
Testes de integração para endpoints da API
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
import io

# Adicionar o diretório backend ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.main import app

class TestAPIEndpoints:
    """Testes de integração para endpoints da API"""
    
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
    
    def test_process_exams_single_file(self, client):
        """Testa processamento de um único arquivo"""
        with patch('app.main.textract_service') as mock_textract, \
             patch('app.main.llm_service') as mock_llm:
            
            # Mock do Textract
            mock_textract.extract_text_from_bytes = AsyncMock(return_value={
                'text': 'Texto extraído de teste',
                'confidence': 95.5,
                'paragraphs': ['Parágrafo 1', 'Parágrafo 2']
            })
            
            # Mock do LLM
            mock_llm.interpretar_exame_para_frontend = AsyncMock(return_value={
                'success': True,
                'llm_analysis': {
                    'clinical_analysis': 'Análise de teste',
                    'exam_type': 'Documento Médico',
                    'key_findings': ['Achado 1', 'Achado 2']
                },
                'model_used': 'gpt-4o',
                'interpretation_complete': True
            })
            
            # Criar arquivo de teste
            test_file = io.BytesIO(b"fake pdf content")
            test_file.name = "test.pdf"
            
            response = client.post(
                "/api/process-exams",
                files={"exams": ("test.pdf", test_file, "application/pdf")},
                data={"patient_context": "Contexto de teste"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "llm_interpretation" in data
    
    def test_process_exams_multiple_files(self, client):
        """Testa processamento de múltiplos arquivos"""
        with patch('app.main.textract_service') as mock_textract, \
             patch('app.main.llm_service') as mock_llm:
            
            # Mock do Textract
            mock_textract.extract_text_from_bytes = AsyncMock(return_value={
                'text': 'Texto extraído de teste',
                'confidence': 95.5,
                'paragraphs': ['Parágrafo 1', 'Parágrafo 2']
            })
            
            # Mock do LLM
            mock_llm.interpretar_exame_para_frontend = AsyncMock(return_value={
                'success': True,
                'llm_analysis': {
                    'clinical_analysis': 'Análise de teste',
                    'exam_type': 'Documento Médico',
                    'key_findings': ['Achado 1', 'Achado 2']
                },
                'model_used': 'gpt-4o',
                'interpretation_complete': True
            })
            
            # Criar múltiplos arquivos de teste
            files = []
            for i in range(3):
                test_file = io.BytesIO(b"fake pdf content")
                test_file.name = f"test_{i}.pdf"
                files.append(("exams", (f"test_{i}.pdf", test_file, "application/pdf")))
            
            response = client.post(
                "/api/process-exams",
                files=files,
                data={"patient_context": "Contexto de teste"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["files_processed"] == 3
            assert "individual_interpretations" in data
    
    def test_process_exams_too_many_files(self, client):
        """Testa limite de arquivos (máximo 10)"""
        # Criar 11 arquivos (acima do limite)
        files = []
        for i in range(11):
            test_file = io.BytesIO(b"fake pdf content")
            test_file.name = f"test_{i}.pdf"
            files.append(("exams", (f"test_{i}.pdf", test_file, "application/pdf")))
        
        response = client.post(
            "/api/process-exams",
            files=files,
            data={"patient_context": "Contexto de teste"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Máximo de 10" in data["error"]
    
    def test_process_exams_no_files(self, client):
        """Testa requisição sem arquivos"""
        response = client.post(
            "/api/process-exams",
            data={"patient_context": "Contexto de teste"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Nenhum arquivo" in data["error"]
    
    def test_process_exams_batch_endpoint(self, client):
        """Testa endpoint de processamento em lote"""
        with patch('app.main.batch_processor') as mock_batch:
            mock_batch.process_batch = AsyncMock(return_value={
                'success': True,
                'total_files': 2,
                'files_processed': 2,
                'results': [
                    {'filename': 'doc1.pdf', 'status': 'success'},
                    {'filename': 'doc2.pdf', 'status': 'success'}
                ],
                'consolidated_analysis': 'Análise consolidada'
            })
            
            # Criar arquivos de teste
            files = []
            for i in range(2):
                test_file = io.BytesIO(b"fake pdf content")
                test_file.name = f"batch_test_{i}.pdf"
                files.append(("exams", (f"batch_test_{i}.pdf", test_file, "application/pdf")))
            
            response = client.post(
                "/api/process-exams-batch",
                files=files,
                data={"patient_context": "Contexto de teste"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["files_processed"] == 2
    
    def test_process_exams_batch_too_many_files(self, client):
        """Testa limite de arquivos no processamento em lote"""
        # Criar 11 arquivos (acima do limite)
        files = []
        for i in range(11):
            test_file = io.BytesIO(b"fake pdf content")
            test_file.name = f"batch_test_{i}.pdf"
            files.append(("exams", (f"batch_test_{i}.pdf", test_file, "application/pdf")))
        
        response = client.post(
            "/api/process-exams-batch",
            files=files,
            data={"patient_context": "Contexto de teste"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Máximo de 10" in data["error"]
    
    def test_invalid_file_types(self, client):
        """Testa tipos de arquivo inválidos"""
        test_file = io.BytesIO(b"fake content")
        test_file.name = "test.txt"  # Tipo não suportado
        
        response = client.post(
            "/api/process-exams",
            files={"exams": ("test.txt", test_file, "text/plain")},
            data={"patient_context": "Contexto de teste"}
        )
        
        # Deve aceitar mas processar com Textract
        assert response.status_code in [200, 400]  # Pode falhar no Textract
    
    def test_large_file_handling(self, client):
        """Testa tratamento de arquivos grandes"""
        # Simular arquivo grande (25MB)
        large_content = b"x" * (25 * 1024 * 1024)
        test_file = io.BytesIO(large_content)
        test_file.name = "large.pdf"
        
        with patch('app.main.textract_service') as mock_textract:
            mock_textract.extract_text_from_bytes = AsyncMock(return_value={
                'text': 'Texto extraído de arquivo grande',
                'confidence': 90.0,
                'paragraphs': ['Parágrafo grande']
            })
            
            response = client.post(
                "/api/process-exams",
                files={"exams": ("large.pdf", test_file, "application/pdf")},
                data={"patient_context": "Contexto de teste"}
            )
            
            # Deve processar ou retornar erro apropriado
            assert response.status_code in [200, 400, 413]
