"""
Testes unitários para o processador em lote
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
from datetime import datetime

# Adicionar o diretório backend ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from services.batch_processor import BatchProcessor

class TestBatchProcessor:
    """Testes para a classe BatchProcessor"""
    
    @pytest.fixture
    def batch_processor(self, mock_llm_service, mock_textract_service):
        """Fixture para criar instância do processador em lote"""
        return BatchProcessor(
            textract_service=mock_textract_service,
            llm_service=mock_llm_service
        )
    
    @pytest.fixture
    def mock_files(self):
        """Arquivos mock para teste"""
        files = []
        for i in range(3):
            mock_file = Mock()
            mock_file.filename = f"test_document_{i}.pdf"
            mock_file.read = AsyncMock(return_value=b"fake pdf content")
            files.append(mock_file)
        return files
    
    @pytest.mark.asyncio
    async def test_process_single_file_success(self, batch_processor, mock_textract_service, mock_llm_service):
        """Testa processamento bem-sucedido de um único arquivo"""
        # Configurar mocks para retornar sucesso
        mock_textract_service.extrair_texto = AsyncMock(return_value={
            'success': True,
            'text': 'Texto extraído de teste'
        })
        
        mock_llm_service.interpretar_exame_para_frontend = AsyncMock(return_value={
            'success': True,
            'llm_analysis': {
                'clinical_analysis': 'Análise de teste'
            }
        })
        
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(return_value=b"fake content")
        
        result = await batch_processor._process_single_file(mock_file, "contexto teste")
        
        assert result['status'] == 'success'
        assert result['filename'] == "test.pdf"
        assert 'extracted_text' in result
        assert 'llm_interpretation' in result
    
    @pytest.mark.asyncio
    async def test_process_single_file_error(self, batch_processor):
        """Testa tratamento de erro no processamento de arquivo"""
        mock_file = Mock()
        mock_file.filename = "error.pdf"
        mock_file.read = AsyncMock(side_effect=Exception("Erro de leitura"))
        
        result = await batch_processor._process_single_file(mock_file, "contexto teste")
        
        assert result['status'] == 'error'
        assert 'error' in result
        assert result['filename'] == "error.pdf"
    
    @pytest.mark.asyncio
    async def test_consolidate_results(self, batch_processor):
        """Testa consolidação de resultados"""
        results = [
            {
                'filename': 'doc1.pdf',
                'status': 'success',
                'llm_interpretation': 'Análise 1'
            },
            {
                'filename': 'doc2.pdf', 
                'status': 'success',
                'llm_interpretation': 'Análise 2'
            }
        ]
        
        consolidated = await batch_processor._consolidate_results(results, "contexto teste")
        
        assert "ANÁLISE CONSOLIDADA" in consolidated
        assert "doc1.pdf" in consolidated
        assert "doc2.pdf" in consolidated
        assert "contexto teste" in consolidated
    
    @pytest.mark.asyncio
    async def test_process_batch_success(self, batch_processor, mock_files):
        """Testa processamento em lote bem-sucedido"""
        result = await batch_processor.process_batch(mock_files, "contexto teste")
        
        assert result['total_files'] == 3
        assert result['processed_files'] == 3
        assert len(result['results']) == 3
        assert 'consolidated_analysis' in result
    
    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self, batch_processor):
        """Testa processamento em lote com alguns erros"""
        # Criar arquivos com um que vai dar erro
        files = []
        
        # Arquivo que funciona
        good_file = Mock()
        good_file.filename = "good.pdf"
        good_file.read = AsyncMock(return_value=b"good content")
        files.append(good_file)
        
        # Arquivo que dá erro
        bad_file = Mock()
        bad_file.filename = "bad.pdf"
        bad_file.read = AsyncMock(side_effect=Exception("Erro"))
        files.append(bad_file)
        
        result = await batch_processor.process_batch(files, "contexto teste")
        
        assert result['total_files'] == 2
        assert result['processed_files'] == 2  # Ambos são processados, mas um falha
        # Verificar se há pelo menos um resultado com status 'error'
        error_results = [r for r in result['results'] if r.get('status') == 'error']
        assert len(error_results) >= 1
    
    def test_max_concurrent_limit(self, batch_processor):
        """Testa limite de processamento simultâneo"""
        assert batch_processor.max_concurrent == 10  # Verificar se foi atualizado
    
    @pytest.mark.asyncio
    async def test_empty_files_list(self, batch_processor):
        """Testa processamento com lista vazia"""
        result = await batch_processor.process_batch([], "contexto teste")
        
        assert result['total_files'] == 0
        assert result['processed_files'] == 0
        assert len(result['results']) == 0
    
    @pytest.mark.asyncio
    async def test_large_batch_processing(self, batch_processor):
        """Testa processamento de lote grande (10 arquivos)"""
        files = []
        for i in range(10):
            mock_file = Mock()
            mock_file.filename = f"large_batch_{i}.pdf"
            mock_file.read = AsyncMock(return_value=b"content")
            files.append(mock_file)
        
        result = await batch_processor.process_batch(files, "contexto teste")
        
        assert result['total_files'] == 10
        assert result['processed_files'] == 10
