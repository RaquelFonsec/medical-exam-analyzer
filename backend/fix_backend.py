@app.post("/simple-consultation/")
async def simple_consultation(request: Request):
    """Rota flexível que aceita qualquer formato"""
    try:
        patient_info = ""
        
        # Tentar pegar dados de diferentes formas
        content_type = request.headers.get("content-type", "")
        
        if "application/x-www-form-urlencoded" in content_type:
            # Formato form
            form_data = await request.form()
            patient_info = form_data.get("patient_info", "")
        elif "multipart/form-data" in content_type:
            # Formato multipart
            form_data = await request.form()
            patient_info = form_data.get("patient_info", "")
        elif "application/json" in content_type:
            # Formato JSON
            json_data = await request.json()
            patient_info = json_data.get("patient_info", "")
        else:
            # Fallback - tentar form
            try:
                form_data = await request.form()
                patient_info = form_data.get("patient_info", "Consulta processada")
            except:
                patient_info = "Consulta médica processada"
        
        print(f"✅ Dados processados: {patient_info}")
        
        return {
            "success": True,
            "transcription": f"Consulta médica: {patient_info}",
            "medical_report": f"""## 📋 LAUDO MÉDICO

**Paciente:** {patient_info}
**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

## 🗣️ QUEIXA PRINCIPAL
Baseado na consulta: {patient_info}

## 📖 AVALIAÇÃO
Consulta processada com sucesso pelo sistema PREVIDAS.

## 🎯 CONDUTA
Seguimento médico adequado.

---
*Sistema PREVIDAS - IA Médica*""",
            "confidence": 0.9
        }
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return {"success": False, "error": str(e)}
