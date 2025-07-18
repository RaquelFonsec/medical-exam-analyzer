from flask import Flask, render_template, request, jsonify
import requests
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'previdas-2024'

BACKEND_URL = "http://localhost:8000"
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/consultation')
def consultation():
    return render_template('consultation.html')

@app.route('/api/upload-exam', methods=['POST'])
def upload_exam():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400
        
        file = request.files['file']
        exam_type = request.form.get('exam_type', 'geral')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            files = {'file': (filename, file, file.content_type)}
            data = {'exam_type': exam_type}
            
            response = requests.post(
                f"{BACKEND_URL}/upload-exam/",
                files=files,
                data=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return jsonify({
                    'success': True,
                    'filename': result.get('filename'),
                    'extracted_text': result.get('extracted_text'),
                    'report': result.get('report'),
                    'confidence': result.get('confidence', 0.0)
                })
            else:
                return jsonify({'success': False, 'error': 'Erro no processamento'}), 500
        
        return jsonify({'success': False, 'error': 'Tipo de arquivo não permitido'}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process-consultation', methods=['POST'])
def process_consultation():
    """USAR IA REAL DO OPENAI"""
    try:
        print("🤖 ENVIANDO PARA IA REAL...")
        
        # Pegar dados do formulário
        patient_info = request.form.get('patient_info', '')
        
        if not patient_info.strip():
            patient_info = "Consulta médica processada"
        
        print(f"📝 Dados do paciente: {patient_info}")
        
        # Chamar IA REAL no backend
        response = requests.post(
            f"{BACKEND_URL}/ai-consultation/",
            data={'patient_info': patient_info},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=120
        )
        
        print(f"📡 Status da IA: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ IA SUCCESS: {result.get('success', False)}")
            return jsonify(result)
        else:
            print(f"❌ IA ERROR: {response.text}")
            return jsonify({
                'success': False, 
                'error': f'IA Backend Error: {response.status_code} - {response.text}'
            }), 500
            
    except Exception as e:
        print(f"❌ FRONTEND ERROR: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
