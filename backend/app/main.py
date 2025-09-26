import sys
import os
from datetime import datetime
import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging
import traceback

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Verificar e adicionar path do backend
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Configuração
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID') 
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

logger.info("Verificando configurações...")
logger.info(f"OPENAI_API_KEY: {'Configurado' if OPENAI_API_KEY else 'Ausente'}")
logger.info(f"AWS_ACCESS_KEY_ID: {'Configurado' if AWS_ACCESS_KEY_ID else 'Ausente'}")
logger.info(f"AWS_SECRET_ACCESS_KEY: {'Configurado' if AWS_SECRET_ACCESS_KEY else 'Ausente'}")
logger.info(f"AWS_REGION: {AWS_REGION}")

# Importar serviços
transcription_service = None
llm_service = None
textract_service = None

try:
    from services.transcription_service import TranscriptionService
    transcription_service = TranscriptionService()
    logger.info("TranscriptionService (Whisper) carregado")
except Exception as e:
    logger.error(f"Erro ao carregar TranscriptionService: {e}")

try:
    from services.llm import InterpretadorLLM
    llm_service = InterpretadorLLM()
    logger.info("InterpretadorLLM carregado")
except Exception as e:
    logger.error(f"Erro ao carregar InterpretadorLLM: {e}")

try:
    from services.textract_service import TextractService
    textract_service = TextractService()
    logger.info("TextractService carregado")
except Exception as e:
    logger.error(f"Erro ao carregar TextractService: {e}")

