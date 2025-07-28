# ============================================================================
# MAIN.PY - SISTEMA MÉDICO COM PIPELINE E RAG
# ============================================================================

import os
import sys
import traceback
import tempfile
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List

# Configurar path para imports
sys.path.append('.')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# Verificar variáveis essenciais
required_env_vars = ['OPENAI_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Variáveis de ambiente faltando: {missing_vars}")
    sys.exit(1)

app = FastAPI(
    title="Medical AI System", 
    version="3.1",
    description="Sistema de análise médica com pipeline e RAG"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importações dos serviços existentes
multimodal_service = None

try:
    # Importar o serviço multimodal que realmente existe
    from services.multimodal_ai_service import MultimodalAIService
    multimodal_service = MultimodalAIService()
    print("✅ MultimodalAIService carregado")
except ImportError as e:
    print(f"❌ Erro ao carregar MultimodalAIService: {e}")
    multimodal_service = None


def is_audio_file(content_type: str, filename: str) -> bool:
    """Verifica se o arquivo é de áudio"""
    if not filename:
        return False
        
    audio_types = ['audio/', 'video/', 'application/octet-stream']
    audio_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.webm', '.mp4', '.mpeg', '.aac']
    
    if content_type:
        for audio_type in audio_types:
            if content_type.startswith(audio_type):
                return True
    
    if filename:
        for ext in audio_extensions:
            if filename.lower().endswith(ext):
                return True
    
    return False


def is_image_file(content_type: str, filename: str) -> bool:
    """Verifica se o arquivo é uma imagem"""
    if not filename:
        return False
        
    image_types = ['image/']
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    
    if content_type:
        for image_type in image_types:
            if content_type.startswith(image_type):
                return True
    
    if filename:
        for ext in image_extensions:
            if filename.lower().endswith(ext):
                return True
    
    return False


def generate_anamnese_from_data(analysis_data: Dict[str, Any]) -> str:
    """Gera anamnese estruturada seguindo padrão ideal para telemedicina"""
    try:
        patient_data = analysis_data.get("patient_data", {})
        transcription = analysis_data.get("transcription", "")
        classification = analysis_data.get("classification", {})
        
        # Dados do paciente
        nome = patient_data.get('nome', 'Não informado')
        idade = patient_data.get('idade', 'Não informada')
        sexo = patient_data.get('sexo', 'Não informado')
        profissao = patient_data.get('profissao', 'Não informada')
        
        # Sintomas e condições
        sintomas = patient_data.get('sintomas', [])
        medicamentos = patient_data.get('medicamentos', [])
        condicoes = patient_data.get('condicoes', [])
        
        # Classificação
        cid = classification.get('cid_principal', 'A definir')
        tipo_beneficio = classification.get('tipo_beneficio', 'Em avaliação')
        
        # Determinar queixa principal baseada no tipo de benefício
        queixa_map = {
            'AUXÍLIO-DOENÇA': 'Afastamento do trabalho por incapacidade temporária',
            'BPC/LOAS': 'Avaliação para Benefício de Prestação Continuada',
            'APOSENTADORIA POR INVALIDEZ': 'Avaliação para aposentadoria por invalidez',
            'AUXÍLIO-ACIDENTE': 'Redução da capacidade laborativa pós-acidente',
            'ISENÇÃO IMPOSTO DE RENDA': 'Isenção de IR por doença grave'
        }
        queixa_principal = queixa_map.get(tipo_beneficio, 'Avaliação de incapacidade')
        
        anamnese = f"""**ANAMNESE MÉDICA - TELEMEDICINA**

**1. IDENTIFICAÇÃO DO PACIENTE**
Nome: {nome}
Idade: {idade} anos
Sexo: {sexo}
Profissão: {profissao}
Documento de identificação: Conforme processo
Número de processo: Conforme solicitação

**2. QUEIXA PRINCIPAL**
{queixa_principal}
Solicitação específica: {tipo_beneficio}

**3. HISTÓRIA DA DOENÇA ATUAL (HDA)**
{transcription if transcription.strip() else 'Paciente relata quadro clínico atual conforme dados fornecidos via telemedicina. Apresenta sintomas compatíveis com a condição referida, com impacto sobre a funcionalidade e capacidade laborativa.'}

Fatores desencadeantes ou agravantes: {', '.join(condicoes) if condicoes else 'A esclarecer em avaliação presencial'}
Tratamentos realizados: {', '.join(medicamentos) if medicamentos else 'Conforme prescrição médica'}
Sintomas atuais: {', '.join(sintomas) if sintomas else 'Conforme relato do paciente'}

**4. ANTECEDENTES PESSOAIS E FAMILIARES RELEVANTES**
Doenças prévias: {', '.join(condicoes) if condicoes else 'Conforme histórico médico'}
Histórico ocupacional: {profissao if profissao != 'Não informada' else 'Conforme CTPS'}
Histórico previdenciário: Conforme CNIS

**5. DOCUMENTAÇÃO APRESENTADA**
Documentos médicos: Conforme processo
Exames complementares: Conforme anexos
Observação: Análise baseada em documentação disponível e consulta por telemedicina

**6. EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)**
Relato de autoavaliação: Limitações funcionais referidas pelo paciente
Observação visual: Por videoconferência/telemedicina
Limitações observadas: Compatíveis com o quadro clínico relatado
Avaliação funcional: Restrições evidentes para atividade laboral habitual

**7. AVALIAÇÃO MÉDICA (ASSESSMENT)**
Hipótese diagnóstica: Compatível com CID-10: {cid}
Correlação clínico-funcional: Quadro clínico com repercussões sobre a capacidade laborativa
Enquadramento previdenciário: {tipo_beneficio}

Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
        
        return anamnese.strip()
        
    except Exception as e:
        print(f"❌ Erro ao gerar anamnese: {e}")
        return "**ANAMNESE MÉDICA - TELEMEDICINA**\n\nErro na geração automática. Recomenda-se consulta médica presencial para elaboração completa da anamnese."


def generate_laudo_from_data(analysis_data: Dict[str, Any]) -> str:
    """Gera laudo médico baseado nos dados da análise"""
    try:
        patient_data = analysis_data.get("patient_data", {})
        classification = analysis_data.get("classification", {})
        medical_report = analysis_data.get("medical_report", "")
        
        laudo = f"""
LAUDO MÉDICO ESPECIALIZADO

IDENTIFICAÇÃO:
Paciente: {patient_data.get('nome', 'Não informado')}
Idade: {patient_data.get('idade', 'Não informada')} anos
Documento: {patient_data.get('documento', 'Não informado')}

DIAGNÓSTICO:
CID-10: {classification.get('cid_principal', 'A definir')}
Gravidade: {classification.get('gravidade', 'A avaliar')}

ANÁLISE FUNCIONAL:
{classification.get('prognostico', 'Prognóstico requer avaliação médica continuada')}

CONCLUSÃO:
Com base na avaliação médica realizada por telemedicina, o paciente apresenta condições compatíveis com:
Tipo de Benefício Recomendado: {classification.get('tipo_beneficio', 'A definir')}

RECOMENDAÇÕES:
- Acompanhamento médico especializado
- Reavaliação periódica das condições funcionais
- Cumprimento do plano terapêutico proposto

{medical_report if medical_report else ''}

___________________________
Dr(a). Sistema de IA Médica
CRM: Virtual
Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}

IMPORTANTE: Este laudo foi gerado por sistema de IA e deve ser validado por médico habilitado.
"""
        return laudo.strip()
        
    except Exception as e:
        print(f"❌ Erro ao gerar laudo: {e}")
        return "Laudo: Erro na geração - consulte o relatório médico completo"


# ============================================================================
# ROTAS DA API
# ============================================================================

@app.get("/")
async def root():
    """Página inicial"""
    return {"message": "Sistema Médico AI - Backend ativo", "version": "3.1"}


@app.get("/health")
async def health_check():
    """Health check da API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "multimodal": multimodal_service is not None
        }
    }


