"""
Enhanced Exam Processor - Versão Corrigida para Integração
"""

import asyncio
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import UploadFile
import tempfile

# Importações com fallbacks
try:
    from .llm_service import LLMService
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

try:
    from .aws_textract_service import AWSTextractService, MedicalDocumentAnalyzer
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False

class EnhancedExamProcessor:
    """
    Processador de Exames Médicos Aprimorado
    Versão compatível com a estrutura atual
    """
    
    def __init__(self):
        print("🚀 Inicializando Enhanced Exam Processor...")
        
        # Serviços principais (com fallbacks)
        self.llm_service = LLMService() if LLM_AVAILABLE else None
        self.textract_service = AWSTextractService() if TEXTRACT_AVAILABLE else None
        self.medical_analyzer = MedicalDocumentAnalyzer() if TEXTRACT_AVAILABLE else None
        
        # Configurações específicas para exames médicos
        self.exam_types_config = {
            'hemograma': {
                'keywords': ['hemograma', 'leucócitos', 'hemácias', 'plaquetas', 'hematócrito'],
                'requires_tables': True,
                'handwriting_common': False
            },
            'glicemia': {
                'keywords': ['glicose', 'glicemia', 'diabetes', 'jejum'],
                'requires_tables': False,
                'handwriting_common': True
            },
            'receita_medica': {
                'keywords': ['receita', 'prescrição', 'medicamento', 'posologia'],
                'requires_tables': False,
                'handwriting_common': True
            },
            'laudo_imagem': {
                'keywords': ['raio-x', 'tomografia', 'ressonância', 'ultrassom'],
                'requires_tables': False,
                'handwriting_common': True
            }
        }
        
        print(f"✅ Enhanced Exam Processor inicializado")
        print(f"   LLM: {'Disponível' if LLM_AVAILABLE else 'Indisponível'}")
        print(f"   Textract: {'Disponível' if TEXTRACT_AVAILABLE else 'Indisponível'}")
    
    async def process_exam(self, file_input, exam_type: str = 'auto') -> Dict[str, Any]:
        """
        Processa exame médico - aceita UploadFile ou caminho de arquivo
        """
        try:
            # Determinar se é UploadFile ou string (caminho)
            if isinstance(file_input, str):
                # É um caminho de arquivo
                file_path = file_input
                filename = os.path.basename(file_path)
                temp_file_created = False
            else:
                # É um UploadFile
                file_path = await self._save_temp_file(file_input)
                filename = file_input.filename
                temp_file_created = True
            
            print(f"🔍 Processando arquivo: {filename}")
            print(f"📋 Tipo de exame: {exam_type}")
            
            try:
                # 1. ANALISAR ARQUIVO
                file_info = await self._analyze_file(file_path, filename)
                print(f"📄 Info do arquivo: {file_info['type']} | {file_info['size_mb']:.1f}MB")
                
                # 2. DETECTAR TIPO DE EXAME (se auto)
                if exam_type == 'auto':
                    exam_type = await self._detect_exam_type(file_path, file_info)
                    print(f"🔍 Tipo detectado: {exam_type}")
                
                # 3. EXTRAIR CONTEÚDO
                extraction_result = await self._extract_content(file_path, exam_type)
                
                # 4. ANÁLISE MÉDICA ESPECIALIZADA
                medical_analysis = await self._analyze_medical_content(extraction_result, exam_type)
                
                # 5. GERAR RELATÓRIO
                report = await self._generate_report(extraction_result, medical_analysis, exam_type)
                
                # 6. CALCULAR MÉTRICAS FINAIS
                final_metrics = self._calculate_final_metrics(extraction_result, medical_analysis, report)
                
                # 7. RESULTADO FINAL
                result = {
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                    "file_info": file_info,
                    "exam_type": exam_type,
                    "extracted_text": extraction_result['extracted_text'],
                    "tables": extraction_result.get('tables', []),
                    "forms": extraction_result.get('key_value_pairs', {}),
                    "medical_analysis": medical_analysis,
                    "document_classification": medical_analysis.get('document_type', exam_type),
                    "report": report,
                    "confidence": final_metrics['overall_confidence'],
                    "extraction_quality": final_metrics['extraction_quality'],
                    "medical_relevance": final_metrics['medical_relevance'],
                    "processing_service": extraction_result['service'],
                    "words_extracted": len(extraction_result['extracted_text'].split()),
                    "lines_extracted": len(extraction_result['extracted_text'].split('\n')),
                    "tables_found": len(extraction_result.get('tables', []))
                }
                
                print(f"✅ Processamento concluído - Confiança: {final_metrics['overall_confidence']:.1%}")
                return result
                
            finally:
                # Limpar arquivo temporário se foi criado
                if temp_file_created and os.path.exists(file_path):
                    os.remove(file_path)
            
        except Exception as e:
            print(f"❌ Erro no processamento: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "file_processed": filename if 'filename' in locals() else "unknown"
            }
    
    async def _save_temp_file(self, file: UploadFile) -> str:
        """Salvar UploadFile como arquivo temporário"""
        suffix = os.path.splitext(file.filename)[1] if file.filename else '.tmp'
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        
        try:
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            return temp_file.name
        finally:
            temp_file.close()
    
    async def _analyze_file(self, file_path: str, original_filename: str) -> Dict[str, Any]:
        """Analisar arquivo antes do processamento"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        file_size = os.path.getsize(file_path)
        file_extension = os.path.splitext(original_filename)[1].lower()
        
        # Detectar tipo de arquivo
        if file_extension == '.pdf':
            file_type = 'pdf'
        elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
            file_type = 'image'
        else:
            file_type = 'unknown'
        
        return {
            'path': file_path,
            'name': original_filename,
            'type': file_type,
            'extension': file_extension,
            'size_bytes': file_size,
            'size_mb': file_size / (1024 * 1024),
            'textract_compatible': file_type in ['pdf', 'image'] and file_size <= 10 * 1024 * 1024
        }
    
    async def _detect_exam_type(self, file_path: str, file_info: Dict) -> str:
        """Detectar tipo de exame baseado no nome do arquivo"""
        
        filename_lower = file_info['name'].lower()
        
        # Detecção baseada no nome do arquivo
        for exam_type, config in self.exam_types_config.items():
            for keyword in config['keywords']:
                if keyword in filename_lower:
                    return exam_type
        
        return 'exame_generico'
    
    async def _extract_content(self, file_path: str, exam_type: str) -> Dict[str, Any]:
        """Extrair conteúdo usando AWS Textract ou fallback"""
        
        if TEXTRACT_AVAILABLE and self.textract_service:
            try:
                # Usar o analisador médico especializado
                if self.medical_analyzer:
                    result = await self.medical_analyzer.analyze_medical_document(file_path)
                else:
                    result = await self.textract_service.extract_text_from_document(file_path)
                
                if result['success']:
                    result['service'] = 'AWS Textract'
                    return result
                else:
                    print(f"⚠️ Textract falhou: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"⚠️ Erro no Textract: {e}")
        
        # Fallback: extração básica
        return await self._basic_extraction(file_path)
    
    async def _basic_extraction(self, file_path: str) -> Dict[str, Any]:
        """Extração básica como fallback"""
        
        try:
            # Para PDFs, tentar extrair texto simples
            if file_path.lower().endswith('.pdf'):
                text = await self._extract_pdf_text(file_path)
            else:
                text = f"Conteúdo extraído de {os.path.basename(file_path)} (método básico)"
            
            return {
                'success': True,
                'service': 'Basic Extraction',
                'extracted_text': text,
                'tables': [],
                'key_value_pairs': {},
                'confidence': 0.7
            }
            
        except Exception as e:
            return {
                'success': False,
                'service': 'Failed Extraction',
                'extracted_text': '',
                'tables': [],
                'key_value_pairs': {},
                'confidence': 0.0,
                'error': str(e)
            }
    
    async def _extract_pdf_text(self, file_path: str) -> str:
        """Extrair texto básico de PDF"""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                return text.strip()
                
        except ImportError:
            return "Extração de PDF requer PyPDF2. Instale com: pip install PyPDF2"
        except Exception as e:
            return f"Erro extraindo PDF: {str(e)}"
    
    async def _analyze_medical_content(self, extraction_result: Dict, exam_type: str) -> Dict[str, Any]:
        """Análise médica especializada"""
        
        if 'medical_analysis' in extraction_result:
            # Já foi analisado pelo MedicalDocumentAnalyzer
            return extraction_result['medical_analysis']
        
        # Análise básica
        text = extraction_result['extracted_text'].lower()
        
        analysis = {
            'document_type': exam_type,
            'text_length': len(extraction_result['extracted_text']),
            'has_medical_content': any(term in text for term in ['hemoglobina', 'glicose', 'exame', 'resultado']),
            'confidence_score': extraction_result.get('confidence', 0.7),
            'relevance_score': 0.8 if any(term in text for term in ['paciente', 'resultado', 'exame']) else 0.5
        }
        
        # Análise específica por tipo
        if exam_type == 'hemograma':
            analysis.update(self._analyze_hemograma(text))
        elif exam_type == 'glicemia':
            analysis.update(self._analyze_glicemia(text))
        elif exam_type == 'receita_medica':
            analysis.update(self._analyze_prescription(text))
        
        return analysis
    
    def _analyze_hemograma(self, text: str) -> Dict[str, Any]:
        """Análise específica para hemograma"""
        import re
        
        findings = []
        hemograma_values = {
            'hemoglobina': r'h[be]moglobina[:\s]*(\d+[\.,]\d*)',
            'hematocrito': r'hematócrito[:\s]*(\d+[\.,]\d*)',
            'leucocitos': r'leucócitos[:\s]*(\d+[\.,]?\d*)',
            'plaquetas': r'plaquetas[:\s]*(\d+[\.,]?\d*)'
        }
        
        for param, pattern in hemograma_values.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                findings.append(f"{param}: {matches[0]}")
        
        return {
            'specific_findings': findings,
            'is_complete_hemograma': len(findings) >= 3,
            'values_found': len(findings)
        }
    
    def _analyze_glicemia(self, text: str) -> Dict[str, Any]:
        """Análise específica para glicemia"""
        import re
        
        glucose_pattern = r'glic[oe]s[ea][:\s]*(\d+)'
        glucose_matches = re.findall(glucose_pattern, text, re.IGNORECASE)
        
        findings = []
        if glucose_matches:
            value = int(glucose_matches[0])
            findings.append(f"Glicose: {value} mg/dL")
            
            if value < 70:
                findings.append("Classificação: Hipoglicemia")
            elif value <= 99:
                findings.append("Classificação: Normal")
            elif value <= 125:
                findings.append("Classificação: Pré-diabetes")
            else:
                findings.append("Classificação: Diabetes")
        
        return {
            'specific_findings': findings,
            'glucose_value': int(glucose_matches[0]) if glucose_matches else None
        }
    
    def _analyze_prescription(self, text: str) -> Dict[str, Any]:
        """Análise específica para receitas médicas"""
        import re
        
        medication_patterns = [
            r'(\w+)\s+(\d+\s*mg)',
            r'(\w+)\s+(\d+\s*ml)',
            r'(\w+).*?(\d+\s*vezes?\s*ao?\s*dia)'
        ]
        
        medications = []
        for pattern in medication_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            medications.extend([f"{med} - {dose}" for med, dose in matches])
        
        return {
            'specific_findings': medications,
            'medications_count': len(medications),
            'has_dosage_info': any('mg' in med or 'ml' in med for med in medications)
        }
    
    async def _generate_report(self, extraction_result: Dict, medical_analysis: Dict, exam_type: str) -> str:
        """Gerar relatório usando LLM ou método básico"""
        
        if LLM_AVAILABLE and self.llm_service:
            try:
                enhanced_context = f"""
