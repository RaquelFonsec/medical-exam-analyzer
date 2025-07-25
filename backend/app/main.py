# ============================================================================
# ENDPOINT PRINCIPAL INTEGRADO COM RAG
# Adicionar ao arquivo main.py
# ============================================================================

from dotenv import load_dotenv
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import traceback

# Carregar variáveis de ambiente
load_dotenv()

app = FastAPI(title="Medical AI System with RAG", version="2.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis_with_rag(
    patient_info: str = Form(...),
    audio_data: UploadFile = File(None),
    image_data: UploadFile = File(None)
):
    """🚀 ANÁLISE MÉDICA COMPLETA COM RAG INTEGRADO"""
    print(f"🚀 ANÁLISE COMPLETA INICIADA: {patient_info}")
    
    try:
        # 1. ANÁLISE MULTIMODAL PADRÃO
        from app.services.multimodal_ai_service import multimodal_ai_service
        
        audio_bytes = None
        if audio_data and audio_data.filename:
            audio_bytes = await audio_data.read()
            print(f"🎤 Áudio processado: {len(audio_bytes)} bytes")
        
        # Executar análise base
        result = await multimodal_ai_service.analyze_multimodal(patient_info, audio_bytes, None)
        
        print("main.py - Análise multimodal concluída:", result)
        
        if not result.get('success'):
            return result
        
        print(f"✅ Análise base concluída - Benefício: {result.get('beneficio', 'N/A')}")
        
        # 2. INTEGRAÇÃO RAG PARA MELHORAR O LAUDO
        try:
            # Importar RAG service (pode falhar se não estiver disponível)
            try:
                from app.services.rag.medical_rag_service import medical_rag_service
                rag_available = True
            except ImportError:
                print("⚠️ RAG service não encontrado")
                rag_available = False
            
            if rag_available:
                print("🔄 Iniciando análise RAG...")
                
                # Preparar dados para RAG
                transcription = result.get('transcription', '')
                especialidade = result.get('especialidade', 'Clínica Geral')
                
                # Buscar casos similares
                rag_response = medical_rag_service.generate_rag_response(
                    patient_info, 
                    transcription
                )
                
                if rag_response.get('success'):
                    similarity_score = rag_response.get('top_similarity_score', 0)
                    cases_used = rag_response.get('similar_cases_count', 0)
                    
                    print(f"✅ RAG concluído - Score: {similarity_score:.3f}, Casos: {cases_used}")
                    
                    # Integrar resultados RAG
                    result['laudo_medico_original'] = result['laudo_medico']
                    result['rag_enabled'] = True
                    result['rag_similarity_score'] = similarity_score
                    result['rag_cases_used'] = cases_used
                    
                    # Se RAG tem boa qualidade, usar como laudo principal
                    if similarity_score > 0.6:
                        result['laudo_medico'] = rag_response['response']
                        result['laudo_source'] = 'RAG Aprimorado'
                        print("🎯 Usando laudo RAG como principal")
                    else:
                        result['laudo_medico_rag'] = rag_response['response']
                        result['laudo_source'] = 'Sistema + RAG Complementar'
                        print("📋 RAG como complemento")
                
                else:
                    print("⚠️ RAG falhou, usando laudo padrão")
                    result['rag_enabled'] = False
                    result['rag_error'] = rag_response.get('error', 'Erro desconhecido')
                    result['laudo_source'] = 'Sistema Padrão'
            
            else:
                print("⚠️ RAG não disponível, usando sistema padrão")
                result['rag_enabled'] = False
                result['laudo_source'] = 'Sistema Padrão'
        
        except Exception as rag_error:
            print(f"⚠️ Erro no RAG: {str(rag_error)}")
            result['rag_enabled'] = False
            result['rag_error'] = str(rag_error)
            result['laudo_source'] = 'Sistema Padrão'
        
        # 3. ENRIQUECER RESPOSTA FINAL
        result['sistema_versao'] = 'Medical AI v2.0 com RAG'
        result['timestamp_final'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"✅ ANÁLISE COMPLETA FINALIZADA - Fonte: {result.get('laudo_source', 'N/A')}")
        
        return result
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {str(e)}")
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "transcription": f"Erro: {str(e)}",
            "anamnese": f"Erro durante análise: {str(e)}",
            "laudo_medico": f"Erro durante geração: {str(e)}",
            "rag_enabled": False,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

@app.get("/api/health")
async def health_check():
    """Verificar saúde do sistema"""
    try:
        from app.services.multimodal_ai_service import multimodal_ai_service
        multimodal_status = "✅ Disponível"
    except:
        multimodal_status = "❌ Indisponível"
    
    try:
        from app.services.rag.medical_rag_service import medical_rag_service
        rag_status = "✅ Disponível"
        rag_chunks = len(medical_rag_service.chunks) if medical_rag_service.chunks else 0
    except:
        rag_status = "❌ Indisponível"
        rag_chunks = 0
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "multimodal_ai": multimodal_status,
            "rag_system": rag_status,
            "rag_knowledge_base": f"{rag_chunks} chunks"
        },
        "version": "Medical AI v2.0"
    }

@app.post("/api/rag/add-documents")
async def add_documents_to_rag(documents: list = Form(...)):
    """Adicionar documentos à base RAG"""
    try:
        from app.services.rag.medical_rag_service import medical_rag_service
        
        medical_rag_service.add_documents_to_knowledge_base(documents)
        
        return {
            "success": True,
            "message": f"Adicionados {len(documents)} documentos",
            "total_chunks": len(medical_rag_service.chunks),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/rag/search")
async def search_rag_knowledge(query: str, top_k: int = 5):
    """Buscar na base de conhecimento RAG"""
    try:
        from app.services.rag.medical_rag_service import medical_rag_service
        
        results = medical_rag_service.search_similar_cases(query, top_k)
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total_found": len(results),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003, reload=True)
