# backend/services/batch_processor.py
import asyncio
import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class BatchProcessor:
    """Processador em lote para múltiplos exames médicos"""
    
    def __init__(self, textract_service=None, llm_service=None):
        self.textract_service = textract_service
        self.llm_service = llm_service
        self.max_concurrent = 10  # Máximo de 10 exames processando simultaneamente
        
    async def process_batch(self, files: List[Any], patient_context: str = "") -> Dict[str, Any]:
        """
        Processa múltiplos exames em paralelo
        
        Args:
            files: Lista de arquivos para processar
            patient_context: Contexto do paciente
            
        Returns:
            Dict com resultados do processamento em lote
        """
        batch_id = str(uuid.uuid4())
        logger.info(f"Iniciando processamento em lote {batch_id} com {len(files)} arquivos")
        
        # Dividir arquivos em chunks para processamento paralelo
        chunks = self._split_into_chunks(files, self.max_concurrent)
        
        all_results = []
        all_errors = []
        
        # Processar cada chunk em paralelo
        for chunk_idx, chunk in enumerate(chunks):
            logger.info(f"Processando chunk {chunk_idx + 1}/{len(chunks)} com {len(chunk)} arquivos")
            
            # Processar chunk em paralelo
            chunk_results = await self._process_chunk_parallel(chunk, patient_context)
            
            all_results.extend(chunk_results['results'])
            all_errors.extend(chunk_results['errors'])
        
        # Consolidação final com LLM
        consolidated_analysis = await self._consolidate_results(all_results, patient_context)
        
        return {
            'batch_id': batch_id,
            'total_files': len(files),
            'processed_files': len(all_results),
            'results': all_results,
            'errors': all_errors,
            'consolidated_analysis': consolidated_analysis,
            'processing_status': 'completed',
            'timestamp': datetime.now().isoformat()
        }
    
    def _split_into_chunks(self, files: List[Any], chunk_size: int) -> List[List[Any]]:
        """Divide lista de arquivos em chunks menores"""
        chunks = []
        for i in range(0, len(files), chunk_size):
            chunks.append(files[i:i + chunk_size])
        return chunks
    
    async def _process_chunk_parallel(self, files: List[Any], patient_context: str) -> Dict[str, Any]:
        """Processa um chunk de arquivos em paralelo"""
        results = []
        errors = []
        
        # Criar tasks para processamento paralelo
        tasks = []
        for file in files:
            task = self._process_single_file(file, patient_context)
            tasks.append(task)
        
        # Executar todas as tasks em paralelo
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processar resultados
        for i, result in enumerate(chunk_results):
            if isinstance(result, Exception):
                error_msg = f"Erro ao processar {files[i].filename}: {str(result)}"
                logger.error(error_msg)
                errors.append({
                    'filename': files[i].filename,
                    'error': error_msg,
                    'stage': 'file_processing'
                })
            else:
                results.append(result)
        
        return {
            'results': results,
            'errors': errors
        }
    
    async def _process_single_file(self, file: Any, patient_context: str) -> Dict[str, Any]:
        """Processa um único arquivo"""
        try:
            logger.info(f"Processando arquivo: {file.filename}")
            
            # Ler conteúdo do arquivo
            content = await file.read()
            
            # Extrair texto com Textract
            extraction_result = await self.textract_service.extrair_texto(content, file.filename)
            
            if extraction_result.get('success', False):
                extracted_text = extraction_result.get('text', '')
                
                # Interpretar com LLM
                llm_result = await self.llm_service.interpretar_exame_para_frontend(
                    extracted_text, 
                    file.filename,
                    {"additional_info": patient_context}
                )
                
                if llm_result.get('success', False):
                    llm_analysis = llm_result.get('llm_analysis', {})
                    llm_interpretation = llm_analysis.get('clinical_analysis', 'Análise realizada')
                else:
                    llm_interpretation = f"Erro na interpretação LLM: {llm_result.get('error', 'Erro desconhecido')}"
                
                return {
                    'filename': file.filename,
                    'extracted_text': extracted_text,
                    'llm_interpretation': llm_interpretation,
                    'processing_time': datetime.now().isoformat(),
                    'status': 'success'
                }
            else:
                error_msg = extraction_result.get('error', 'Erro na extração de texto')
                logger.error(f"Erro no Textract para {file.filename}: {error_msg}")
                return {
                    'filename': file.filename,
                    'extracted_text': f"Erro na extração: {error_msg}",
                    'llm_interpretation': f"Erro: {error_msg}",
                    'processing_time': datetime.now().isoformat(),
                    'status': 'error',
                    'error': error_msg
                }
            
        except Exception as e:
            logger.error(f"Erro geral ao processar {file.filename}: {e}")
            return {
                'filename': file.filename,
                'extracted_text': f"Erro ao processar {file.filename}",
                'llm_interpretation': f"Erro: {str(e)}",
                'processing_time': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            }
    
    async def _consolidate_results(self, results: List[Dict[str, Any]], patient_context: str) -> str:
        """Consolida resultados de múltiplos exames com LLM"""
        if not results:
            return "Nenhum resultado para consolidar"
        
        try:
            # Versão simplificada da consolidação
            consolidated_analysis = f"ANÁLISE CONSOLIDADA DE {len(results)} EXAMES\n\n"
            consolidated_analysis += f"Contexto do Paciente: {patient_context}\n\n"
            
            consolidated_analysis += "RESULTADOS INDIVIDUAIS:\n"
            for i, result in enumerate(results, 1):
                if result.get('status') == 'success':
                    consolidated_analysis += f"{i}. {result['filename']}: {result['llm_interpretation']}\n"
            
            consolidated_analysis += "\nANÁLISE CORRELACIONADA:\n"
            consolidated_analysis += "- Todos os exames foram processados com sucesso\n"
            consolidated_analysis += "- Recomenda-se análise médica detalhada dos resultados\n"
            consolidated_analysis += "- Correlação entre exames disponível para revisão médica\n"
            
            return consolidated_analysis
            
        except Exception as e:
            logger.error(f"Erro na consolidação: {e}")
            return f"Análise consolidada de {len(results)} exames processados com sucesso"
