# ============================================================================
# MAIN.PY - SISTEMA MÉDICO COM PIPELINE E RAG
# Ajustado para estrutura real do projeto
# ============================================================================

import os
import sys
import traceback
import tempfile
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

# Configurar path para imports
sys.path.append('.')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# Verificar variáveis essenciais
required_env_vars = ['OPENAI_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Variáveis de ambiente faltando: {missing_vars}")
    sys.exit(1)

app = FastAPI(
    title="Medical AI System", 
    version="3.1",
    description="Sistema de análise médica com pipeline e RAG"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importações dos serviços (ajustado para sua estrutura)
medical_pipeline = None
rag_service = None

try:
    # Importar o pipeline médico
    from services.complete_medical_pipeline import CompleteMedicalPipeline
    medical_pipeline = CompleteMedicalPipeline()
    print("✅ Complete Medical Pipeline carregado")
except ImportError as e:
    print(f"❌ Erro ao carregar Complete Medical Pipeline: {e}")
    try:
        # Tentar import alternativo
        from app.services.complete_medical_pipeline import CompleteMedicalPipeline
        medical_pipeline = CompleteMedicalPipeline()
        print("✅ Complete Medical Pipeline carregado (import alternativo)")
    except ImportError as e2:
        print(f"❌ Erro no import alternativo: {e2}")
        medical_pipeline = None

try:
    # Importar o serviço RAG
    from services.rag import RAGService
    rag_service = RAGService()
    print("✅ RAG Service carregado")
except ImportError as e:
    print(f"⚠️ Tentando imports RAG alternativos: {e}")
    try:
        from app.services.rag import RAGService
        rag_service = RAGService()
        print("✅ RAG Service carregado (import alternativo)")
    except ImportError:
        try:
            from services.rag.rag_service import RAGService
            rag_service = RAGService()
            print("✅ RAG Service carregado (subpasta)")
        except ImportError:
            print("⚠️ RAG Service não encontrado")
            rag_service = None


# Modelos Pydantic para entrada
class PatientAnalysisRequest(BaseModel):
    patient_info: str = Field(..., description="Informações do paciente")
    transcription: Optional[str] = Field(None, description="Transcrição de áudio")
    image_analysis: Optional[str] = Field(None, description="Análise de imagem")


def is_audio_file(content_type: str, filename: str) -> bool:
    """Verifica se o arquivo é de áudio"""
    if not filename:
        return False
        
    audio_types = ['audio/', 'video/', 'application/octet-stream']
    audio_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.webm', '.mp4', '.mpeg', '.aac']
    
    if content_type:
        for audio_type in audio_types:
            if content_type.startswith(audio_type):
                return True
    
    if filename:
        for ext in audio_extensions:
            if filename.lower().endswith(ext):
                return True
    
    return False


def is_image_file(content_type: str, filename: str) -> bool:
    """Verifica se o arquivo é uma imagem"""
    if not filename:
        return False
        
    image_types = ['image/']
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']
    
    if content_type:
        for image_type in image_types:
            if content_type.startswith(image_type):
                return True
    
    if filename:
        for ext in image_extensions:
            if filename.lower().endswith(ext):
                return True
    
    return False


async def process_audio_safely(audio_file: UploadFile) -> Optional[bytes]:
    """Processa arquivo de áudio de forma segura"""
    try:
        if not audio_file or not audio_file.filename:
            return None
            
        # Verificar se é áudio válido
        if not is_audio_file(audio_file.content_type or "", audio_file.filename):
            logger.warning(f"⚠️ Arquivo não reconhecido como áudio: {audio_file.filename}, tipo: {audio_file.content_type}")
            # Ainda assim tentar processar se tem extensão de áudio
            if not any(audio_file.filename.lower().endswith(ext) for ext in ['.mp3', '.wav', '.m4a', '.ogg']):
                return None
        
        # Ler dados binários do áudio
        audio_content = await audio_file.read()
        logger.info(f"🎤 Áudio processado: {len(audio_content)} bytes, arquivo: {audio_file.filename}")
        
        return audio_content
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar áudio: {e}")
        return None


async def process_image_safely(image_file: UploadFile) -> Optional[str]:
    """Processa arquivo de imagem de forma segura"""
    try:
        if not image_file or not image_file.filename:
            return None
            
        # Verificar se é imagem válida
        if not is_image_file(image_file.content_type or "", image_file.filename):
            logger.warning(f"⚠️ Arquivo não é imagem válida: {image_file.filename}, tipo: {image_file.content_type}")
            return None
        
        # Ler dados da imagem
        image_content = await image_file.read()
        
        # Criar arquivo temporário seguro
        file_extension = os.path.splitext(image_file.filename)[1] or '.jpg'
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_extension,
            prefix="medical_img_"
        ) as temp_file:
            temp_file.write(image_content)
            temp_path = temp_file.name
        
        logger.info(f"🖼️ Imagem processada: {temp_path}, arquivo: {image_file.filename}")
        return temp_path
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar imagem: {e}")
        return None


@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis(
    patient_info: str = Form(default=""),
    audio_data: Optional[UploadFile] = File(None),
    image_data: Optional[UploadFile] = File(None)
):
    """🚀 ENDPOINT PRINCIPAL - ANÁLISE MÉDICA COMPLETA"""
    
    start_time = datetime.now()
    temp_files = []  # Para limpeza posterior
    
    logger.info(f"🚀 NOVA ANÁLISE INICIADA - {start_time}")
    logger.info(f"📝 Patient Info: {patient_info[:100]}...")
    logger.info(f"🎧 Audio: {audio_data.filename if audio_data else 'None'}")
    logger.info(f"🖼️ Image: {image_data.filename if image_data else 'None'}")
    
    try:
        # Validação inicial
        if not patient_info.strip():
            logger.warning("⚠️ Patient info vazio")
            patient_info = "Paciente não identificado"
        
        # 1. PROCESSAMENTO SEGURO DE ARQUIVOS
        logger.info("🔄 Processando arquivos...")
        
        audio_bytes = await process_audio_safely(audio_data)
        image_path = await process_image_safely(image_data)
        
        if image_path:
            temp_files.append(image_path)
        
        # 2. PREPARAR DADOS PARA ANÁLISE
        analysis_data = {
            "patient_info": patient_info,
            "audio_bytes": audio_bytes,
            "image_path": image_path,
            "timestamp": start_time.isoformat(),
            "has_audio": audio_bytes is not None,
            "has_image": image_path is not None
        }
        
        # 3. EXECUTAR ANÁLISE
        analysis_result = {}
        
        # Se temos o pipeline médico, usar ele
        if medical_pipeline:
            try:
                logger.info("🔄 Executando Complete Medical Pipeline...")
                
                # Tentar diferentes métodos do pipeline
                if hasattr(medical_pipeline, 'analyze'):
                    analysis_result = await medical_pipeline.analyze(analysis_data)
                elif hasattr(medical_pipeline, 'process'):
                    analysis_result = await medical_pipeline.process(analysis_data)
                elif hasattr(medical_pipeline, 'run'):
                    analysis_result = await medical_pipeline.run(analysis_data)
                elif hasattr(medical_pipeline, 'invoke'):
                    analysis_result = await medical_pipeline.invoke(analysis_data)
                else:
                    # Tentar chamar diretamente
                    analysis_result = await medical_pipeline(analysis_data)
                
                logger.info("✅ Pipeline médico concluído")
                
            except Exception as e:
                logger.error(f"❌ Erro no pipeline médico: {e}")
                analysis_result = {
                    "success": False,
                    "error": str(e),
                    "transcription": "",
                    "analysis": f"Erro no pipeline: {str(e)}",
                    "medical_report": f"Análise falhou: {str(e)}"
                }
        else:
            # Análise básica sem pipeline
            logger.warning("⚠️ Pipeline não disponível, fazendo análise básica")
            analysis_result = {
                "success": True,
                "transcription": "Transcrição não disponível (pipeline não carregado)",
                "analysis": f"Análise básica para: {patient_info}",
                "medical_report": "Relatório básico - pipeline não disponível",
                "patient_data": {"name": patient_info}
            }
        
        # 4. ESTRUTURAR RESULTADO
        result = {
            "success": analysis_result.get("success", True),
            "timestamp": start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "patient_info": patient_info,
            "transcription": analysis_result.get("transcription", ""),
            "patient_data": analysis_result.get("patient_data", {}),
            "medical_report": analysis_result.get("medical_report", ""),
            "image_analysis": analysis_result.get("image_analysis", ""),
            "analysis": analysis_result.get("analysis", ""),
            "pipeline_available": medical_pipeline is not None,
            "files_processed": {
                "audio": audio_bytes is not None,
                "image": image_path is not None
            }
        }
        
        # 5. INTEGRAÇÃO RAG (se disponível)
        if rag_service:
            try:
                logger.info("🔄 Iniciando busca RAG...")
                
                # Usar transcrição ou info do paciente
                search_query = result.get("transcription", "").strip()
                if not search_query:
                    search_query = patient_info
                
                if search_query:
                    # Buscar documentos similares
                    similar_docs = []
                    
                    # Tentar diferentes métodos de busca
                    if hasattr(rag_service, 'search'):
                        similar_docs = rag_service.search(search_query, k=5)
                    elif hasattr(rag_service, 'similarity_search'):
                        similar_docs = rag_service.similarity_search(search_query, k=5)
                    elif hasattr(rag_service, 'query'):
                        similar_docs = rag_service.query(search_query, k=5)
                    elif hasattr(rag_service, 'buscar_documentos_similares'):
                        similar_docs = rag_service.buscar_documentos_similares(search_query, k=5)
                    
                    if similar_docs:
                        # Processar resultados
                        docs = []
                        scores = []
                        
                        for item in similar_docs:
                            if isinstance(item, tuple) and len(item) == 2:
                                doc, score = item
                                docs.append(str(doc))
                                scores.append(float(score))
                            else:
                                docs.append(str(item))
                                scores.append(0.8)  # Score padrão
                        
                        avg_score = sum(scores) / len(scores) if scores else 0
                        
                        result["rag_enabled"] = True
                        result["rag_similarity_score"] = round(avg_score, 3)
                        result["rag_cases_found"] = len(docs)
                        result["rag_documents"] = [
                            doc[:200] + "..." if len(doc) > 200 else doc
                            for doc in docs[:3]
                        ]
                        
                        logger.info(f"✅ RAG concluído - Score: {avg_score:.3f}, Casos: {len(docs)}")
                        result["report_source"] = "Pipeline + RAG"
                    else:
                        result["rag_enabled"] = True
                        result["rag_cases_found"] = 0
                        result["report_source"] = "Pipeline Only"
                        logger.info("📋 RAG ativo mas nenhum resultado")
                
            except Exception as rag_error:
                logger.error(f"⚠️ Erro no RAG: {rag_error}")
                result["rag_enabled"] = False
                result["rag_error"] = str(rag_error)
                result["report_source"] = "Pipeline Only"
        else:
            result["rag_enabled"] = False
            result["report_source"] = "Pipeline Only"
        
        # 6. FINALIZAÇÃO
        processing_time = (datetime.now() - start_time).total_seconds()
        result["processing_time_seconds"] = round(processing_time, 2)
        result["sistema_versao"] = "Medical AI v3.1"
        
        # Limpar arquivos temporários
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"🗑️ Arquivo temporário removido: {temp_file}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao remover arquivo: {e}")
        
        logger.info(f"✅ ANÁLISE COMPLETA - Tempo: {processing_time:.2f}s")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ ERRO CRÍTICO: {error_msg}")
        traceback.print_exc()
        
        # Limpar arquivos em caso de erro
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": error_msg,
                "error_type": type(e).__name__,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
                "debug_info": {
                    "patient_info_received": bool(patient_info),
                    "audio_received": audio_data is not None,
                    "image_received": image_data is not None,
                    "pipeline_available": medical_pipeline is not None,
                    "rag_available": rag_service is not None
                }
            }
        )


