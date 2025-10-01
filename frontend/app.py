from flask import Flask, render_template, request, jsonify, redirect
import requests
import os

app = Flask(__name__)

# Configuração do backend
BACKEND_URL = "http://localhost:8000"

@app.route("/")
def index():
    """Página principal - redirecionar para login"""
    return redirect("/login")

@app.route('/login')
def login_page():
    """Página de login médico"""
    return render_template('login.html')

@app.route("/consultation")
def consultation():
    """Interface de consulta médica inteligente"""
    from flask import make_response
    import time
    response = make_response(render_template("consultation.html", version=int(time.time())))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/test_audio_button.html")
def test_audio_button():
    """Página de diagnóstico do botão de áudio"""
    return app.send_static_file('../test_audio_button.html')

@app.route("/test-google-meet")
def test_google_meet():
    """Página de teste para captura de áudio do Google Meet"""
    return render_template("test_google_meet.html")

@app.route("/test-simple")
def test_simple():
    """Teste simples"""
    return "<h1>Flask funcionando!</h1>"

@app.route("/dual-stream-guide")
def dual_stream_guide():
    """Guia para dual stream"""
    return render_template("dual_stream_guide.html")

@app.route("/telemedicina-guide")
def telemedicina_guide():
    """Guia de telemedicina para captura de áudio do Google Meet"""
    return render_template("telemedicina_guide.html")

@app.route("/test-audio-capture")
def test_audio_capture():
    """Teste de captura de áudio do Google Meet"""
    return render_template("test_audio_capture.html")

@app.route('/api/login', methods=['POST'])
def api_login():
    """API de login - redirecionar para backend"""
    try:
        # Repassar dados para backend
        response = requests.post(
            f"{BACKEND_URL}/login",
            json=request.get_json(),
            timeout=30
        )
        
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Erro de comunicação: {str(e)}'
        }), 500

@app.route('/logout')
def logout():
    """Logout do sistema"""
    return redirect('/login')