TIPO DE EXAME: {exam_type}
CONFIANÇA DA EXTRAÇÃO: {extraction_result.get('confidence', 0):.1%}
SERVIÇO USADO: {extraction_result.get('service', 'unknown')}

TEXTO EXTRAÍDO:
{extraction_result['extracted_text'][:500]}...

ANÁLISE MÉDICA:
- Tipo de documento: {medical_analysis.get('document_type', 'unknown')}
- Achados específicos: {medical_analysis.get('specific_findings', [])}
"""
                
                return await self.llm_service.generate_medical_report(enhanced_context, exam_type)
            except Exception as e:
                print(f"⚠️ LLM falhou: {e}")
        
        # Relatório básico
        return self._generate_basic_report(extraction_result, medical_analysis, exam_type)
    
    def _generate_basic_report(self, extraction_result: Dict, medical_analysis: Dict, exam_type: str) -> str:
        """Gerar relatório básico sem LLM"""
        
        report_lines = [
            f"📋 RELATÓRIO DE ANÁLISE - {exam_type.upper()}",
            "=" * 50,
            f"⏰ Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"🔧 Serviço: {extraction_result.get('service', 'Básico')}",
            f"📊 Confiança: {extraction_result.get('confidence', 0):.1%}",
            "",
            "📝 CONTEÚDO EXTRAÍDO:",
            f"Caracteres: {len(extraction_result['extracted_text'])}",
            f"Palavras: {len(extraction_result['extracted_text'].split())}",
            ""
        ]
        
        # Adicionar achados específicos
        findings = medical_analysis.get('specific_findings', [])
        if findings:
            report_lines.append("🔍 ACHADOS ESPECÍFICOS:")
            for finding in findings:
                report_lines.append(f"  • {finding}")
            report_lines.append("")
        
        report_lines.extend([
            "⚠️ IMPORTANTE:",
            "Esta análise é automatizada e não substitui avaliação médica profissional.",
            "Em caso de dúvidas, consulte um médico especialista."
        ])
        
        return '\n'.join(report_lines)
    
    def _calculate_final_metrics(self, extraction_result: Dict, medical_analysis: Dict, report: str) -> Dict[str, Any]:
        """Calcular métricas finais de qualidade"""
        
        extraction_confidence = extraction_result.get('confidence', 0)
        medical_relevance = medical_analysis.get('relevance_score', 0.7)
        text_quality = min(1.0, len(extraction_result['extracted_text']) / 1000)
        
        overall_confidence = (extraction_confidence * 0.4 + medical_relevance * 0.3 + text_quality * 0.3)
        
        return {
            'overall_confidence': overall_confidence,
            'extraction_quality': extraction_confidence,
            'medical_relevance': medical_relevance,
            'text_quality': text_quality,
            'has_structured_data': len(extraction_result.get('tables', [])) > 0,
            'processing_complete': len(report) > 100
        }

# Funções de conveniência para compatibilidade
async def process_medical_exam(file_path: str, exam_type: str = 'auto') -> Dict[str, Any]:
    """Função de conveniência para processar exame médico"""
    processor = EnhancedExamProcessor()
    return await processor.process_exam(file_path, exam_type)

print("✅ Enhanced Exam Processor implementado com fallbacks!")
