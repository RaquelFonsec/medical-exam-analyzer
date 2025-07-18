import openai
from typing import Dict, Any
from ..config import settings

class LLMService:
    def __init__(self):
        # Configurar OpenAI com a nova versão
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4"
    
    async def generate_medical_report(self, exam_text: str, exam_type: str) -> str:
        """Gera relatório médico usando LLM"""
        try:
            prompt = self._create_medical_prompt(exam_text, exam_type)
            return await self._openai_generate(prompt)
                
        except Exception as e:
            # Fallback se der erro
            return f"""
## 📋 DADOS DO EXAME
- Tipo de exame: {exam_type}
- Status: Texto extraído com sucesso

## 🔍 TEXTO EXTRAÍDO
{exam_text[:800]}

## ⚠️ AVISO
Sistema processou o arquivo, mas houve problema na análise automática.
Por favor, consulte um médico para interpretação adequada dos resultados.

## 🏥 RECOMENDAÇÕES
- Levar este exame para consulta médica
- Solicitar interpretação profissional
- Manter histórico de exames

Erro técnico: {str(e)}
"""
    
    def _create_medical_prompt(self, exam_text: str, exam_type: str) -> str:
        """Cria prompt específico para análise médica"""
        return f"""
Você é um assistente médico especializado em análise de exames laboratoriais.

TIPO DE EXAME: {exam_type}

TEXTO EXTRAÍDO DO EXAME:
{exam_text}

Analise este exame e gere um relatório estruturado:

## 📋 DADOS DO EXAME
- Tipo de exame identificado
- Principais parâmetros encontrados

## 🔍 PRINCIPAIS ACHADOS
- Liste os valores numéricos identificados
- Identifique as unidades de medida
- Destaque parâmetros importantes

## ⚠️ ANÁLISE DOS VALORES
- Compare com valores de referência (quando disponíveis)
- Identifique possíveis alterações
- Categorize como: normal, elevado, diminuído

## 📊 INTERPRETAÇÃO CLÍNICA
- Significados clínicos dos achados
- Correlações entre parâmetros
- Possíveis implicações

## 🎯 PONTOS DE ATENÇÃO
- Valores que merecem atenção médica
- Recomendações para acompanhamento
- Sugestões de exames complementares

## ⚖️ LIMITAÇÕES
- Este relatório é apenas informativo
- Não substitui consulta médica profissional
- Interpretação automatizada pode ter limitações

IMPORTANTE: Sempre consulte um médico qualificado.
"""
    
    async def _openai_generate(self, prompt: str) -> str:
        """Gera resposta usando OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um assistente médico especializado em análise de exames."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"Erro OpenAI: {str(e)}")
