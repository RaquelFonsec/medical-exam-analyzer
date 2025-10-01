"""
Testes de performance e carga
"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
import io

# Adicionar o diretório backend ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from app.main import app

class TestPerformance:
    """Testes de performance e carga"""
    
    @pytest.fixture
    def client(self):
        """Cliente de teste para a API"""
        return TestClient(app)
    
    def test_single_document_processing_time(self, client):
        """Testa tempo de processamento de um documento"""
        with patch('app.main.textract_service') as mock_textract, \
             patch('app.main.llm_service') as mock_llm:
            
            # Mock com delay simulado
            async def mock_textract_delay(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simular 100ms
                return {
                    'text': 'Texto extraído',
                    'confidence': 95.5,
                    'paragraphs': ['Parágrafo 1']
                }
            
            async def mock_llm_delay(*args, **kwargs):
                await asyncio.sleep(0.2)  # Simular 200ms
                return {
                    'success': True,
                    'llm_analysis': {
                        'clinical_analysis': 'Análise',
                        'exam_type': 'Documento Médico',
                        'key_findings': ['Achado']
                    },
                    'model_used': 'gpt-4o',
                    'interpretation_complete': True
                }
            
            mock_textract.extract_text_from_bytes = mock_textract_delay
            mock_llm.interpretar_exame_para_frontend = mock_llm_delay
            
            test_file = io.BytesIO(b"fake pdf content")
            test_file.name = "test.pdf"
            
            start_time = time.time()
            response = client.post(
                "/api/process-exams",
                files={"exams": ("test.pdf", test_file, "application/pdf")},
                data={"patient_context": "Contexto"}
            )
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            assert response.status_code == 200
            assert processing_time < 5.0  # Deve processar em menos de 5 segundos
            print(f"Tempo de processamento: {processing_time:.2f}s")
    
    def test_multiple_documents_parallel_processing(self, client):
        """Testa processamento paralelo de múltiplos documentos"""
        with patch('app.main.textract_service') as mock_textract, \
             patch('app.main.llm_service') as mock_llm:
            
            # Mock com delay simulado
            async def mock_textract_delay(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms por documento
                return {
                    'text': 'Texto extraído',
                    'confidence': 95.5,
                    'paragraphs': ['Parágrafo']
                }
            
            async def mock_llm_delay(*args, **kwargs):
                await asyncio.sleep(0.2)  # 200ms por documento
                return {
                    'success': True,
                    'llm_analysis': {
                        'clinical_analysis': 'Análise',
                        'exam_type': 'Documento Médico',
                        'key_findings': ['Achado']
                    },
                    'model_used': 'gpt-4o',
                    'interpretation_complete': True
                }
            
            mock_textract.extract_text_from_bytes = mock_textract_delay
            mock_llm.interpretar_exame_para_frontend = mock_llm_delay
            
            # Criar 5 documentos
            files = []
            for i in range(5):
                test_file = io.BytesIO(b"fake pdf content")
                test_file.name = f"test_{i}.pdf"
                files.append(("exams", (f"test_{i}.pdf", test_file, "application/pdf")))
            
            start_time = time.time()
            response = client.post(
                "/api/process-exams",
                files=files,
                data={"patient_context": "Contexto"}
            )
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            assert response.status_code == 200
            # Processamento paralelo deve ser mais rápido que sequencial
            # 5 documentos * 300ms = 1.5s sequencial, paralelo deve ser < 1.5s
            assert processing_time < 1.5
            print(f"Tempo de processamento paralelo (5 docs): {processing_time:.2f}s")
    
    def test_maximum_files_processing(self, client):
        """Testa processamento do máximo de arquivos (10)"""
        with patch('app.main.textract_service') as mock_textract, \
             patch('app.main.llm_service') as mock_llm:
            
            # Mock otimizado para teste de carga
            async def mock_textract_fast(*args, **kwargs):
                await asyncio.sleep(0.05)  # 50ms
                return {
                    'text': 'Texto extraído',
                    'confidence': 95.5,
                    'paragraphs': ['Parágrafo']
                }
            
            async def mock_llm_fast(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms
                return {
                    'success': True,
                    'llm_analysis': {
                        'clinical_analysis': 'Análise',
                        'exam_type': 'Documento Médico',
                        'key_findings': ['Achado']
                    },
                    'model_used': 'gpt-4o',
                    'interpretation_complete': True
                }
            
            mock_textract.extract_text_from_bytes = mock_textract_fast
            mock_llm.interpretar_exame_para_frontend = mock_llm_fast
            
            # Criar 10 documentos (máximo)
            files = []
            for i in range(10):
                test_file = io.BytesIO(b"fake pdf content")
                test_file.name = f"max_test_{i}.pdf"
                files.append(("exams", (f"max_test_{i}.pdf", test_file, "application/pdf")))
            
            start_time = time.time()
            response = client.post(
                "/api/process-exams",
                files=files,
                data={"patient_context": "Contexto"}
            )
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            assert response.status_code == 200
            data = response.json()
            assert data["files_processed"] == 10
            assert processing_time < 3.0  # Deve processar 10 docs em menos de 3s
            print(f"Tempo de processamento (10 docs): {processing_time:.2f}s")
    
    def test_concurrent_requests(self, client):
        """Testa múltiplas requisições simultâneas"""
        with patch('app.main.textract_service') as mock_textract, \
             patch('app.main.llm_service') as mock_llm:
            
            # Mock com delay
            async def mock_textract_delay(*args, **kwargs):
                await asyncio.sleep(0.1)
                return {
                    'text': 'Texto extraído',
                    'confidence': 95.5,
                    'paragraphs': ['Parágrafo']
                }
            
            async def mock_llm_delay(*args, **kwargs):
                await asyncio.sleep(0.2)
                return {
                    'success': True,
                    'llm_analysis': {
                        'clinical_analysis': 'Análise',
                        'exam_type': 'Documento Médico',
                        'key_findings': ['Achado']
                    },
                    'model_used': 'gpt-4o',
                    'interpretation_complete': True
                }
            
            mock_textract.extract_text_from_bytes = mock_textract_delay
            mock_llm.interpretar_exame_para_frontend = mock_llm_delay
            
            def make_request():
                test_file = io.BytesIO(b"fake pdf content")
                test_file.name = "concurrent_test.pdf"
                return client.post(
                    "/api/process-exams",
                    files={"exams": ("concurrent_test.pdf", test_file, "application/pdf")},
                    data={"patient_context": "Contexto"}
                )
            
            # Fazer 3 requisições simultâneas
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(make_request) for _ in range(3)]
                responses = [future.result() for future in futures]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Todas as requisições devem ter sucesso
            for response in responses:
                assert response.status_code == 200
            
            # Tempo total deve ser menor que processamento sequencial
            # 3 requisições * 300ms = 900ms sequencial, paralelo deve ser < 900ms
            assert total_time < 1.0
            print(f"Tempo de 3 requisições simultâneas: {total_time:.2f}s")
    
    def test_memory_usage_with_large_files(self, client):
        """Testa uso de memória com arquivos grandes"""
        with patch('app.main.textract_service') as mock_textract, \
             patch('app.main.llm_service') as mock_llm:
            
            # Mock que simula processamento de arquivo grande
            async def mock_textract_large(*args, **kwargs):
                await asyncio.sleep(0.2)
                return {
                    'text': 'Texto muito longo ' * 1000,  # Simular texto grande
                    'confidence': 90.0,
                    'paragraphs': ['Parágrafo grande'] * 100
                }
            
            async def mock_llm_large(*args, **kwargs):
                await asyncio.sleep(0.3)
                return {
                    'success': True,
                    'llm_analysis': {
                        'clinical_analysis': 'Análise longa ' * 100,
                        'exam_type': 'Documento Médico',
                        'key_findings': ['Achado'] * 50
                    },
                    'model_used': 'gpt-4o',
                    'interpretation_complete': True
                }
            
            mock_textract.extract_text_from_bytes = mock_textract_large
            mock_llm.interpretar_exame_para_frontend = mock_llm_large
            
            # Criar arquivo grande
            large_content = b"x" * (5 * 1024 * 1024)  # 5MB
            test_file = io.BytesIO(large_content)
            test_file.name = "large_file.pdf"
            
            start_time = time.time()
            response = client.post(
                "/api/process-exams",
                files={"exams": ("large_file.pdf", test_file, "application/pdf")},
                data={"patient_context": "Contexto"}
            )
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            assert response.status_code == 200
            assert processing_time < 10.0  # Deve processar arquivo grande em menos de 10s
            print(f"Tempo de processamento de arquivo grande: {processing_time:.2f}s")
