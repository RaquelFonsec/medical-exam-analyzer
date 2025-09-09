FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 
RUN pip install pdf2image

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

