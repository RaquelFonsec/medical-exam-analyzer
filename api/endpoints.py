# api/endpoints.py
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from typing import Optional
import logging
from datetime import datetime
from services.audio_mixer import AudioMixerService
from services.transcription import TranscricaoService

logger = logging.getLogger(__name__)

# Instâncias dos serviços
audio_mixer = AudioMixerService()
transcricao_service = TranscricaoService()

async def dual_stream_audio_endpoint(
    patient_info: str = Form(default=""),
    doctor_audio: UploadFile = File(...),
    patient_audio: UploadFile = File(...),
    recording_metadata: Optional[str] = Form(None)
):
    """
    ENDPOINT PRINCIPAL: Processamento de dois streams de áudio simultâneos
    
    Fluxo:
    1. Recebe dois arquivos de áudio separados
    2. Mixa os áudios com AudioMixerService
    3. Transcreve o áudio mixado com Whisper
    4. Analisa com GPT para separar falantes
    5. Retorna resultado estruturado
    """
    start_time = datetime.now()
    
    try:
        logger.info("🎯 DUAL STREAM: Iniciando processamento")
        
        # Validar arquivos de entrada
        if not doctor_audio.filename or not patient_audio.filename:
            raise HTTPException(
                status_code=400, 
                detail="Ambos os arquivos de áudio são obrigatórios"
            )
        
        # Decodificar metadados se fornecidos
        metadata = {}
        if recording_metadata:
            try:
                import json
                metadata = json.loads(recording_metadata)
                logger.info(f"Metadados recebidos: {metadata}")
            except Exception as e:
                logger.warning(f"Erro ao decodificar metadados: {e}")
        
        # ETAPA 1: Ler arquivos de áudio
        logger.info("ETAPA 1: Lendo arquivos de áudio...")
        doctor_audio_data = await doctor_audio.read()
        patient_audio_data = await patient_audio.read()
        
        logger.info(f"Áudio médico: {len(doctor_audio_data)} bytes")
        logger.info(f"Áudio paciente: {len(patient_audio_data)} bytes")
        
        # Verificar se os arquivos não estão vazios
        if len(doctor_audio_data) == 0 or len(patient_audio_data) == 0:
            return {
                'success': False,
                'error': 'Um ou ambos os arquivos de áudio estão vazios',
                'transcription': '',
                'medical_conversation': {}
            }
        
        # ETAPA 2: Mixar áudios
        logger.info("ETAPA 2: Mixando áudios...")
        mix_result = await audio_mixer.process_dual_streams(
            doctor_audio_data, 
            patient_audio_data,
            doctor_audio.filename, 
            patient_audio.filename
        )
        
        if not mix_result['success']:
            return {
                'success': False,
                'error': f"Erro na mixagem: {mix_result['error']}",
                'transcription': '',
                'medical_conversation': {}
            }
        
        logger.info("Mixagem concluída com sucesso")
        
        # ETAPA 3: Transcrever áudio mixado
        logger.info("ETAPA 3: Transcrevendo áudio mixado...")
        
        # Ler o áudio mixado
        with open(mix_result['mixed_audio_path'], 'rb') as f:
            mixed_audio_bytes = f.read()
        
        # Transcrever com o serviço existente
        transcricao_result = await transcricao_service.transcrever_audio_com_diarizacao(
            mixed_audio_bytes, 
            "mixed_audio.wav", 
            metadata
        )
        
        if not transcricao_result['sucesso']:
            return {
                'success': False,
                'error': f"Erro na transcrição: {transcricao_result.get('erro', 'Erro desconhecido')}",
                'transcription': '',
                'medical_conversation': {}
            }
        
        logger.info("Transcrição concluída com sucesso")
        
        # ETAPA 4: Analisar qualidade do áudio final
        audio_quality = await audio_mixer.analyze_audio_quality(mix_result['mixed_audio_path'])
        
        # ETAPA 5: Preparar resposta estruturada
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            'success': True,
            'processing_method': 'dual_stream_mixed',
            'transcription': transcricao_result.get('transcricao', ''),
            'medical_conversation': {
                'doctor_text': transcricao_result.get('medico', ''),
                'patient_text': transcricao_result.get('paciente', ''),
                'detailed_conversation': transcricao_result.get('conversa_detalhada', ''),
                'total_speakers': transcricao_result.get('total_falantes', 2),
                'method_used': transcricao_result.get('metodo', 'dual_stream_whisper_gpt')
            },
            'audio_processing_details': {
                'mixing_success': mix_result['success'],
                'original_doctor_duration': mix_result['audio_info']['doctor_duration_seconds'],
                'original_patient_duration': mix_result['audio_info']['patient_duration_seconds'],
                'final_mixed_duration': mix_result['audio_info']['mixed_duration_seconds'],
                'audio_quality': audio_quality,
                'volume_adjustments': mix_result['processing_notes']['volume_adjustments']
            },
            'file_info': {
                'doctor_filename': doctor_audio.filename,
                'patient_filename': patient_audio.filename,
                'doctor_size_bytes': len(doctor_audio_data),
                'patient_size_bytes': len(patient_audio_data),
                'mixed_audio_path': mix_result['mixed_audio_path']  # Para debug/análise
            },
            'processing_time_seconds': processing_time,
            'timestamp': start_time.isoformat(),
            'warnings': [transcricao_result.get('warning')] if transcricao_result.get('warning') else []
        }
        
        # ETAPA 6: Limpar arquivos temporários (opcional, manter para debug)
        # audio_mixer._cleanup_temp_files()
        
        logger.info(f"DUAL STREAM processado com sucesso em {processing_time:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"Erro crítico no dual stream: {e}")
        return {
            'success': False,
            'error': str(e),
            'transcription': '',
            'medical_conversation': {},
            'timestamp': start_time.isoformat()
        }

async def fallback_single_stream_endpoint(
    patient_info: str = Form(default=""),
    audio: UploadFile = File(...),
    recording_metadata: Optional[str] = Form(None)
):
    """
    ENDPOINT FALLBACK: Compatibilidade com stream único
    
    Mantém compatibilidade com o sistema atual
    """
    start_time = datetime.now()
    
    try:
        logger.info("🔄 FALLBACK: Processando stream único")
        
        # Decodificar metadados
        metadata = {}
        if recording_metadata:
            try:
                import json
                metadata = json.loads(recording_metadata)
            except Exception as e:
                logger.warning(f"Erro ao decodificar metadados: {e}")
        
        # Ler arquivo de áudio
        audio_data = await audio.read()
        
        # Usar o serviço de transcrição existente
        resultado = await transcricao_service.transcrever_audio_com_diarizacao(
            audio_data, audio.filename, metadata
        )
        
        if not resultado['sucesso']:
            return {
                'success': False,
                'error': resultado.get('erro', 'Erro na transcrição'),
                'transcription': '',
                'medical_conversation': {}
            }
        
        # Preparar resposta
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'success': True,
            'processing_method': 'single_stream_fallback',
            'transcription': resultado.get('transcricao', ''),
            'medical_conversation': {
                'doctor_text': resultado.get('medico', ''),
                'patient_text': resultado.get('paciente', ''),
                'detailed_conversation': resultado.get('conversa_detalhada', ''),
                'total_speakers': resultado.get('total_falantes', 0),
                'method_used': resultado.get('metodo', 'whisper_gpt_analysis_v2')
            },
            'file_info': {
                'filename': audio.filename,
                'size_bytes': len(audio_data),
                'transcription_length': resultado.get('tamanho', 0)
            },
            'processing_time_seconds': processing_time,
            'warnings': [resultado.get('warning')] if resultado.get('warning') else []
        }
        
    except Exception as e:
        logger.error(f"Erro no fallback single stream: {e}")
        return {
            'success': False,
            'error': str(e),
            'transcription': '',
            'medical_conversation': {}
        }

