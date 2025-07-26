# ============================================================================
# MAIN.PY - SISTEMA MÉDICO COM RAG INTEGRADO
# Versão Corrigida e Otimizada
# ============================================================================

import os
import sys
import traceback
from datetime import datetime
from typing import Optional

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Carregar variáveis de ambiente
load_dotenv()

# Verificar variáveis essenciais
required_env_vars = ['OPENAI_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Variáveis de ambiente faltando: {missing_vars}")
    sys.exit(1)

app = FastAPI(
    title="Medical AI System with RAG", 
    version="2.0",
    description="Sistema de análise médica com IA multimodal e RAG"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importações globais (com tratamento de erro)
multimodal_service = None
rag_service = None

try:
    from app.services.multimodal_ai_service import MultimodalAIService
    multimodal_service = MultimodalAIService()
    print("✅ Serviço Multimodal carregado")
except ImportError as e:
    print(f"❌ Erro ao carregar serviço multimodal: {e}")
    multimodal_service = None

try:
    from app.services.medical_rag_service import MedicalRAGService
    rag_service = MedicalRAGService()
    print("✅ Serviço RAG carregado")
except ImportError as e:
    print(f"⚠️ RAG service não encontrado: {e}")
    rag_service = None


@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis_with_rag(
    patient_info: str = Form(...),
    audio_data: UploadFile = File(None),
    image_data: UploadFile = File(None)
):
    """🚀 ENDPOINT PRINCIPAL - ANÁLISE MÉDICA COMPLETA COM RAG"""
    
    print(f"🚀 NOVA ANÁLISE INICIADA - Paciente: {patient_info[:50]}...")
    start_time = datetime.now()
    
    try:
        # Validação inicial
        if not multimodal_service:
            raise HTTPException(
                status_code=503, 
                detail="Serviço multimodal não disponível"
            )
        
        # 1. PROCESSAMENTO DE ARQUIVOS
        audio_bytes = None
        image_path = None
        
        if audio_data and audio_data.filename:
            audio_bytes = await audio_data.read()
            print(f"🎤 Áudio recebido: {len(audio_bytes)} bytes")
        
        if image_data and image_data.filename:
            # Salvar imagem temporariamente
            temp_dir = "temp_images"
            os.makedirs(temp_dir, exist_ok=True)
            image_path = os.path.join(temp_dir, f"img_{int(datetime.now().timestamp())}.jpg")
            
            with open(image_path, "wb") as f:
                f.write(await image_data.read())
            print(f"🖼️ Imagem salva: {image_path}")
        
        # 2. ANÁLISE MULTIMODAL BASE
        print("🔄 Executando análise multimodal...")
        
        multimodal_result = await multimodal_service.analyze_multimodal(
            patient_info=patient_info,
            audio_bytes=audio_bytes,
            image_path=image_path
        )
        
        if multimodal_result.get("status") == "error":
            print(f"❌ Erro na análise multimodal: {multimodal_result.get('error')}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": multimodal_result.get("error"),
                    "source": "multimodal_analysis"
                }
            )
        
        # 3. PREPARAR RESULTADO BASE
        result = {
            "success": True,
            "timestamp": start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "patient_info": patient_info,
            "transcription": multimodal_result.get("transcription", ""),
            "patient_data": multimodal_result.get("patient_data", {}),
            "medical_report": multimodal_result.get("medical_report", ""),
            "image_analysis": multimodal_result.get("image_analysis", ""),
            "analysis": multimodal_result.get("analysis", ""),
            "multimodal_success": True
        }
        
        print("✅ Análise multimodal concluída")
        
        # 4. INTEGRAÇÃO RAG (se disponível)
        if rag_service:
            try:
                print("🔄 Iniciando análise RAG...")
                
                # Usar a transcrição para buscar casos similares
                transcription = result.get("transcription", "")
                patient_data = result.get("patient_data", {})
                
                if transcription or patient_data:
                    # Buscar contexto similar
                    search_query = transcription or patient_info
                    similar_docs = rag_service.search_similar_documents(search_query, k=5)
                    
                    if similar_docs:
                        similarity_scores = [score for _, score in similar_docs]
                        avg_score = sum(similarity_scores) / len(similarity_scores)
                        
                        result["rag_enabled"] = True
                        result["rag_similarity_score"] = avg_score
                        result["rag_cases_found"] = len(similar_docs)
                        result["rag_documents"] = [doc[:200] + "..." for doc, _ in similar_docs[:3]]
                        
                        print(f"✅ RAG concluído - Score médio: {avg_score:.3f}, Casos: {len(similar_docs)}")
                        
                        # Se temos boa similaridade, enriquecer o relatório
                        if avg_score > 0.6:
                            enhanced_report = await _enhance_report_with_rag(
                                result["medical_report"], 
                                similar_docs, 
                                rag_service
                            )
                            result["medical_report_enhanced"] = enhanced_report
                            result["report_source"] = "RAG Enhanced"
                        else:
                            result["report_source"] = "Multimodal + RAG Context"
                    else:
                        result["rag_enabled"] = True
                        result["rag_cases_found"] = 0
                        result["report_source"] = "Multimodal Only"
                        print("📋 RAG ativo mas nenhum caso similar encontrado")
                
            except Exception as rag_error:
                print(f"⚠️ Erro no RAG: {str(rag_error)}")
                result["rag_enabled"] = False
                result["rag_error"] = str(rag_error)
                result["report_source"] = "Multimodal Only"
        else:
            result["rag_enabled"] = False
            result["report_source"] = "Multimodal Only"
            print("⚠️ RAG não disponível")
        
        # 5. FINALIZAÇÃO
        processing_time = (datetime.now() - start_time).total_seconds()
        result["processing_time_seconds"] = round(processing_time, 2)
        result["sistema_versao"] = "Medical AI v2.0"
        
        # Limpar arquivos temporários
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        
        print(f"✅ ANÁLISE COMPLETA FINALIZADA - Tempo: {processing_time:.2f}s")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERRO CRÍTICO: {error_msg}")
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": error_msg,
                "error_type": type(e).__name__,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds()
            }
        )


