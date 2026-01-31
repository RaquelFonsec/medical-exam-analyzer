
import openai
import os
import tempfile
from typing import Union, Dict, Any
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        """Inicializar serviço de transcrição com Whisper API"""
        try:
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("TranscriptionService inicializado com OpenAI Whisper")
        except Exception as e:
            logger.error(f"Erro ao inicializar TranscriptionService: {e}")
            self.client = None
    
    async def transcribe_audio_bytes(self, audio_bytes: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """
        Transcrição de áudio usando OpenAI Whisper API
        
        Args:
            audio_bytes: Dados binários do áudio
            filename: Nome do arquivo para referência
        
        Returns:
            Dict: Resultado da transcrição com metadados
        """
        if not self.client:
            logger.error("Cliente OpenAI não disponível para transcrição")
            return {
                "transcription": "Erro: Cliente OpenAI não configurado",
                "success": False,
                "error": "Cliente não inicializado"
            }
        
        temp_file_path = None
        
        try:
            logger.info(f"Processando áudio: {len(audio_bytes)} bytes")
            
            # Validar se os bytes não estão vazios
            if len(audio_bytes) < 100:
                logger.warning("Arquivo de áudio muito pequeno - possivelmente vazio")
                return {
                    "transcription": "Erro: Arquivo de áudio muito pequeno",
                    "success": False,
                    "error": "Arquivo muito pequeno"
                }
            
            # Validar tamanho mínimo para áudio real
            if len(audio_bytes) < 1000:
                logger.warning("Áudio muito pequeno - pode não conter fala suficiente")
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_bytes)
                temp_file_path = tmp_file.name
                
            logger.info(f"Áudio salvo temporariamente: {temp_file_path}")
            
            # Verificar tamanho do arquivo
            file_size = os.path.getsize(temp_file_path)
            logger.info(f"Tamanho do arquivo: {file_size} bytes")
            
            if file_size == 0:
                logger.error("Arquivo de áudio vazio")
                return {
                    "transcription": "Erro: Arquivo de áudio vazio",
                    "success": False,
                    "error": "Arquivo vazio"
                }
            
            # Validação adicional para arquivos pequenos
            if file_size < 10000:  # Menos de 10KB
                logger.warning("Arquivo muito pequeno - pode não conter fala audível")
            
            # Realizar transcrição com Whisper API
            logger.info("Iniciando transcrição com Whisper API...")
            
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt",  # Português
                    response_format="text",
                    temperature=0.1,  # Mais conservador para melhor precisão
                    prompt="Esta é uma consulta médica em português. O paciente está relatando sintomas e histórico médico para o médico."  # Contexto para melhor transcrição
                )
            
            # O Whisper retorna um objeto, extrair o texto
            transcribed_text = transcript if isinstance(transcript, str) else str(transcript)
            
            # Limpar e validar o texto transcrito
            transcribed_text = transcribed_text.strip()
            
            if transcribed_text:
                logger.info(f"Transcrição concluída: {len(transcribed_text)} caracteres")
                logger.info(f"Preview: {transcribed_text[:150]}...")
                
                # Verificar se parece ser uma transcrição válida
                if len(transcribed_text) < 5:
                    logger.warning("Transcrição muito curta - pode não ter capturado fala suficiente")
                elif not any(char.isalpha() for char in transcribed_text):
                    logger.warning("Transcrição não contém letras - pode ser ruído")
                else:
                    logger.info("Transcrição parece válida")
                
                return {
                    "transcription": transcribed_text,
                    "language": "pt",
                    "model": "whisper-1",
                    "success": True,
                    "character_count": len(transcribed_text),
                    "filename": filename
                }
                    
            else:
                logger.warning("Transcrição retornou vazio")
                return {
                    "transcription": "Nenhum texto foi detectado no áudio. Verifique a qualidade da gravação.",
                    "success": False,
                    "error": "Transcrição vazia"
                }
            
        except openai.BadRequestError as e:
            error_msg = str(e)
            logger.error(f"Erro de requisição OpenAI: {error_msg}")
            
            if "audio_too_short" in error_msg:
                suggestion = "Grave pelo menos 0.1 segundos (idealmente 2-3 segundos) de fala clara"
            elif "invalid_file" in error_msg:
                suggestion = "Use formatos suportados (mp3, mp4, wav, webm, m4a)"
            else:
                suggestion = "Verifique o formato do arquivo e qualidade da gravação"
            
            return {
                "transcription": f"Erro na transcrição: {error_msg}",
                "success": False,
                "error": error_msg,
                "suggestion": suggestion
            }
            
        except openai.AuthenticationError as e:
            logger.error(f"Erro de autenticação OpenAI: {e}")
            return {
                "transcription": "Erro de autenticação. Verifique se a OPENAI_API_KEY está correta.",
                "success": False,
                "error": str(e)
            }
            
        except openai.RateLimitError as e:
            logger.error(f"Limite de rate da OpenAI excedido: {e}")
            return {
                "transcription": "Limite de requisições excedido. Aguarde alguns segundos e tente novamente.",
                "success": False,
                "error": str(e)
            }
            
        except Exception as e:
            logger.error(f"Erro inesperado na transcrição: {type(e).__name__}: {e}")
            return {
                "transcription": f"Erro inesperado: {str(e)}",
                "success": False,
                "error": str(e)
            }
            
        finally:
            # Limpar arquivo temporário se foi criado
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info("Arquivo temporário removido")
                except Exception as e:
                    logger.warning(f"Erro ao remover arquivo temporário: {e}")
    
    def test_whisper_connection(self) -> bool:
        """Testa se a conexão com Whisper API está funcionando"""
        try:
            if not self.client:
                return False
            
            # Criar um arquivo de áudio vazio para teste
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(b'')
                test_file = tmp.name
            
            try:
                # Teste básico - vai falhar mas nos dirá se a API está acessível
                with open(test_file, "rb") as f:
                    self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
            except openai.BadRequestError:
                # Erro esperado com arquivo vazio - mas API está acessível
                return True
            except openai.AuthenticationError:
                # Problema de autenticação
                return False
            finally:
                os.unlink(test_file)
            
            return True
            
        except Exception as e:
            logger.error(f"Erro no teste Whisper: {e}")
            return False

    def validate_audio_quality(self, audio_input: Union[str, bytes]) -> dict:
        """
        Valida a qualidade do áudio antes da transcrição
        
        Returns:
            dict: Informações sobre a qualidade do áudio
        """
        try:
            if isinstance(audio_input, bytes):
                size = len(audio_input)
                file_path = None
            else:
                file_path = audio_input
                size = os.path.getsize(file_path) if os.path.exists(audio_input) else 0
            
            # Análise básica
            quality = {
                "valid": True,
                "size_bytes": size,
                "estimated_duration": size / 44100 / 2 if size > 44 else 0,  # Estimativa grosseira
                "warnings": [],
                "recommendations": []
            }
            
            # Verificações
            if size < 1000:
                quality["warnings"].append("Arquivo muito pequeno")
                quality["recommendations"].append("Grave pelo menos 2-3 segundos de fala")
            
            if size < 100:
                quality["valid"] = False
                quality["warnings"].append("Arquivo vazio ou corrompido")
            
            if size > 25 * 1024 * 1024:  # 25MB
                quality["warnings"].append("Arquivo muito grande - pode demorar para processar")
                quality["recommendations"].append("Para melhor performance, grave áudios de até 2-3 minutos")
            
            return quality
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "warnings": ["Erro ao analisar áudio"],
                "recommendations": ["Verifique o formato e integridade do arquivo"]
            }
    
    def get_health_status(self) -> Dict:
        """Status de saúde do serviço"""
        return {
            'service': 'OpenAI Whisper API',
            'status': 'Ready' if self.client else 'Not configured',
            'features': ['Portuguese language', 'Medical context', 'High accuracy']
        }
    
    def get_status(self) -> str:
        """Status simples"""
        return "Ready" if self.client else "Not configured"