app = FastAPI(
    title="PREVIDAS - Sistema de Telemedicina",
    description="Consultas com Whisper + Análise de exames com Textract",
    version="6.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Servir arquivos estáticos
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Funções auxiliares
async def _validate_audio_quality(audio_bytes: bytes) -> dict:
    """Valida qualidade básica do áudio"""
    try:
        from pydub import AudioSegment
        import io
        
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
        
        quality_score = 100
        issues = []
        
        duration = audio_segment.duration_seconds
        if duration < 5:
            quality_score -= 40
            issues.append(f"Audio muito curto ({duration:.1f}s)")
        elif duration < 30:
            quality_score -= 20
            issues.append(f"Audio curto ({duration:.1f}s)")
        
        if audio_segment.dBFS < -50:
            quality_score -= 25
            issues.append("Volume muito baixo")
        elif audio_segment.dBFS < -30:
            quality_score -= 10
            issues.append("Volume baixo")
        
        if audio_segment.frame_rate < 16000:
            quality_score -= 15
            issues.append("Baixa qualidade de audio")
        
        return {
            'quality_score': max(quality_score, 0),
            'duration_seconds': duration,
            'volume_dbfs': audio_segment.dBFS,
            'sample_rate': audio_segment.frame_rate,
            'channels': audio_segment.channels,
            'file_size_bytes': len(audio_bytes),
            'issues': issues,
            'is_good_quality': quality_score >= 70
        }
        
    except Exception as e:
        return {
            'quality_score': 0,
            'error': str(e),
            'issues': ["Erro na analise do audio"],
            'is_good_quality': False
        }

def validate_required_services(service_names: list):
    """Valida se os serviços necessários estão disponíveis"""
    services_map = {
        'transcription': transcription_service,
        'llm': llm_service,
        'textract': textract_service
    }
    
    missing_services = []
    for service_name in service_names:
        if service_name in services_map and services_map[service_name] is None:
            missing_services.append(service_name)
    
    return missing_services

def _generate_consultation_recommendations(quality_analysis, transcription_success, transcription_analysis):
    """Gera recomendações para melhorar futuras consultas"""
    recommendations = []
    
    if not transcription_success:
        recommendations.extend([
            "Verifique se o audio foi capturado corretamente",
            "Certifique-se de que a captura de audio do sistema esta habilitada",
            "Teste a gravacao antes da consulta"
        ])
    
    if quality_analysis.get('quality_score', 100) < 70:
        if 'Volume muito baixo' in quality_analysis.get('issues', []):
            recommendations.append("Aumente o volume da videochamada antes de gravar")
        
        if 'Audio muito curto' in str(quality_analysis.get('issues', [])):
            recommendations.append("Grave por mais tempo para obter melhor transcricao")
        
        if 'Baixa qualidade de audio' in quality_analysis.get('issues', []):
            recommendations.append("Use fones de ouvido ou melhore a conexao de internet")
    
    if transcription_analysis.get('word_count', 0) < 50:
        recommendations.append("Transcricao muito curta - verifique se a consulta foi gravada completamente")
    
    if not transcription_analysis.get('has_medical_content', False):
        recommendations.append("Conteudo medico nao detectado - verifique se e uma consulta medica")
    
    if not recommendations:
        recommendations.append("Processamento realizado com sucesso")
    
    return recommendations

# ENDPOINT PRINCIPAL - CONSULTAS
@app.post("/api/process-consultation")
async def process_consultation(
    consultation_audio: UploadFile = File(...),
    patient_info: str = Form(default=""),
    consultation_type: str = Form(default="telemedicina"),
    audio_quality_check: bool = Form(default=True),
    processing_mode: str = Form(default="batch"),
    audio_duration_seconds: str = Form(default="0")
):
    """Processa audio completo da consulta de telemedicina"""
    try:
        logger.info("CONSULTA: Iniciando processamento")
        start_time = datetime.now()
        
        # Validar serviços necessários
        missing_services = validate_required_services(['transcription'])
        if missing_services:
            return JSONResponse(
                status_code=503,
                content={
                    'success': False,
                    'error': f"Servicos nao disponiveis: {', '.join(missing_services)}",
                    'transcription': 'Servico nao disponivel',
                    'consultation_data': {}
                }
            )
        
        # Ler arquivo de áudio
        audio_data = await consultation_audio.read()
        
        logger.info(f"Arquivo recebido: {consultation_audio.filename}")
        logger.info(f"Tamanho: {len(audio_data)} bytes ({len(audio_data)/1024/1024:.2f} MB)")
        if audio_duration_seconds != "0":
            logger.info(f"Duracao informada: {audio_duration_seconds}s")
        
        # Validação de qualidade
        quality_analysis = {}
        if audio_quality_check:
            quality_analysis = await _validate_audio_quality(audio_data)
            
            logger.info(f"Qualidade do audio:")
            logger.info(f"Score: {quality_analysis['quality_score']}/100")
            logger.info(f"Duracao: {quality_analysis.get('duration_seconds', 0):.1f}s")
            logger.info(f"Volume: {quality_analysis.get('volume_dbfs', 0):.1f} dBFS")
            
            if quality_analysis['issues']:
                logger.warning(f"Problemas: {', '.join(quality_analysis['issues'])}")
        
        # Transcrição com Whisper
        logger.info("Iniciando transcricao com Whisper...")
        
        transcription_result = await transcription_service.transcribe_audio(audio_data)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Processar resultado
        transcription_text = ""
        transcription_success = False
        transcription_error = None
        
        if transcription_result and transcription_result.strip():
            transcription_text = transcription_result.strip()
            transcription_success = True
            logger.info(f"Transcricao concluida: {len(transcription_text)} caracteres")
        else:
            transcription_error = 'Transcricao vazia ou falhou'
            logger.error(f"Erro na transcricao: {transcription_error}")
        
        # Análise da transcrição
        transcription_analysis = {}
        if transcription_text:
            words = transcription_text.split()
            transcription_analysis = {
                'word_count': len(words),
                'character_count': len(transcription_text),
                'estimated_duration_minutes': len(words) / 150,
                'has_medical_content': any(term in transcription_text.lower() for term in [
                    'sintoma', 'dor', 'medicamento', 'exame', 'diagnostico', 'tratamento',
                    'pressao', 'diabetes', 'consulta', 'paciente', 'medico', 'doutor'
                ])
            }
        
        # Qualidade geral
        overall_quality = 'good'
        if not transcription_success:
            overall_quality = 'failed'
        elif quality_analysis.get('quality_score', 100) < 50:
            overall_quality = 'poor'
        elif quality_analysis.get('quality_score', 100) < 70:
            overall_quality = 'medium'
        
        # Recomendações
        recommendations = _generate_consultation_recommendations(
            quality_analysis, transcription_success, transcription_analysis
        )
        
        logger.info(f"Processamento concluido em {processing_time:.2f}s")
        logger.info(f"Transcricao: {'Sucesso' if transcription_success else 'Falha'}")
        logger.info(f"Qualidade geral: {overall_quality}")
        
        # Resposta
        return {
            'success': transcription_success,
            'service_type': 'consulta_telemedicina',
            'transcription': transcription_text,
            'consultation_data': {
                'full_transcription': transcription_text,
                'transcription_success': transcription_success,
                'transcription_method': 'whisper_pos_processamento',
                'audio_source': 'browser_capture',
                'processing_quality': {
                    'overall_quality': overall_quality,
                    'transcription_length': len(transcription_text),
                    'processing_time_seconds': processing_time,
                    'audio_quality_score': quality_analysis.get('quality_score', 0),
                    'recommendations': recommendations
                }
            },
            'technical_details': {
                'processing_method': 'whisper_single_stream',
                'processing_time_seconds': processing_time,
                'audio_analysis': quality_analysis,
                'transcription_analysis': transcription_analysis,
                'transcription_error': transcription_error,
                'file_info': {
                    'filename': consultation_audio.filename,
                    'size_bytes': len(audio_data),
                    'size_mb': round(len(audio_data) / 1024 / 1024, 2)
                },
                'processing_mode': processing_mode
            },
            'patient_info': patient_info,
            'timestamp': datetime.now().isoformat(),
            'consultation_summary': {
                'duration_estimated_minutes': transcription_analysis.get('estimated_duration_minutes', 0),
                'word_count': transcription_analysis.get('word_count', 0),
                'has_medical_content': transcription_analysis.get('has_medical_content', False),
                'quality_assessment': overall_quality
            }
        }
        
    except Exception as e:
        logger.error(f"Erro geral no processamento: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': str(e),
                'transcription': 'Erro no processamento',
                'consultation_data': {},
                'technical_error': True
            }
        )

