import re

# Ler arquivo main.py
with open('main.py', 'r') as f:
    content = f.read()

# Encontrar padrões problemáticos e corrigir
# Padrão: service_real.analyze_consultation_zero_hallucination(algo, audio_file, patient_info)
# Corrigir para: service_real.analyze_consultation_zero_hallucination(audio_file, patient_info)

# Substituir chamadas incorretas
patterns = [
    # Padrão com 4 argumentos
    (r'await service_real\.analyze_consultation_zero_hallucination\([^,]+,\s*([^,]+),\s*([^)]+)\)', 
     r'await service_real.analyze_consultation_zero_hallucination(\1, \2)'),
    
    # Padrão com service como primeiro argumento
    (r'await service_real\.analyze_consultation_zero_hallucination\(service_real,\s*([^,]+),\s*([^)]+)\)', 
     r'await service_real.analyze_consultation_zero_hallucination(\1, \2)'),
]

for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content)

# Salvar arquivo corrigido
with open('main.py', 'w') as f:
    f.write(content)

print("✅ main.py corrigido!")
