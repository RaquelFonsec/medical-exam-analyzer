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
    return render_template("consultation.html")

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
        
        # Arquivo de áudio (gravação) - NOME CORRETO
        if 'audio_data' in request.files:
            audio_file = request.files['audio_data']
            if audio_file.filename:
                files['audio_data'] = (audio_file.filename, audio_file, audio_file.content_type)
                print(f"🎤 Áudio enviado: {audio_file.filename}")
        
        # Arquivo de imagem/documento - NOME CORRETO
        if 'image_data' in request.files:
            image_file = request.files['image_data']
            if image_file.filename:
                files['image_data'] = (image_file.filename, image_file, image_file.content_type)
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
                "anamnese": result.get("anamnese", "Erro na anamnese"),  # NOVO!
                "laudo_medico": result.get("laudo_medico", "Erro no laudo"),  # NOVO!
                "medical_report": result.get("laudo_medico", "Erro no laudo"),  # Compatibilidade
                "context_analysis": result.get("context_analysis", {}),  # NOVO!
                "specialized_type": result.get("specialized_type", "clinica"),  # NOVO!
                "confidence": result.get("confidence", 0.95),
                "model": result.get("model", "PREVIDAS Intelligence"),
                "timestamp": result.get("timestamp", ""),
                "processing_details": result.get("processing_details", {})  # NOVO!
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
                    const response = await fetch('http://localhost:8000/health');
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
    
    app.run(debug=True, host='0.0.0.0', port=5003)