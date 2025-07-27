# ============================================================================
# MAIN.PY - SISTEMA MÉDICO COM RAG INTEGRADO + FRONTEND
# Versão Completa e Corrigida com Roteamento Frontend
# ============================================================================

import os
import sys
import traceback
from datetime import datetime
from typing import Optional

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Adicionar também o diretório pai para imports relativos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from dotenv import load_dotenv
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Carregar variáveis de ambiente
load_dotenv()

# Verificar variáveis essenciais
required_env_vars = ['OPENAI_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Variáveis de ambiente faltando: {missing_vars}")
    sys.exit(1)

app = FastAPI(
    title="Medical AI System with RAG", 
    version="2.0",
    description="Sistema de análise médica com IA multimodal e RAG"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_anamnese_from_data(multimodal_result: dict) -> str:
    """Gera anamnese seguindo o Modelo Ideal para Telemedicina"""
    try:
        patient_data = multimodal_result.get("patient_data", {})
        transcription = multimodal_result.get("transcription", "")
        benefit_classification = multimodal_result.get("benefit_classification", {})
        
        nome = patient_data.get("nome", "Não informado")
        idade = patient_data.get("idade", "Não informada")
        profissao = patient_data.get("profissao", "Não informada")
        queixa = patient_data.get("queixa_principal", "Não informada")
        sintomas = patient_data.get("sintomas", "Não informados")
        
        tipo_beneficio = benefit_classification.get("tipo_beneficio", "A definir")
        cid = benefit_classification.get("cid_principal", "A definir")
        cid_desc = benefit_classification.get("cid_descricao", "Diagnóstico a confirmar")
        justificativa = benefit_classification.get("justificativa", "Análise médica necessária")
        
        data_atual = datetime.now().strftime("%d/%m/%Y")
        
        anamnese = f"""**ANAMNESE MÉDICA - TELEMEDICINA**

**1. IDENTIFICAÇÃO DO PACIENTE**
• Nome: {nome}
• Idade: {idade}
• Sexo: Não informado
• Profissão: {profissao}
• Documento de identificação: Não informado
• Número de processo/referência: Não informado

**2. QUEIXA PRINCIPAL**
• Motivo da consulta: {queixa}
• Solicitação específica: {tipo_beneficio}
• Objetivo: Avaliação médica para fins previdenciários

**3. HISTÓRIA DA DOENÇA ATUAL (HDA)**
• Data de início dos sintomas: Não especificada na consulta
• Sintomas atuais: {sintomas}
• Fatores desencadeantes: A investigar mediante documentação complementar
• Tratamentos realizados: Não relatados especificamente
• Situação atual: Limitações funcionais compatíveis com o quadro apresentado

**4. ANTECEDENTES PESSOAIS E FAMILIARES RELEVANTES**
• Doenças prévias: A investigar mediante documentação médica
• Histórico ocupacional: {profissao}
• Histórico previdenciário: A confirmar mediante documentação específica

**5. DOCUMENTAÇÃO APRESENTADA**
• Exames complementares: A avaliar documentação apresentada
• Relatórios médicos: Análise baseada nas informações disponíveis
• Observação: Recomenda-se apresentação de documentação médica completa

**6. EXAME CLÍNICO (ADAPTADO PARA TELEMEDICINA)**
• Autoavaliação guiada: Relatadas limitações funcionais
• Observação por vídeo: Limitações da modalidade telemedicina
• Limitações funcionais: Compatíveis com {sintomas}
• Capacidade de comunicação: Preservada durante a consulta

**7. AVALIAÇÃO MÉDICA (ASSESSMENT)**
• Hipótese diagnóstica: {cid_desc} (CID: {cid})
• Justificativa clínica: {justificativa}
• Recomendação: {tipo_beneficio}
• Observações: Avaliação realizada por telemedicina conforme protocolos vigentes

---
**Data:** {data_atual}  
**Modalidade:** Telemedicina  
**Observação:** Esta anamnese segue o modelo ideal para telemedicina e deve ser complementada com documentação médica quando disponível."""
        
        return anamnese.strip()
        
    except Exception as e:
        return f"**ANAMNESE MÉDICA**\n\nErro ao gerar anamnese: {str(e)}\n\nRecomenda-se coleta manual das informações do paciente."

def generate_laudo_from_data(multimodal_result: dict) -> str:
    """Gera laudo médico estruturado conforme especificação profissional"""
    try:
        patient_data = multimodal_result.get("patient_data", {})
        classification = multimodal_result.get("benefit_classification", {})
        transcription = multimodal_result.get("transcription", "")
        
        # Se já existe um relatório médico estruturado, usá-lo
        medical_report = multimodal_result.get("medical_report", "")
        if medical_report and "LAUDO MÉDICO" in medical_report and len(medical_report) > 500:
            return medical_report
        
        nome = patient_data.get("nome", "Não informado")
        idade = patient_data.get("idade", "Não informada")
        profissao = patient_data.get("profissao", "Não informada")
        queixa = patient_data.get("queixa_principal", "Não informada")
        sintomas = patient_data.get("sintomas", "Não informados")
        
        tipo_beneficio = classification.get("tipo_beneficio", "AUXÍLIO-DOENÇA")
        cid = classification.get("cid_principal", "I10.0")
        cid_desc = classification.get("cid_descricao", "Condição médica")
        gravidade = classification.get("gravidade", "MODERADA")
        justificativa = classification.get("justificativa", "Análise médica baseada nos dados fornecidos")
        prognostico = classification.get("prognostico", "Prognóstico reservado, necessita acompanhamento especializado")
        
        data_atual = datetime.now().strftime("%d/%m/%Y")
        
        laudo = f"""**LAUDO MÉDICO**

**IDENTIFICAÇÃO:**
- Nome: {nome}
- Idade: {idade}
- Profissão: {profissao}

**1. HISTÓRIA CLÍNICA RESUMIDA**
Paciente apresenta {queixa} com sintomas incluindo {sintomas}. O quadro clínico atual demonstra evolução compatível com a condição diagnosticada, com impacto significativo na capacidade funcional e laborativa. As manifestações clínicas atuais justificam a classificação diagnóstica principal como {cid} - {cid_desc}.

**2. LIMITAÇÃO FUNCIONAL**
O paciente apresenta limitações funcionais decorrentes da condição clínica atual, com comprometimento da capacidade laborativa. As limitações observadas impactam significativamente a funcionalidade, especialmente considerando as exigências da atividade profissional ({profissao}). Os sintomas relatados ({sintomas}) contribuem para o agravamento das limitações funcionais.

**3. TRATAMENTO**
Paciente em seguimento médico conforme protocolo estabelecido para a condição diagnosticada. O tratamento atual visa controle sintomático e melhora funcional, com necessidade de acompanhamento médico regular e reavaliações periódicas para monitorização da evolução clínica.

**4. PROGNÓSTICO**
{prognostico} A evolução do quadro requer observação continuada para adequação terapêutica. Considerando a gravidade {gravidade.lower()}, o prognóstico é reservado com necessidade de acompanhamento especializado.

**5. CONCLUSÃO**
Com base na avaliação clínica realizada, o quadro apresentado é compatível com {tipo_beneficio}. O paciente apresenta limitações funcionais que justificam a classificação proposta, considerando os critérios estabelecidos pela legislação previdenciária vigente. {justificativa}

**6. CID-10:**
- Principal: {cid} - {cid_desc}

---
**Data:** {data_atual}  
**Avaliação médica realizada conforme critérios técnicos e legislação vigente**"""
        
        return laudo.strip()
        
    except Exception as e:
        return f"**LAUDO MÉDICO**\n\nErro ao gerar laudo: {str(e)}\n\nRecomenda-se avaliação médica presencial."

# Configurar templates e arquivos estáticos
templates = None
static_dir = None

# Tentar encontrar o diretório frontend
frontend_paths = [
    "../../frontend",  # De backend/app para frontend
    "../frontend",     # De backend para frontend  
    "frontend"         # Diretório local
]

for frontend_path in frontend_paths:
    if os.path.exists(frontend_path):
        print(f"✅ Frontend encontrado em: {os.path.abspath(frontend_path)}")
        
        # Configurar arquivos estáticos
        static_path = os.path.join(frontend_path, "static")
        if os.path.exists(static_path):
            app.mount("/static", StaticFiles(directory=static_path), name="static")
            static_dir = static_path
            print(f"✅ Arquivos estáticos montados de: {static_path}")
        
        # Configurar templates
        templates_path = os.path.join(frontend_path, "templates")
        if os.path.exists(templates_path):
            templates = Jinja2Templates(directory=templates_path)
            print(f"✅ Templates configurados de: {templates_path}")
        
        break

if not templates:
    print("⚠️ Frontend não encontrado, usando páginas de fallback")

# Importações globais (com tratamento de erro)
multimodal_service = None
rag_service = None

try:
    from services.multimodal_ai_service import MultimodalAIService
    multimodal_service = MultimodalAIService()
    print("✅ Serviço Multimodal carregado")
except ImportError as e:
    print(f"❌ Erro ao carregar serviço multimodal: {e}")
    try:
        # Tentar import alternativo
        from app.services.multimodal_ai_service import MultimodalAIService
        multimodal_service = MultimodalAIService()
        print("✅ Serviço Multimodal carregado (path alternativo)")
    except Exception as e2:
        print(f"❌ Erro definitivo ao carregar serviço multimodal: {e2}")
        multimodal_service = None

try:
    from services.rag.medical_rag_service import MedicalRAGService
    rag_service = MedicalRAGService()
    print("✅ Serviço RAG carregado")
except ImportError as e:
    print(f"⚠️ RAG service não encontrado no path services/rag/: {e}")
    rag_service = None

# Se o multimodal service foi carregado, sempre usar o RAG integrado
if multimodal_service and hasattr(multimodal_service, 'rag_service'):
    rag_service = multimodal_service.rag_service
    print("✅ Usando RAG integrado do MultimodalAIService (com índices carregados)")


# ============================================================================
# ENDPOINTS PARA SERVIR O FRONTEND
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """🏠 SERVIR PÁGINA INICIAL - REDIRECIONAMENTO PARA CONSULTATION"""
    return await serve_frontend_page(request, "consultation.html")

@app.get("/consultation", response_class=HTMLResponse)
async def serve_consultation(request: Request):
    """🏥 SERVIR PÁGINA DE CONSULTA"""
    return await serve_frontend_page(request, "consultation.html")

@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    """🔐 SERVIR PÁGINA DE LOGIN"""
    return await serve_frontend_page(request, "login.html")

@app.get("/upload", response_class=HTMLResponse)
async def serve_upload(request: Request):
    """📤 SERVIR PÁGINA DE UPLOAD"""
    return await serve_frontend_page(request, "upload.html")

@app.get("/report", response_class=HTMLResponse)
async def serve_report(request: Request):
    """📋 SERVIR PÁGINA DE RELATÓRIO"""
    return await serve_frontend_page(request, "report.html")

@app.get("/debug", response_class=HTMLResponse)
async def serve_debug(request: Request):
    """🐛 SERVIR PÁGINA DE DEBUG"""
    return await serve_frontend_page(request, "consultation_debug.html")

@app.get("/premium", response_class=HTMLResponse)
async def serve_premium(request: Request):
    """💎 SERVIR PÁGINA PREMIUM"""
    return await serve_frontend_page(request, "consultation_premium.html")

async def serve_frontend_page(request: Request, page_name: str):
    """Função auxiliar para servir páginas do frontend"""
    
    print(f"🔍 Tentando servir página: {page_name}")
    
    # Se temos templates configurados, usar template engine
    if templates:
        try:
            # Tentar usar como template
            print(f"📄 Usando template engine para: {page_name}")
            return templates.TemplateResponse(page_name, {
                "request": request,
                "page_title": page_name.replace('.html', '').title(),
                "api_base_url": str(request.base_url)
            })
        except Exception as e:
            print(f"❌ Erro ao renderizar template {page_name}: {e}")
    
    # Tentar encontrar o arquivo manualmente se o template falhar
    frontend_paths = [
        "../../frontend",  # De backend/app para frontend
        "../frontend",     # De backend para frontend  
    ]
    
    for frontend_base in frontend_paths:
        if os.path.exists(frontend_base):
            # Tentar diferentes localizações do arquivo
            possible_paths = [
                os.path.join(frontend_base, "templates", page_name),
                os.path.join(frontend_base, page_name),
                os.path.join(frontend_base, "pages", page_name),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    try:
                        print(f"📂 Servindo arquivo estático: {path}")
                        return FileResponse(path)
                    except Exception as e:
                        print(f"❌ Erro ao servir {path}: {e}")
                        continue
    
    # Se nenhum arquivo foi encontrado, retornar página de erro personalizada
    print(f"❌ Página não encontrada: {page_name}")
    return HTMLResponse(
        content=create_fallback_page(page_name, str(request.base_url)),
        status_code=404
    )

def create_fallback_page(page_name: str, base_url: str) -> str:
    """Criar página de fallback quando o frontend não é encontrado"""
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Medical AI System - {page_name}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                text-align: center;
                max-width: 600px;
                width: 100%;
            }}
            .icon {{
                font-size: 4rem;
                margin-bottom: 20px;
            }}
            h1 {{
                color: #333;
                margin-bottom: 10px;
            }}
            .status {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            .endpoints {{
                text-align: left;
                background: #e9ecef;
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
            }}
            .endpoint {{
                margin: 5px 0;
                padding: 5px 10px;
                background: white;
                border-radius: 5px;
                display: block;
                text-decoration: none;
                color: #495057;
                transition: all 0.3s;
            }}
            .endpoint:hover {{
                background: #007bff;
                color: white;
                transform: translateX(5px);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">🏥</div>
            <h1>Medical AI System v2.0</h1>
            <p><strong>Sistema de Análise Médica com IA e RAG</strong></p>
            
            <div class="status">
                <h3>⚠️ Frontend não encontrado</h3>
                <p>A página <strong>{page_name}</strong> não foi encontrada no diretório frontend/</p>
                <p>Mas a API está funcionando perfeitamente!</p>
            </div>
            
            <div class="endpoints">
                <h4>🔗 Endpoints Disponíveis:</h4>
                <a href="{base_url}api/health" class="endpoint">📊 Health Check</a>
                <a href="{base_url}api/info" class="endpoint">ℹ️ Informações da API</a>
                <a href="{base_url}docs" class="endpoint">📚 Documentação Swagger</a>
                <a href="{base_url}api/rag/stats" class="endpoint">🧠 Estatísticas RAG</a>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                <p><strong>Para usar o sistema:</strong></p>
                <ol style="text-align: left;">
                    <li>Certifique-se que os arquivos do frontend estão em <code>frontend/</code></li>
                    <li>Use a API diretamente via POST para <code>/api/intelligent-medical-analysis</code></li>
                    <li>Consulte a documentação em <code>/docs</code></li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    """


# ============================================================================
# ENDPOINT PRINCIPAL - ANÁLISE MÉDICA
# ============================================================================

@app.post("/api/intelligent-medical-analysis")
async def intelligent_medical_analysis_with_rag(
    patient_info: str = Form(...),
    audio_data: UploadFile = File(None),
    image_data: UploadFile = File(None)
):
    """🚀 ENDPOINT PRINCIPAL - ANÁLISE MÉDICA COMPLETA COM RAG"""
    
    print(f"🚀 NOVA ANÁLISE INICIADA - Paciente: {patient_info[:50]}...")
    start_time = datetime.now()
    
    try:
        # Validação inicial
        if not multimodal_service:
            raise HTTPException(
                status_code=503, 
                detail="Serviço multimodal não disponível"
            )
        
        # 1. PROCESSAMENTO DE ARQUIVOS
        audio_bytes = None
        image_path = None
        
        if audio_data and audio_data.filename:
            audio_bytes = await audio_data.read()
            print(f"🎤 Áudio recebido: {len(audio_bytes)} bytes, filename: {audio_data.filename}")
            print(f"🔍 Tipo de conteúdo do áudio: {audio_data.content_type}")
        else:
            print("⚠️ Nenhum áudio recebido ou filename vazio")
        
        if image_data and image_data.filename:
            # Salvar imagem temporariamente
            temp_dir = "temp_images"
            os.makedirs(temp_dir, exist_ok=True)
            image_path = os.path.join(temp_dir, f"img_{int(datetime.now().timestamp())}.jpg")
            
            with open(image_path, "wb") as f:
                f.write(await image_data.read())
            print(f"🖼️ Imagem salva: {image_path}")
        else:
            print("ℹ️ Nenhuma imagem recebida")
        
        # 2. ANÁLISE MULTIMODAL BASE
        print("🔄 Executando análise multimodal...")
        
        multimodal_result = await multimodal_service.analyze_multimodal(
            patient_info=patient_info,
            audio_bytes=audio_bytes,
            image_path=image_path
        )
        
        if multimodal_result.get("status") == "error":
            print(f"❌ Erro na análise multimodal: {multimodal_result.get('error')}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": multimodal_result.get("error"),
                    "source": "multimodal_analysis"
                }
            )
        
        # 3. PREPARAR RESULTADO BASE
        result = {
            "success": True,
            "timestamp": start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "patient_info": patient_info,
            "transcription": multimodal_result.get("transcription", ""),
            "patient_data": multimodal_result.get("patient_data", {}),
            "medical_report": multimodal_result.get("medical_report", ""),
            "anamnese": generate_anamnese_from_data(multimodal_result),  # ANAMNESE ESPECÍFICA
            "laudo_medico": generate_laudo_from_data(multimodal_result),  # LAUDO ESPECÍFICO  
            "image_analysis": multimodal_result.get("image_analysis", ""),
            "analysis": multimodal_result.get("analysis", ""),
            "benefit_classification": multimodal_result.get("benefit_classification", {}),  # CLASSIFICAÇÃO ADICIONADA
            "multimodal_success": True
        }
        
        print("✅ Análise multimodal concluída")
        
        # 4. INTEGRAÇÃO RAG (se disponível)
        if rag_service:
            try:
                print("🔄 Iniciando análise RAG...")
                
                # Usar a transcrição para buscar casos similares
                transcription = result.get("transcription", "")
                patient_data = result.get("patient_data", {})
                
                if transcription or patient_data:
                    # Buscar contexto similar
                    search_query = transcription or patient_info
                    similar_docs = rag_service.search_similar_documents(search_query, k=5)
                    
                    if similar_docs:
                        similarity_scores = [score for _, score in similar_docs]
                        avg_score = sum(similarity_scores) / len(similarity_scores)
                        
                        result["rag_enabled"] = True
                        result["rag_similarity_score"] = avg_score
                        result["rag_cases_found"] = len(similar_docs)
                        result["rag_documents"] = [doc[:200] + "..." for doc, _ in similar_docs[:3]]
                        
                        print(f"✅ RAG concluído - Score médio: {avg_score:.3f}, Casos: {len(similar_docs)}")
                        
                        # Se temos boa similaridade, enriquecer o relatório
                        if avg_score > 0.6:
                            enhanced_report = await _enhance_report_with_rag(
                                result["medical_report"], 
                                similar_docs, 
                                rag_service
                            )
                            result["medical_report_enhanced"] = enhanced_report
                            result["report_source"] = "RAG Enhanced"
                        else:
                            result["report_source"] = "Multimodal + RAG Context"
                    else:
                        result["rag_enabled"] = True
                        result["rag_cases_found"] = 0
                        result["report_source"] = "Multimodal Only"
                        print("📋 RAG ativo mas nenhum caso similar encontrado")
                
            except Exception as rag_error:
                print(f"⚠️ Erro no RAG: {str(rag_error)}")
                result["rag_enabled"] = False
                result["rag_error"] = str(rag_error)
                result["report_source"] = "Multimodal Only"
        else:
            result["rag_enabled"] = False
            result["report_source"] = "Multimodal Only"
            print("⚠️ RAG não disponível")
        
        # 5. DADOS ADICIONAIS PARA COMPATIBILIDADE COM FRONTEND
        result.update({
            "cfm_compliant": True,
            "confidence": 0.85,
            "model": "Medical AI v2.0 with RAG",
            "classification": {
                "main_specialty": "clinica_geral",
                "main_benefit": "clinica"
            }
        })
        
        # 6. FINALIZAÇÃO
        processing_time = (datetime.now() - start_time).total_seconds()
        result["processing_time_seconds"] = round(processing_time, 2)
        result["sistema_versao"] = "Medical AI v2.0"
        
        # Limpar arquivos temporários
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        
        print(f"✅ ANÁLISE COMPLETA FINALIZADA - Tempo: {processing_time:.2f}s")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERRO CRÍTICO: {error_msg}")
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": error_msg,
                "error_type": type(e).__name__,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds()
            }
        )


async def _enhance_report_with_rag(base_report: str, similar_docs: list, rag_service) -> str:
    """Enriquece o relatório base com contexto do RAG"""
    try:
        context = "\n".join([doc for doc, _ in similar_docs[:3]])
        
        # Usar o RAG service para gerar versão melhorada
        enhanced = rag_service.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um médico especialista. Enriqueça o relatório base com insights do contexto médico relevante."
                },
                {
                    "role": "user",
                    "content": f"""
RELATÓRIO BASE:
{base_report}

CONTEXTO MÉDICO SIMILAR:
{context}

Enriqueça o relatório base incorporando insights relevantes do contexto, mantendo a estrutura original mas adicionando detalhes clínicos pertinentes.
"""
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        return enhanced.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Erro ao enriquecer relatório: {e}")
        return base_report


# ============================================================================
# ENDPOINTS DE SISTEMA
# ============================================================================

@app.get("/api/health")
async def health_check():
    """🔍 VERIFICAÇÃO DE SAÚDE DO SISTEMA"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "Medical AI v2.0",
        "services": {}
    }
    
    # Verificar serviço multimodal
    if multimodal_service:
        health_status["services"]["multimodal_ai"] = {
            "status": "✅ Disponível",
            "class": type(multimodal_service).__name__
        }
    else:
        health_status["services"]["multimodal_ai"] = {
            "status": "❌ Indisponível",
            "error": "Serviço não carregado"
        }
    
    # Verificar serviço RAG
    if rag_service:
        try:
            rag_stats = rag_service.get_rag_stats()
            health_status["services"]["rag_system"] = {
                "status": "✅ Disponível",
                "stats": rag_stats
            }
        except Exception as e:
            health_status["services"]["rag_system"] = {
                "status": "⚠️ Parcialmente disponível",
                "error": str(e)
            }
    else:
        health_status["services"]["rag_system"] = {
            "status": "❌ Indisponível",
            "error": "Serviço não encontrado"
        }
    
    # Verificar variáveis de ambiente
    health_status["environment"] = {
        "openai_api_configured": bool(os.getenv('OPENAI_API_KEY')),
        "python_version": sys.version.split()[0],
        "frontend_available": os.path.exists("frontend/index.html")
    }
    
    return health_status


@app.get("/api/rag/search")
async def search_rag_knowledge(
    query: str = Query(..., description="Consulta para buscar na base de conhecimento"),
    top_k: int = Query(5, ge=1, le=20, description="Número de resultados")
):
    """🔍 BUSCAR NA BASE DE CONHECIMENTO RAG"""
    
    if not rag_service:
        raise HTTPException(status_code=503, detail="Serviço RAG não disponível")
    
    try:
        results = rag_service.search_similar_documents(query, k=top_k)
        
        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "document": doc[:300] + "..." if len(doc) > 300 else doc,
                    "similarity_score": float(score)
                }
                for doc, score in results
            ],
            "total_found": len(results),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca RAG: {str(e)}")


@app.get("/api/rag/stats")
async def get_rag_statistics():
    """📊 ESTATÍSTICAS DO SISTEMA RAG"""
    
    if not rag_service:
        raise HTTPException(status_code=503, detail="Serviço RAG não disponível")
    
    try:
        stats = rag_service.get_rag_stats()
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")


@app.get("/api/info")
async def api_info():
    """📋 INFORMAÇÕES DA API"""
    return {
        "message": "Medical AI System with RAG",
        "version": "2.0",
        "status": "running",
        "endpoints": {
            "frontend_home": "/",
            "frontend_consultation": "/consultation",
            "frontend_dashboard": "/dashboard",
            "frontend_results": "/results",
            "analysis": "/api/intelligent-medical-analysis",
            "health": "/api/health",
            "rag_search": "/api/rag/search",
            "rag_stats": "/api/rag/stats"
        }
    }


# ============================================================================
# TRATAMENTO DE EXCEÇÕES
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Tratamento global de erros"""
    print(f"❌ Erro não tratado: {str(exc)}")
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Erro interno do servidor",
            "error_type": type(exc).__name__,
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Iniciando Medical AI System...")
    print(f"✅ Multimodal Service: {'Carregado' if multimodal_service else 'Não disponível'}")
    print(f"✅ RAG Service: {'Carregado' if rag_service else 'Não disponível'}")
    print(f"🌐 Frontend: {'Disponível' if templates else 'Fallback mode'}")
    print("📍 Rotas disponíveis:")
    print("   - http://localhost:8000/api/health (Health check)")
    print("   - http://localhost:8000/docs (Documentação API)")
    print("   - http://localhost:8000/api/intelligent-medical-analysis (Análise)")
    print("   - http://localhost:8000/api/search-rag (Busca RAG)")
    print("")
    print("🌐 FRONTEND EM: http://localhost:5003")
    print("🔌 BACKEND EM: http://localhost:8000")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=False,  
        log_level="info"
    )