from flask import Flask, request, jsonify
import asyncio
import time
import os
from backend.app.services.cfm_compliance import medical_integration_service

app = Flask(__name__)

@app.route('/api/intelligent-medical-analysis', methods=['POST'])
def intelligent_medical_analysis():
    """Endpoint principal - SISTEMA COMPLETO"""
    try:
        print("🏥 Iniciando análise médica COMPLETA")
        
        # 1. EXTRAIR DADOS DA REQUISIÇÃO
        patient_info = request.form.get('patient_info', '')
        print(f"📝 Dados do paciente: {patient_info[:100]}...")
        
        if not patient_info.strip():
            return jsonify({
                "success": False,
                "error": "Informações do paciente são obrigatórias"
            })
        
        # 2. PROCESSAR ÁUDIO
        audio_file = None
        if 'audio_data' in request.files:
            audio_file = request.files['audio_data']
            print(f"🎤 Áudio recebido: {audio_file.filename}")
        
        # 3. PROCESSAR DOCUMENTO
        image_file = None
        if 'image_data' in request.files:
            image_file = request.files['image_data']
            print(f"📄 Documento recebido: {image_file.filename}")
        
        # 4. PREPARAR DADOS PARA ANÁLISE COMPLETA
        consultation_data = {
            'patient_info': patient_info,
            'audio_data': audio_file,
            'image_data': image_file
        }
        
        # 5. EXECUTAR ANÁLISE COMPLETA (ASYNC)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            medical_integration_service.process_consultation_complete(consultation_data)
        )
        
        loop.close()
        
        print(f"✅ Análise concluída: {result.get('context_analysis', {}).get('main_context', 'N/A')}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"💥 Erro na análise: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Erro interno: {str(e)}",
            "transcription": "Erro no processamento",
            "anamnese": f"Erro ao gerar anamnese: {str(e)}",
            "laudo_medico": f"Erro ao gerar laudo: {str(e)}"
        })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check do sistema"""
    return jsonify({
        "status": "healthy",
        "sistema": "Médico Completo v2.0",
        "timestamp": time.time()
    })

@app.route('/api/contexts', methods=['GET'])
def get_available_contexts():
    """Listar contextos médicos disponíveis"""
    try:
        from app.services.multimodal_ai_service import MultimodalAIService
        # Criar instância local ao invés de usar global
        service = MultimodalAIService()
        contexts = service.get_available_contexts() if hasattr(service, 'get_available_contexts') else []
        
        return jsonify({
            "success": True,
            "contexts": contexts,
            "total": len(contexts)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