# Endpoint inteligente que detecta automaticamente o tipo de requisição
async def smart_audio_processing_endpoint(
    patient_info: str = Form(default=""),
    audio: Optional[UploadFile] = File(None),
    doctor_audio: Optional[UploadFile] = File(None),
    patient_audio: Optional[UploadFile] = File(None),
    recording_metadata: Optional[str] = Form(None)
):
    """
    ENDPOINT INTELIGENTE: Detecta automaticamente dual stream vs single stream
    
    - Se receber doctor_audio + patient_audio: usa dual stream
    - Se receber apenas audio: usa single stream
    - Retorna erro se não receber nenhum áudio
    """
    
    # Verificar qual tipo de processamento usar
    if doctor_audio and patient_audio:
        logger.info("🎯 Detectado: DUAL STREAM")
        return await dual_stream_audio_endpoint(
            patient_info, doctor_audio, patient_audio, recording_metadata
        )
    
    elif audio:
        logger.info("🔄 Detectado: SINGLE STREAM")
        return await fallback_single_stream_endpoint(
            patient_info, audio, recording_metadata
        )
    
    else:
        return {
            'success': False,
            'error': 'Nenhum áudio fornecido. Use "audio" para stream único ou "doctor_audio" + "patient_audio" para dual stream',
            'transcription': '',
            'medical_conversation': {}
        }