@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis(
    patient_info: str = Form(""),
    audio: UploadFile = File(None),
    image: UploadFile = File(None)
):
    """Análise médica inteligente multimodal"""
    try:
        if not multimodal_service:
            raise HTTPException(status_code=500, detail="Serviço multimodal não disponível")

        print(f"🧠 Análise inteligente: {patient_info[:50]}...")
        
        audio_bytes = None
        if audio and audio.filename:
            print(f"🎤 Áudio enviado: {audio.filename}")
            print(f"🔍 Tipo de conteúdo do áudio: {audio.content_type}")
            audio_bytes = await audio.read()
            print(f"📊 Tamanho do áudio: {len(audio_bytes)} bytes")
            
            if len(audio_bytes) < 100:
                print("⚠️ Arquivo de áudio muito pequeno - ignorando")
                audio_bytes = None
        elif audio:
            print("⚠️ Áudio sem nome de arquivo - tentando processar")
            audio_bytes = await audio.read()
            if len(audio_bytes) < 100:
                print("⚠️ Áudio inválido - ignorando")
                audio_bytes = None
        
        image_path = None
        if image:
            print(f"🖼️ Imagem enviada: {image.filename}")
            # Salvar imagem temporariamente se necessário
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(await image.read())
                image_path = tmp.name
        else:
            print("ℹ️ Nenhuma imagem recebida")

        print("🔄 Executando análise multimodal...")
        
        # Executar análise multimodal
        multimodal_result = await multimodal_service.analyze_multimodal(
            patient_info=patient_info,
            audio_bytes=audio_bytes,
            image_path=image_path
        )
        
        # Limpar arquivo temporário
        if image_path and os.path.exists(image_path):
            os.unlink(image_path)
        
        print("✅ Análise multimodal concluída")
        
        # Preparar resposta (com suporte ao Pydantic AI)
        if multimodal_result.get("pydantic_analysis"):
            # Usar dados do Pydantic AI diretamente
            response_data = {
                "success": True,
                "transcription": multimodal_result.get("transcription", ""),
                "anamnese": multimodal_result.get("anamnese", "Anamnese gerada pelo Pydantic AI"),
                "laudo_medico": multimodal_result.get("medical_report", "Laudo gerado pelo Pydantic AI"),
                "classification": multimodal_result.get("classification", {}),
                "patient_data": multimodal_result.get("patient_data", {}),
                "medical_report": multimodal_result.get("medical_report", ""),
                "rag_results": multimodal_result.get("rag_results", []),
                "confidence_score": multimodal_result.get("confidence_score", 0.8),
                "analysis_method": "Pydantic AI + LangGraph + RAG + FAISS",
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Usar método tradicional
            response_data = {
                "success": True,
                "transcription": multimodal_result.get("transcription", ""),
                "anamnese": generate_anamnese_from_data(multimodal_result),
                "laudo_medico": generate_laudo_from_data(multimodal_result),
                "classification": multimodal_result.get("classification", {}),
                "patient_data": multimodal_result.get("patient_data", {}),
                "medical_report": multimodal_result.get("medical_report", ""),
                "rag_results": multimodal_result.get("rag_results", []),
                "analysis_method": "Tradicional + RAG",
                "timestamp": datetime.now().isoformat()
            }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        print(f"❌ Erro na análise: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "transcription": "Erro na análise",
                "anamnese": "Erro ao gerar anamnese",
                "laudo_medico": "Erro ao gerar laudo",
                "timestamp": datetime.now().isoformat()
            }
        )