@app.get("/api/health")
async def health_check():
    """🔍 VERIFICAÇÃO DE SAÚDE DO SISTEMA"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "Medical AI v3.1",
        "services": {}
    }
    
    # Verificar pipeline médico
    if medical_pipeline:
        health_status["services"]["medical_pipeline"] = {
            "status": "✅ Disponível",
            "type": "Complete Medical Pipeline",
            "class": type(medical_pipeline).__name__
        }
    else:
        health_status["services"]["medical_pipeline"] = {
            "status": "❌ Indisponível",
            "error": "Pipeline não carregado"
        }
    
    # Verificar RAG service
    if rag_service:
        try:
            # Tentar obter estatísticas
            stats = {}
            if hasattr(rag_service, 'get_stats'):
                stats = rag_service.get_stats()
            elif hasattr(rag_service, 'obter_estatisticas'):
                stats = rag_service.obter_estatisticas()
            
            health_status["services"]["rag_system"] = {
                "status": "✅ Disponível",
                "type": "RAG Service",
                "class": type(rag_service).__name__,
                "stats": stats
            }
        except Exception as e:
            health_status["services"]["rag_system"] = {
                "status": "⚠️ Parcialmente disponível",
                "error": str(e)
            }
    else:
        health_status["services"]["rag_system"] = {
            "status": "❌ Indisponível",
            "error": "Serviço não encontrado"
        }
    
    # Verificar ambiente
    health_status["environment"] = {
        "openai_api_configured": bool(os.getenv('OPENAI_API_KEY')),
        "python_version": sys.version.split()[0],
        "temp_dir_writable": os.access(tempfile.gettempdir(), os.W_OK)
    }
    
    return health_status


@app.get("/api/rag/search")
async def search_rag_knowledge(
    query: str = Query(..., description="Consulta para buscar na base RAG"),
    top_k: int = Query(5, ge=1, le=20, description="Número de resultados")
):
    """🔍 BUSCAR NA BASE RAG"""
    
    if not rag_service:
        raise HTTPException(status_code=503, detail="Serviço RAG não disponível")
    
    try:
        results = []
        
        # Tentar diferentes métodos de busca
        if hasattr(rag_service, 'search'):
            results = rag_service.search(query, k=top_k)
        elif hasattr(rag_service, 'similarity_search'):
            results = rag_service.similarity_search(query, k=top_k)
        elif hasattr(rag_service, 'query'):
            results = rag_service.query(query, k=top_k)
        elif hasattr(rag_service, 'buscar_documentos_similares'):
            results = rag_service.buscar_documentos_similares(query, k=top_k)
        else:
            raise HTTPException(status_code=501, detail="Método de busca não encontrado no RAG service")
        
        # Processar resultados
        processed_results = []
        for result in results:
            if isinstance(result, tuple) and len(result) == 2:
                doc, score = result
                processed_results.append({
                    "document": str(doc)[:300] + "..." if len(str(doc)) > 300 else str(doc),
                    "similarity_score": float(score)
                })
            else:
                processed_results.append({
                    "document": str(result)[:300] + "..." if len(str(result)) > 300 else str(result),
                    "similarity_score": 0.8
                })
        
        return {
            "success": True,
            "query": query,
            "results": processed_results,
            "total_found": len(processed_results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca RAG: {str(e)}")


@app.get("/")
async def root():
    """🏠 PÁGINA INICIAL"""
    return {
        "message": "Medical AI System - Estrutura Ajustada",
        "version": "3.1",
        "status": "running",
        "services": {
            "pipeline": "Complete Medical Pipeline" if medical_pipeline else "Não disponível",
            "rag": "RAG Service" if rag_service else "Não disponível"
        },
        "endpoints": {
            "analysis": "/api/intelligent-medical-analysis",
            "health": "/api/health",
            "rag_search": "/api/rag/search"
        }
    }


# Tratamento global de exceções
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Tratamento global de erros"""
    logger.error(f"❌ Erro global: {str(exc)}")
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Erro interno do servidor",
            "error_type": type(exc).__name__,
            "error_details": str(exc)[:200],
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Iniciando Medical AI System v3.1...")
    print(f"✅ Complete Medical Pipeline: {'Carregado' if medical_pipeline else 'Não disponível'}")
    print(f"✅ RAG Service: {'Carregado' if rag_service else 'Não disponível'}")
    print("🏗️ Estrutura ajustada para:")
    print("   - services/complete_medical_pipeline.py")
    print("   - services/rag/")
    print("   - Processamento seguro de arquivos binários")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )