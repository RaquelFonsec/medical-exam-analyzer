from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/consultation')
def consultation():
    return render_template('consultation.html')

@app.route('/api/simple-test', methods=['POST'])
def simple_test():
    try:
        patient_info = request.form.get('patient_info', 'Teste')
        
        # Usar rota simples do backend
        response = requests.post(
            'http://localhost:8000/simple-consultation/',
            data={'patient_info': patient_info},
            timeout=30
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'success': False, 'error': f'Status: {response.status_code}'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
