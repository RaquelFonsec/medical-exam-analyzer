// Form submission - VERSÃO CORRIGIDA
consultationForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    // Preparar dados simples
    const patientInfo = this.querySelector('textarea[name="patient_info"]').value || 
                       "Paciente com consulta gravada";

    // Mostrar loading
    document.getElementById('submitBtn').style.display = 'none';
    document.getElementById('processing').style.display = 'block';
    document.getElementById('results').style.display = 'none';

    try {
        // Chamar rota que funciona
        const response = await fetch('http://localhost:8000/simple-consultation/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: 'patient_info=' + encodeURIComponent(patientInfo)
        });

        const result = await response.json();

        if (result.success) {
            displayResults(result);
        } else {
            alert('Erro: ' + result.error);
        }

    } catch (error) {
        console.error('Erro:', error);
        alert('Erro na comunicação: ' + error.message);
    } finally {
        document.getElementById('processing').style.display = 'none';
        document.getElementById('submitBtn').style.display = 'block';
    }
});
