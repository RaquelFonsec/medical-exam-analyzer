"""
Configuração global para testes
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import tempfile
import os
from pathlib import Path

# Configuração de fixtures globais
@pytest.fixture(scope="session")
def event_loop():
    """Cria event loop para testes assíncronos"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_llm_service():
    """Mock do serviço LLM para testes"""
    mock = Mock()
    mock.interpretar_exame_para_frontend = AsyncMock(return_value={
        'success': True,
        'llm_analysis': {
            'clinical_analysis': 'Análise de teste',
            'exam_type': 'Documento Médico',
            'key_findings': ['Achado 1', 'Achado 2']
        },
        'model_used': 'gpt-4o',
        'interpretation_complete': True
    })
    return mock

@pytest.fixture
def mock_textract_service():
    """Mock do serviço Textract para testes"""
    mock = Mock()
    mock.extract_text_from_bytes = AsyncMock(return_value={
        'text': 'Texto extraído de teste',
        'confidence': 95.5,
        'paragraphs': ['Parágrafo 1', 'Parágrafo 2']
    })
    return mock

@pytest.fixture
def sample_pdf_file():
    """Arquivo PDF de teste"""
    # Criar um arquivo temporário para testes
    temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    temp_file.write(b'%PDF-1.4\n%Test PDF content')
    temp_file.close()
    yield temp_file.name
    os.unlink(temp_file.name)

@pytest.fixture
def sample_image_file():
    """Arquivo de imagem de teste"""
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    temp_file.write(b'fake image content')
    temp_file.close()
    yield temp_file.name
    os.unlink(temp_file.name)
