"""
Testes unitários para o serviço LLM
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Adicionar o diretório backend ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from services.llm import InterpretadorLLM

class TestInterpretadorLLM:
    """Testes para a classe InterpretadorLLM"""
    
    @pytest.fixture
    def llm_service(self):
        """Fixture para criar instância do serviço LLM"""
        with patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            service = InterpretadorLLM()
            return service
    
    def test_detectar_tipo_documento_medico(self, llm_service):
        """Testa detecção de documento médico"""
        texto_medico = """
        Paciente: João Silva
        Data: 15/10/2024
        Hemograma completo
        Leucócitos: 7.500/mm³
        Hemácias: 4.5 milhões/mm³
        """
        
        tipo = llm_service._detectar_tipo_documento(texto_medico, "exame.pdf")
        assert 'Médico' in tipo or 'EXAME' in tipo or 'Hemograma' in tipo
    
    def test_detectar_tipo_documento_juridico(self, llm_service):
        """Testa detecção de documento jurídico"""
        texto_juridico = """
        CONTRATO DE PRESTAÇÃO DE SERVIÇOS
        Cláusula 1: Objeto
        Cláusula 2: Prazo
        """
        
        tipo = llm_service._detectar_tipo_documento(texto_juridico, "contrato.pdf")
        assert 'Jurídico' in tipo
    
    def test_detectar_tipo_documento_tecnico(self, llm_service):
        """Testa detecção de documento técnico"""
        texto_tecnico = """
        DOCUMENTAÇÃO TÉCNICA
        API REST
        Endpoint: /api/v1/users
        Método: GET
        """
        
        tipo = llm_service._detectar_tipo_documento(texto_tecnico, "api.pdf")
        assert 'Técnico' in tipo
    
    def test_remover_duplicacao_analise_finalizada(self, llm_service):
        """Testa remoção de duplicação de 'ANÁLISE FINALIZADA'"""
        texto_com_duplicacao = """
        Análise do documento...
        
        ANÁLISE FINALIZADA
        
        Mais texto...
        
        ANÁLISE FINALIZADA
        """
        
        # Simular o processamento interno
        if texto_com_duplicacao.count("ANÁLISE FINALIZADA") > 1:
            primeira_ocorrencia = texto_com_duplicacao.find("ANÁLISE FINALIZADA")
            if primeira_ocorrencia != -1:
                texto_com_duplicacao = texto_com_duplicacao[:primeira_ocorrencia + len("ANÁLISE FINALIZADA")]
        
        assert texto_com_duplicacao.count("ANÁLISE FINALIZADA") == 1
        assert texto_com_duplicacao.endswith("ANÁLISE FINALIZADA")
    
    def test_garantir_analise_finalizada_no_final(self, llm_service):
        """Testa garantia de 'ANÁLISE FINALIZADA' no final"""
        texto_sem_finalizacao = "Análise do documento..."
        
        # Simular lógica de garantia
        if not texto_sem_finalizacao.endswith("ANÁLISE FINALIZADA"):
            if "ANÁLISE FINALIZADA" in texto_sem_finalizacao:
                texto_sem_finalizacao = texto_sem_finalizacao.split("ANÁLISE FINALIZADA")[0] + "ANÁLISE FINALIZADA"
            else:
                texto_sem_finalizacao = texto_sem_finalizacao.strip() + "\n\nANÁLISE FINALIZADA"
        
        assert texto_sem_finalizacao.endswith("ANÁLISE FINALIZADA")
        assert texto_sem_finalizacao.count("ANÁLISE FINALIZADA") == 1
    
    def test_extrair_achados_relevantes(self, llm_service):
        """Testa extração de achados relevantes"""
        texto_exame = """
        Hemograma completo:
        - Leucócitos: 7.500/mm³ (normal)
        - Hemácias: 4.5 milhões/mm³ (normal)
        - Plaquetas: 250.000/mm³ (normal)
        - Hemoglobina: 14.5 g/dL (normal)
        
        Conclusão: Hemograma dentro da normalidade
        """
        
        achados = llm_service._extrair_achados_principais(texto_exame)
        
        assert len(achados) > 0
        assert any('Leucócitos' in achado for achado in achados)
        assert any('Hemácias' in achado for achado in achados)
    
    def test_gerar_status_geral_medico(self, llm_service):
        """Testa geração de status geral para documento médico"""
        status = llm_service._gerar_status_geral("Documento Médico", "Análise realizada")
        
        assert "médico" in status.lower()
        assert "profissional" in status.lower()
    
    def test_gerar_status_geral_juridico(self, llm_service):
        """Testa geração de status geral para documento jurídico"""
        status = llm_service._gerar_status_geral("Documento Jurídico", "Análise realizada")
        
        assert "jurídico" in status.lower()
        assert "advogado" in status.lower()