# ENDPOINT PARA EXAMES
@app.post("/api/process-exams")
async def process_exams(
    exams: list[UploadFile] = File(...),
    patient_context: str = Form(default=""),
    service_type: str = Form(default="exames")
):
    """Processamento de múltiplos exames médicos com Textract + LLM"""
    try:
        logger.info(f"Iniciando processamento de exames: {len(exams)} arquivo(s)")
        
        # Validar serviços
        missing_services = validate_required_services(['textract', 'llm'])
        if missing_services:
            error_msg = f"Servicos nao disponiveis: {', '.join(missing_services)}"
            logger.error(error_msg)
            
            config_issues = []
            if not AWS_ACCESS_KEY_ID:
                config_issues.append("AWS_ACCESS_KEY_ID nao configurado")
            if not AWS_SECRET_ACCESS_KEY:
                config_issues.append("AWS_SECRET_ACCESS_KEY nao configurado")
            if not OPENAI_API_KEY:
                config_issues.append("OPENAI_API_KEY nao configurado")
            
            return JSONResponse(
                status_code=503,
                content={
                    'success': False,
                    'error': error_msg,
                    'missing_services': missing_services,
                    'config_issues': config_issues,
                    'files_processed': 0,
                    'extracted_texts': [],
                    'llm_interpretation': 'Servicos nao disponiveis'
                }
            )
        
        if not exams:
            return JSONResponse(
                status_code=400,
                content={
                    'success': False,
                    'error': 'Nenhum exame fornecido',
                    'files_processed': 0,
                    'extracted_texts': [],
                    'llm_interpretation': 'Nenhum arquivo recebido'
                }
            )
        
        logger.info(f"Contexto do paciente: {patient_context[:100]}...")
        
        extracted_texts = []
        processing_errors = []
        all_extracted_text = ""
        
        # Extração com Textract
        logger.info("Iniciando extracao de texto com Textract...")
        for i, exam in enumerate(exams):
            try:
                logger.info(f"Processando exame {i+1}/{len(exams)}: {exam.filename}")
                exam_data = await exam.read()
                
                if len(exam_data) == 0:
                    logger.warning(f"Arquivo vazio: {exam.filename}")
                    processing_errors.append({
                        'filename': exam.filename,
                        'error': 'Arquivo vazio',
                        'stage': 'file_validation'
                    })
                    continue
                
                logger.info(f"Arquivo {exam.filename}: {len(exam_data)} bytes")
                
                extraction_result = await textract_service.extrair_texto(exam_data, exam.filename)
                
                if extraction_result.get('success', False):
                    extracted_text = extraction_result.get('extracted_text', '').strip()
                    
                    if extracted_text:
                        all_extracted_text += f"\n\n=== EXAME: {exam.filename} ===\n{extracted_text}"
                        
                        extracted_texts.append({
                            'filename': exam.filename,
                            'text': extracted_text,
                            'text_length': len(extracted_text),
                            'confidence': extraction_result.get('confidence', 0),
                            'success': True
                        })
                        logger.info(f"{exam.filename}: {len(extracted_text)} caracteres extraidos")
                    else:
                        logger.warning(f"Texto vazio extraido de {exam.filename}")
                        processing_errors.append({
                            'filename': exam.filename,
                            'error': 'Nenhum texto extraido',
                            'stage': 'textract_extraction'
                        })
                else:
                    error_msg = extraction_result.get('error', 'Erro desconhecido no Textract')
                    logger.error(f"{exam.filename}: {error_msg}")
                    processing_errors.append({
                        'filename': exam.filename,
                        'error': error_msg,
                        'stage': 'textract_extraction'
                    })
                    
            except Exception as e:
                error_msg = f"Erro no processamento: {str(e)}"
                logger.error(f"{exam.filename}: {error_msg}")
                processing_errors.append({
                    'filename': exam.filename,
                    'error': error_msg,
                    'stage': 'file_processing'
                })
        
        # Interpretação com LLM
        combined_llm_interpretation = "Nenhuma interpretacao disponivel"
        llm_interpretations = []
        
        if all_extracted_text.strip():
            try:
                logger.info(f"Iniciando interpretacao medica com LLM ({len(all_extracted_text)} caracteres)...")
                
                llm_result = await llm_service.interpretar_exame_para_frontend(
                    all_extracted_text,
                    f"exames_multiplos_{len(exams)}_arquivos",
                    {
                        "additional_info": patient_context, 
                        "service_type": service_type,
                        "total_files": len(exams)
                    }
                )
                
                if llm_result.get('success', False):
                    llm_analysis = llm_result.get('llm_analysis', {})
                    combined_llm_interpretation = llm_analysis.get('clinical_analysis', 'Analise realizada')
                    
                    llm_interpretations.append({
                        'scope': 'consolidated_analysis',
                        'interpretation': combined_llm_interpretation,
                        'model_used': llm_result.get('model_used', 'gpt-4o'),
                        'complete': llm_result.get('interpretation_complete', False),
                        'exam_type': llm_analysis.get('exam_type', 'Exame Clinico'),
                        'key_findings': llm_analysis.get('key_findings', [])
                    })
                    logger.info("Interpretacao medica concluida com sucesso")
                else:
                    error_msg = llm_result.get('error', 'Erro na interpretacao LLM')
                    logger.error(f"Erro LLM: {error_msg}")
                    processing_errors.append({
                        'filename': 'llm_service',
                        'error': error_msg,
                        'stage': 'llm_interpretation'
                    })
                    combined_llm_interpretation = f"Erro na interpretacao: {error_msg}"
                    
            except Exception as e:
                error_msg = f"Erro na interpretacao LLM: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                processing_errors.append({
                    'filename': 'llm_service',
                    'error': error_msg,
                    'stage': 'llm_interpretation'
                })
                combined_llm_interpretation = f"Erro na interpretacao: {error_msg}"
        else:
            logger.warning("Nenhum texto extraido para interpretacao LLM")
            combined_llm_interpretation = "Nenhum texto foi extraido dos exames para interpretacao"
        
        # Resposta
        success = len(extracted_texts) > 0
        
        response_data = {
            'success': success,
            'service_type': service_type,
            'files_processed': len(extracted_texts),
            'extracted_texts': [item['text'] for item in extracted_texts],
            'all_extracted_text': all_extracted_text,
            'extraction_details': extracted_texts,
            'llm_interpretation': combined_llm_interpretation,
            'llm_analysis': llm_interpretations,
            'processing_summary': {
                'total_exams': len(exams),
                'successful_extractions': len(extracted_texts),
                'failed_extractions': len([e for e in processing_errors if e.get('stage') == 'textract_extraction']),
                'total_text_extracted': len(all_extracted_text),
                'llm_analysis_success': len(llm_interpretations) > 0 and 'Erro' not in combined_llm_interpretation
            },
            'processing_errors': processing_errors,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Processamento concluido: {len(extracted_texts)}/{len(exams)} arquivos processados")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Erro geral no processamento de exames: {e}")
        logger.error(traceback.format_exc())
        
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': f"Erro interno do servidor: {str(e)}",
                'files_processed': 0,
                'extracted_texts': [],
                'llm_interpretation': 'Processamento falhou',
                'processing_errors': [{'error': str(e), 'stage': 'general_processing'}],
                'timestamp': datetime.now().isoformat()
            }
        )