@app.post("/api/analyze-document")
async def analyze_document_with_textract(
    document: UploadFile = File(...),
    patient_info: str = Form(""),
    use_textract: bool = Form(True)
):
    """Analisa documento médico usando AWS Textract ou OCR básico"""
    try:
        if not multimodal_service:
            raise HTTPException(status_code=500, detail="Serviço multimodal não disponível")

        print(f"📄 Analisando documento: {document.filename}")
        
        # Salvar arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(document.filename)[1]) as tmp:
            tmp.write(await document.read())
            temp_path = tmp.name
        
        try:
            # Analisar documento
            analysis_result = await multimodal_service._analyze_documents([temp_path])
            
            # Combinar análise com informações do paciente
            if patient_info:
                combined_text = f"{patient_info}\n"
                for doc in analysis_result.get("documents", []):
                    combined_text += f"{doc.get('text', '')}\n"
                
                # Executar análise completa
                multimodal_result = await multimodal_service.analyze_multimodal(
                    patient_info=combined_text,
                    document_paths=[temp_path]
                )
                
                response_data = {
                    "success": True,
                    "document_analysis": analysis_result,
                    "transcription": "",
                    "anamnese": generate_anamnese_from_data(multimodal_result),
                    "laudo_medico": generate_laudo_from_data(multimodal_result),
                    "classification": multimodal_result.get("classification", {}),
                    "patient_data": multimodal_result.get("patient_data", {}),
                    "medical_report": multimodal_result.get("medical_report", ""),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                response_data = {
                    "success": True,
                    "document_analysis": analysis_result,
                    "timestamp": datetime.now().isoformat()
                }
            
            return JSONResponse(content=response_data)
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except Exception as e:
        print(f"❌ Erro na análise de documento: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
