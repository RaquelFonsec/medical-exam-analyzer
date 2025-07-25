# 🏥 Sistema de Análise Médica - RESUMO

## 🚀 Comandos Básicos

### **Iniciar Sistema**
```bash
# 1. Ir para o diretório
cd /home/raquel/medical-exam-analyzer

# 2. Configurar OpenAI
export OPENAI_API_KEY="sua_chave_aqui"

# 3. Iniciar servidor
cd backend/app && python main.py

# 4. Testar
curl http://localhost:5003/api/health
```

### **Usar Sistema**
```bash
# Interface Web
firefox http://localhost:5003/consultation

# API - Teste simples
curl -X POST http://localhost:5003/api/intelligent-medical-analysis \
  -F "patient_info=João, 30 anos, fratura braço, recuperação 2 meses"

# Parar servidor
pkill -f "python main.py"
```

## 🏗️ Arquitetura

### **🏗️ Arquitetura do Sistema**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FRONTEND      │    │    BACKEND      │    │   SERVIÇOS IA   │
│                 │    │                 │    │                 │
│ • Interface Web │◄──►│ • FastAPI       │◄──►│ • OpenAI GPT-4o │
│ • JavaScript    │    │ • Endpoints     │    │ • Whisper API   │
│ • HTML/CSS      │    │ • Validação     │    │ • Embeddings    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   COMPONENTES   │
                       │                 │
                       │ • RAG Service   │
                       │ • Multimodal AI │
                       │ • Classification│
                       │ • FAISS Index   │
                       └─────────────────┘
```

### **Componentes**
- **MultimodalAIService**: Coordenador principal
- **MedicalRAGService**: Sistema de conhecimento médico
- **Classification**: Auxílio Doença vs Perícia Médica
- **Report Generation**: Geração de laudos

### **Fluxo de Dados**
```
Entrada → Extração → Classificação → Laudo
   │         │           │            │
   │         ▼           ▼            ▼
Texto → Dados do → Tipo Benefício → Relatório
Audio   Paciente   + CID-10        Integrado
```

## 🔌 Endpoints

| Endpoint | Método | Função |
|----------|--------|--------|
| `/api/health` | GET | Status do sistema |
| `/api/intelligent-medical-analysis` | POST | **Análise principal** |
| `/consultation` | GET | Interface web |
| `/docs` | GET | Documentação API |

## ⚙️ Funcionamento

### **1. Processo de Análise**
```python
# 1. Recebe dados (texto/áudio)
# 2. Extrai informações do paciente
# 3. Classifica tipo de benefício
# 4. Sugere CID-10
# 5. Gera laudo completo
```

### **2. Critérios de Classificação**
```
AUXÍLIO DOENÇA:
- Fraturas com recuperação
- Cirurgias temporárias
- Doenças agudas

PERÍCIA MÉDICA:
- Doenças crônicas
- Incapacidade permanente
- Deficiências definitivas
```

### **3. Tecnologias**
```yaml
Backend: FastAPI + Python
Frontend: HTML/JavaScript
IA: OpenAI (GPT-4o + Whisper)
Busca: FAISS + Embeddings
Cache: Redis (opcional)
```

## 🧪 Teste Rápido

```bash
# Exemplo 1 - Auxílio Doença
curl -X POST http://localhost:5003/api/intelligent-medical-analysis \
  -F "patient_info=Pedro, 35 anos, fratura perna, cirurgia, recuperação 3 meses"

# Exemplo 2 - Perícia Médica  
curl -X POST http://localhost:5003/api/intelligent-medical-analysis \
  -F "patient_info=Ana, 60 anos, diabetes grave, cegueira, sem cura"
```

## 📊 Resposta da API

```json
{
  "patient_data": {
    "nome": "Pedro",
    "idade": "35 anos",
    "profissao": "...",
    "queixa_principal": "fratura perna"
  },
  "benefit_classification": {
    "tipo_beneficio": "AUXILIO_DOENCA",
    "cid_principal": "S72.0",
    "cid_descricao": "Fratura do fêmur",
    "gravidade": "MODERADA",
    "justificativa": "..."
  },
  "medical_report": "**LAUDO MÉDICO**\n..."
}
```

## 🔧 Troubleshooting

```bash
# Porta em uso
lsof -i :5003
fuser -k 5003/tcp

# Verificar processos
ps aux | grep "python main.py"

# Logs
cd backend/app && python main.py | tee log.txt

# Testar OpenAI
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

---

**✅ Sistema funcional com classificação automática de benefícios previdenciários integrada no laudo médico!** 