# ENDPOINTS AUXILIARES
@app.get("/")
async def root():
    """Página inicial"""
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    
    return {
        "service": "PREVIDAS - Sistema de Telemedicina",
        "version": "6.1.0",
        "status": "running",
        "focus": "Pos-processamento otimizado com Whisper",
        "endpoints": [
            "/api/process-consultation (POST)",
            "/api/process-exams (POST)", 
            "/api/health (GET)"
        ],
        "features": [
            "Consultas com pos-processamento Whisper otimizado",
            "Analise de exames com Textract + LLM", 
            "Validacao de qualidade de audio",
            "Interface web integrada"
        ]
    }

@app.get("/api/health")
async def health():
    """Health check"""
    
    config_status = {
        'openai_api_key': bool(OPENAI_API_KEY),
        'aws_access_key': bool(AWS_ACCESS_KEY_ID),
        'aws_secret_key': bool(AWS_SECRET_ACCESS_KEY),
        'aws_region': AWS_REGION
    }
    
    services_status = {}
    
    if transcription_service:
        services_status['transcription_service'] = "ready"
    else:
        services_status['transcription_service'] = "not_available"
    
    if textract_service:
        services_status['textract_service'] = "ready"
    else:
        services_status['textract_service'] = "not_available"
    
    if llm_service:
        services_status['llm_service'] = "ready"
    else:
        services_status['llm_service'] = "not_available"
    
    critical_services = ['transcription_service']
    critical_ready = all(services_status.get(service, '') == 'ready' for service in critical_services)
    
    overall_status = "healthy" if critical_ready else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "services": services_status,
        "configuration": config_status,
        "capabilities": {
            "consultation_transcription": bool(transcription_service),
            "exam_analysis": bool(textract_service and llm_service),
            "audio_quality_validation": True,
            "post_processing_optimized": True
        },
        "system_focus": "Pos-processamento com Whisper + analise de exames",
        "missing_configs": [
            key for key, value in config_status.items() 
            if not value and key != 'aws_region'
        ]
    }

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("PREVIDAS - Sistema de Telemedicina v6.1.0")
    logger.info("=" * 60)
    logger.info("FOCO: Pos-processamento otimizado com Whisper")
    logger.info("RECURSOS:")
    logger.info("   • Captura de audio otimizada para pos-processamento")
    logger.info("   • Transcricao com Whisper (OpenAI)")
    logger.info("   • Analise de exames com Textract + LLM")
    logger.info("   • Validacao de qualidade de audio")
    logger.info("   • Interface web integrada")
    
    services_loaded = sum([
        bool(transcription_service),
        bool(llm_service),
        bool(textract_service)
    ])
    
    logger.info(f"Servicos carregados: {services_loaded}/3")
    
    if transcription_service:
        logger.info("   Whisper (OpenAI) - Transcricoes")
    else:
        logger.warning("   Whisper nao disponivel")
    
    if textract_service and llm_service:
        logger.info("   Textract + LLM - Analise de exames")
    else:
        logger.warning("   Textract/LLM limitados")
    
    logger.info("=" * 60)
    logger.info("Iniciando servidor...")                                                                                                                                                                                    
    logger.info("Interface: http://localhost:8000")
    logger.info("API Health: http://localhost:8000/api/health")
    logger.info("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)                                                                                                                                                                                                       