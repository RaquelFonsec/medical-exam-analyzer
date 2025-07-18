from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return "Home funciona!"

@app.route('/consultation')
def consultation():
    return "CONSULTATION FUNCIONA SEM TEMPLATE!"

@app.route('/consultation-with-template')
def consultation_with_template():
    return render_template('consultation.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