@app.route('/api/intelligent-medical-analysis', methods=['POST'])
def intelligent_medical_analysis():
    """🧠 ANÁLISE MÉDICA INTELIGENTE - Rota principal"""
    try:
        patient_info = request.form.get('patient_info', '')
        
        print(f"🧠 Análise inteligente: {patient_info[:50]}...")
        
        # Preparar dados
        data = {'patient_info': patient_info}
        files = {}
        
        # Arquivo de áudio (gravação) - NOME CORRIGIDO
        if 'audio' in request.files:
            audio_file = request.files['audio']
            if audio_file.filename:
                files['audio'] = (audio_file.filename, audio_file, audio_file.content_type)
                print(f"🎤 Áudio enviado: {audio_file.filename}")
        
        # Arquivo de imagem/documento - NOME CORRIGIDO  
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename:
                files['image'] = (image_file.filename, image_file, image_file.content_type)
                print(f"📄 Documento enviado: {image_file.filename}")
        
        # Chamar backend na ROTA CORRETA
        response = requests.post(
            f"{BACKEND_URL}/api/intelligent-medical-analysis",
            files=files,
            data=data,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Análise inteligente concluída")
            
            return jsonify({
                "success": True,
                "transcription": result.get("transcription", "Sem transcrição"),
                "anamnese": result.get("anamnese", "Anamnese não disponível"),
                "laudo_medico": result.get("laudo_medico", "Laudo não disponível"),
                "medical_report": result.get("medical_report", "Relatório não disponível"),
                "classification": result.get("classification", {}),
                "patient_data": result.get("patient_data", {}),
                "analysis_method": result.get("analysis_method", "Não informado"),
                "confidence_score": result.get("confidence_score", 0.8),
                "timestamp": result.get("timestamp", "")
            })
        else:
            print(f"❌ Erro backend: {response.status_code}")
            return jsonify({
                'success': False, 
                'error': f'Erro no backend: {response.status_code} - {response.text}'
            }), 500
            
    except Exception as e:
        print(f"❌ Erro no frontend: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/multimodal-consultation', methods=['POST'])
def multimodal_consultation_legacy():
    """🔄 ROTA LEGADO - Compatibilidade com versão anterior"""
    try:
        print("🔄 Usando rota legado - redirecionando para análise inteligente")
        
        # Redirecionar para análise inteligente
        return intelligent_medical_analysis()
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-audio-consultation', methods=['POST'])
def upload_audio_consultation():
    """📁 Upload de arquivo de áudio"""
    try:
        patient_info = request.form.get('patient_info', '')
        
        print(f"📁 Upload de áudio: {patient_info}")
        
        # Preparar dados
        data = {'patient_info': patient_info}
        files = {}
        
        # Arquivo de áudio upload
        if 'audio_upload' in request.files:
            audio_file = request.files['audio_upload']
            if audio_file.filename:
                files['audio_upload'] = (audio_file.filename, audio_file, audio_file.content_type)
                print(f"📁 Arquivo enviado: {audio_file.filename}")
        
        # Chamar backend
        response = requests.post(
            f"{BACKEND_URL}/upload-audio/",
            files=files,
            data=data,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload processado com sucesso")
            
            return jsonify({
                "success": True,
                "transcription": result.get("transcription", "Erro na transcrição"),
                "medical_report": result.get("multimodal_report", "Erro no laudo"),
                "modalities_used": result.get("modalities_used", {}),
                "model": result.get("model", "GPT-4o"),
                "confidence": result.get("confidence", 0.95),
                "timestamp": result.get("timestamp", ""),
                "type": "audio_upload"
            })
        else:
            return jsonify({
                'success': False, 
                'error': f'Erro no backend: {response.status_code}'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-telemedicine', methods=['POST'])
def process_telemedicine():
    """🏥 API: Processamento de telemedicina com áudios separados"""
    try:
        patient_info = request.form.get('patient_info', '')
        service_type = request.form.get('service_type', 'telemedicina')
        
        print(f"🏥 Telemedicina: {patient_info}")
        
        # Preparar dados
        data = {
            'patient_info': patient_info,
            'service_type': service_type
        }
        files = {}
        
        # Arquivo de áudio do médico
        if 'doctor_audio' in request.files:
            doctor_audio = request.files['doctor_audio']
            if doctor_audio.filename:
                files['doctor_audio'] = (doctor_audio.filename, doctor_audio, doctor_audio.content_type)
                print(f"👨‍⚕️ Áudio do médico: {doctor_audio.filename}")
        
        # Arquivo de áudio do paciente
        if 'patient_audio' in request.files:
            patient_audio = request.files['patient_audio']
            if patient_audio.filename:
                files['patient_audio'] = (patient_audio.filename, patient_audio, patient_audio.content_type)
                print(f"👤 Áudio do paciente: {patient_audio.filename}")
        
        if len(files) != 2:
            return jsonify({
                'success': False, 
                'error': 'Ambos os arquivos de áudio (médico e paciente) são obrigatórios'
            }), 400
        
        # Chamar backend
        response = requests.post(
            f"{BACKEND_URL}/api/process-telemedicine",
            files=files,
            data=data,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Telemedicina processada com sucesso")
            
            # Extrair dados da conversa médica
            medical_conv = result.get("medical_conversation", {})
            processing_details = result.get("processing_details", {})
            
            return jsonify({
                "success": True,
                "service_type": result.get("service_type", "telemedicina"),
                "transcription": result.get("transcription", ""),
                "doctor_text": medical_conv.get("doctor_text", ""),
                "patient_text": medical_conv.get("patient_text", ""),
                "method": medical_conv.get("method", "telemedicine_processing"),
                "total_speakers": medical_conv.get("total_speakers", 2),
                "processing_details": processing_details,
                "timestamp": result.get("timestamp", "")
            })
        else:
            print(f"❌ Erro do backend: {response.status_code}")
            return jsonify({
                'success': False, 
                'error': f'Erro do backend: {response.status_code}'
            }), 500
            
    except Exception as e:
        print(f"❌ Erro na telemedicina: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/audio-diarization-consultation', methods=['POST'])
def audio_diarization_consultation():
    """🎯 Upload de áudio com diarização de falantes"""
    try:
        patient_info = request.form.get('patient_info', '')
        
        print(f"🎯 Diarização de áudio: {patient_info}")
        
        # Preparar dados
        data = {'patient_info': patient_info}
        files = {}
        
        # Arquivo de áudio
        if 'audio' in request.files:
            audio_file = request.files['audio']
            if audio_file.filename:
                files['audio'] = (audio_file.filename, audio_file, audio_file.content_type)
                print(f"🎤 Arquivo para diarização: {audio_file.filename}")
        
        if not files:
            return jsonify({
                'success': False, 
                'error': 'Arquivo de áudio é obrigatório'
            }), 400
        
        # Chamar backend
        response = requests.post(
            f"{BACKEND_URL}/api/audio-diarization",
            files=files,
            data=data,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Diarização processada com sucesso")
            
            # Extrair dados da conversa médica
            medical_conv = result.get("medical_conversation", {})
            
            return jsonify({
                "success": True,
                "transcription": result.get("transcription", ""),
                "doctor_text": medical_conv.get("doctor_text", ""),
                "patient_text": medical_conv.get("patient_text", ""),
                "detailed_conversation": medical_conv.get("detailed_conversation", ""),
                "total_speakers": medical_conv.get("total_speakers", 0),
                "method_used": medical_conv.get("method_used", "unknown"),
                "duration": medical_conv.get("duration_seconds", 0),
                "processing_time": result.get("processing_time_seconds", 0),
                "warnings": result.get("warnings", []),
                "timestamp": result.get("timestamp", ""),
                "type": "audio_diarization"
            })
        else:
            error_msg = f'Erro no backend: {response.status_code}'
            try:
                error_data = response.json()
                error_msg = error_data.get('error', error_msg)
            except:
                pass
                
            return jsonify({
                'success': False, 
                'error': error_msg
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test')
def test_page():
    """🧪 Página de teste do sistema"""
    return """
    <html>
    <head><title>PREVIDAS - Teste</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🧪 PREVIDAS - Teste do Sistema</h1>
        
        <h2>Status dos Serviços:</h2>
        <p><strong>Frontend:</strong> ✅ Rodando na porta 5003</p>
        <p><strong>Backend:</strong> <span id="backend-status">Verificando...</span></p>
        
        <h2>Rotas Disponíveis:</h2>
        <ul>
            <li><a href="/login">Login</a></li>
            <li><a href="/consultation">Consulta Inteligente</a></li>
        </ul>
        
        <h2>Teste de Conectividade:</h2>
        <button onclick="testBackend()">Testar Backend</button>
        <div id="test-result"></div>
        
        <script>
            async function testBackend() {
                try {
                    const response = await fetch('https://consultorio.previdas.com.br/health');
                    const result = await response.json();
                    document.getElementById('backend-status').innerHTML = '✅ ' + result.status;
                    document.getElementById('test-result').innerHTML = 
                        '<h3>✅ Backend OK</h3><pre>' + JSON.stringify(result, null, 2) + '</pre>';
                } catch (error) {
                    document.getElementById('backend-status').innerHTML = '❌ Erro';
                    document.getElementById('test-result').innerHTML = 
                        '<h3>❌ Backend Error</h3><p>' + error.message + '</p>';
                }
            }
            
            // Testar automaticamente
            testBackend();
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    print("🧠 PREVIDAS Frontend Inteligente iniciando na porta 5003...")
    print("📋 Rotas disponíveis:")
    print("  • http://localhost:5003 → Redireciona para login")
    print("  • http://localhost:5003/login → Página de login")
    print("  • http://localhost:5003/consultation → Interface inteligente")
    print("  • http://localhost:5003/test → Página de teste")
    print("")
    print("🎯 FUNCIONALIDADES:")
    print("  • Análise inteligente de contexto (BPC/Incapacidade/Perícia)")
    print("  • Anamnese + Laudo especializados")
    print("  • Transcrição com Whisper")
    print("  • Análise de documentos")
    
    @app.route('/api/dual-audio-stream', methods=['POST'])
    def dual_audio_stream_consultation():
        """🎯 NOVA API: Processamento de dois streams de áudio simultâneos"""
        try:
            patient_info = request.form.get('patient_info', '')
            recording_metadata = request.form.get('recording_metadata', '')
            
            print(f"🎯 Dual stream de áudio: {patient_info}")
            
            # Preparar dados
            data = {
                'patient_info': patient_info,
                'recording_metadata': recording_metadata
            }
            files = {}
            
            # Arquivo de áudio do médico
            if 'doctor_audio' in request.files:
                doctor_audio = request.files['doctor_audio']
                if doctor_audio.filename:
                    files['doctor_audio'] = (doctor_audio.filename, doctor_audio, doctor_audio.content_type)
                    print(f"👨‍⚕️ Áudio do médico: {doctor_audio.filename}")
            
            # Arquivo de áudio do paciente
            if 'patient_audio' in request.files:
                patient_audio = request.files['patient_audio']
                if patient_audio.filename:
                    files['patient_audio'] = (patient_audio.filename, patient_audio, patient_audio.content_type)
                    print(f"👤 Áudio do paciente: {patient_audio.filename}")
            
            if len(files) != 2:
                return jsonify({
                    'success': False, 
                    'error': 'Ambos os arquivos de áudio (médico e paciente) são obrigatórios'
                }), 400
            
            # Chamar backend
            response = requests.post(
                f"{BACKEND_URL}/api/dual-stream-audio",
                files=files,
                data=data,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Dual stream processado com sucesso")
                
                # Extrair dados da conversa médica
                medical_conv = result.get("medical_conversation", {})
                processing_details = result.get("processing_details", {})
                
                return jsonify({
                    "success": True,
                    "transcription": result.get("transcription", ""),
                    "doctor_text": medical_conv.get("doctor_text", ""),
                    "patient_text": medical_conv.get("patient_text", ""),
                    "method": medical_conv.get("method", "dual_stream_separate_processing"),
                    "total_speakers": medical_conv.get("total_speakers", 2),
                    "processing_details": processing_details,
                    "timestamp": result.get("timestamp", "")
                })
            else:
                print(f"❌ Erro do backend: {response.status_code}")
                return jsonify({
                    'success': False, 
                    'error': f'Erro do backend: {response.status_code}'
                }), 500
                
        except Exception as e:
            print(f"❌ Erro no dual stream: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-exams', methods=['POST'])
def proxy_process_exams():
    """Proxy para processamento de exames"""
    try:
        # Obter dados do formulário
        exams = request.files.getlist('exams[]')
        patient_context = request.form.get('patient_context', '')
        service_type = request.form.get('service_type', 'exames')
        
        if not exams or not any(exam.filename for exam in exams):
            return jsonify({
                'success': False,
                'error': 'Nenhum exame fornecido'
            }), 400
        
        print(f"🔬 Processamento de exames: {len(exams)} arquivos")
        
        # Preparar dados para o backend
        files = []
        for exam in exams:
            if exam.filename:
                files.append(('exams', (exam.filename, exam, exam.content_type)))
        
        data = {
            'patient_context': patient_context,
            'service_type': service_type
        }
        
        # Fazer requisição para o backend
        response = requests.post(
            f"{BACKEND_URL}/api/process-exams",
            files=files,
            data=data,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Exames processados com sucesso")
            return jsonify(result)
        else:
            print(f"❌ Erro do backend: {response.status_code}")
            return jsonify({
                'success': False,
                'error': f'Backend error: {response.status_code}',
                'details': response.text
            }), 500
            
    except Exception as e:
        print(f"❌ Erro no processamento de exames: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)