async def _enhance_report_with_rag(base_report: str, similar_docs: list, rag_service) -> str:
    """Enriquece o relatório base com contexto do RAG"""
    try:
        context = "\n".join([doc for doc, _ in similar_docs[:3]])
        
        # Usar o RAG service para gerar versão melhorada
        enhanced = rag_service.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um médico especialista. Enriqueça o relatório base com insights do contexto médico relevante."
                },
                {
                    "role": "user",
                    "content": f"""
RELATÓRIO BASE:
{base_report}

CONTEXTO MÉDICO SIMILAR:
{context}

Enriqueça o relatório base incorporando insights relevantes do contexto, mantendo a estrutura original mas adicionando detalhes clínicos pertinentes.
"""
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        return enhanced.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Erro ao enriquecer relatório: {e}")
        return base_report


@app.get("/api/health")
async def health_check():
    """🔍 VERIFICAÇÃO DE SAÚDE DO SISTEMA"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "Medical AI v2.0",
        "services": {}
    }
    
    # Verificar serviço multimodal
    if multimodal_service:
        health_status["services"]["multimodal_ai"] = {
            "status": "✅ Disponível",
            "class": type(multimodal_service).__name__
        }
    else:
        health_status["services"]["multimodal_ai"] = {
            "status": "❌ Indisponível",
            "error": "Serviço não carregado"
        }
    
    # Verificar serviço RAG
    if rag_service:
        try:
            rag_stats = rag_service.get_rag_stats()
            health_status["services"]["rag_system"] = {
                "status": "✅ Disponível",
                "stats": rag_stats
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
    
    # Verificar variáveis de ambiente
    health_status["environment"] = {
        "openai_api_configured": bool(os.getenv('OPENAI_API_KEY')),
        "python_version": sys.version.split()[0]
    }
    
    return health_status


@app.get("/api/rag/search")
async def search_rag_knowledge(
    query: str = Query(..., description="Consulta para buscar na base de conhecimento"),
    top_k: int = Query(5, ge=1, le=20, description="Número de resultados")
):
    """🔍 BUSCAR NA BASE DE CONHECIMENTO RAG"""
    
    if not rag_service:
        raise HTTPException(status_code=503, detail="Serviço RAG não disponível")
    
    try:
        results = rag_service.search_similar_documents(query, k=top_k)
        
        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "document": doc[:300] + "..." if len(doc) > 300 else doc,
                    "similarity_score": float(score)
                }
                for doc, score in results
            ],
            "total_found": len(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca RAG: {str(e)}")


@app.get("/api/rag/stats")
async def get_rag_statistics():
    """📊 ESTATÍSTICAS DO SISTEMA RAG"""
    
    if not rag_service:
        raise HTTPException(status_code=503, detail="Serviço RAG não disponível")
    
    try:
        stats = rag_service.get_rag_stats()
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")


@app.get("/")
async def root():
    """🏠 PÁGINA INICIAL"""
    return {
        "message": "Medical AI System with RAG",
        "version": "2.0",
        "status": "running",
        "endpoints": {
            "analysis": "/api/intelligent-medical-analysis",
            "health": "/api/health",
            "rag_search": "/api/rag/search",
            "rag_stats": "/api/rag/stats"
        }
    }


# Tratamento global de exceções
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Tratamento global de erros"""
    print(f"❌ Erro não tratado: {str(exc)}")
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Erro interno do servidor",
            "error_type": type(exc).__name__,
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Iniciando Medical AI System...")
    print(f"✅ Multimodal Service: {'Carregado' if multimodal_service else 'Não disponível'}")
    print(f"✅ RAG Service: {'Carregado' if rag_service else 'Não disponível'}")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=5003, 
        reload=False,
        log_level="info"
    )