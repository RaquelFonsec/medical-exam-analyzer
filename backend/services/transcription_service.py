import openai
import os
import tempfile
from typing import Union
from ..config import settings

class TranscriptionService:
    def __init__(self):
        """Inicializar serviço de transcrição com Whisper API"""
        try:
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            print("✅ TranscriptionService inicializado com OpenAI Whisper")
        except Exception as e:
            print(f"❌ Erro ao inicializar TranscriptionService: {e}")
            self.client = None
    
    async def transcribe_audio(self, audio_input: Union[str, bytes]) -> str:
        """
        Transcrição de áudio usando OpenAI Whisper API
        
        Args:
            audio_input: Pode ser:
                - str: Caminho para arquivo de áudio
                - bytes: Dados binários do áudio
        
        Returns:
            str: Texto transcrito ou string vazia em caso de erro
        """
        if not self.client:
            print("❌ Cliente OpenAI não disponível para transcrição")
            return ""
        
        temp_file_path = None
        
        try:
            # Se recebeu bytes, salvar em arquivo temporário
            if isinstance(audio_input, bytes):
                print(f"🎤 Processando áudio: {len(audio_input)} bytes")
                
                # Validar se os bytes não estão vazios
                if len(audio_input) < 100:
                    print("⚠️ Arquivo de áudio muito pequeno - possivelmente vazio")
                    return ""
                
                # Validar tamanho mínimo para áudio real
                if len(audio_input) < 1000:
                    print("⚠️ Áudio muito pequeno - pode não conter fala suficiente")
                
                # Criar arquivo temporário com extensão baseada no conteúdo
                file_extension = self._detect_audio_format(audio_input)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                    tmp_file.write(audio_input)
                    temp_file_path = tmp_file.name
                    
                audio_file_path = temp_file_path
                print(f"📁 Áudio salvo temporariamente: {audio_file_path}")
                
            # Se recebeu string (caminho do arquivo)
            elif isinstance(audio_input, str):
                audio_file_path = audio_input
                print(f"📁 Processando arquivo: {audio_file_path}")
                
                # Verificar se o arquivo existe
                if not os.path.exists(audio_file_path):
                    print(f"❌ Arquivo não encontrado: {audio_file_path}")
                    return ""
            else:
                print(f"❌ Tipo de entrada inválido: {type(audio_input)}")
                return ""
            
            # Verificar tamanho do arquivo
            file_size = os.path.getsize(audio_file_path)
            print(f"📊 Tamanho do arquivo: {file_size} bytes")
            
            if file_size == 0:
                print("❌ Arquivo de áudio vazio")
                return ""
            
            # Validação adicional para arquivos pequenos
            if file_size < 10000:  # Menos de 10KB
                print("⚠️ Arquivo muito pequeno - pode não conter fala audível")
                print("💡 Para melhor resultado: grave pelo menos 2-3 segundos de fala clara")
            
            # Realizar transcrição com Whisper API
            print("🤖 Iniciando transcrição com Whisper API...")
            
            with open(audio_file_path, "rb") as audio_file:
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
                print(f"✅ Transcrição concluída: {len(transcribed_text)} caracteres")
                print(f"📝 Preview: {transcribed_text[:150]}...")
                
                # Verificar se parece ser uma transcrição válida
                if len(transcribed_text) < 5:
                    print("⚠️ Transcrição muito curta - pode não ter capturado fala suficiente")
                elif not any(char.isalpha() for char in transcribed_text):
                    print("⚠️ Transcrição não contém letras - pode ser ruído")
                else:
                    print("✅ Transcrição parece válida")
                    
            else:
                print("⚠️ Transcrição retornou vazio")
                print("💡 Possíveis causas:")
                print("   - Áudio sem fala audível")
                print("   - Gravação muito baixa")
                print("   - Formato de áudio não ideal")
                print("   - Ruído excessivo")
            
            return transcribed_text
            
        except openai.BadRequestError as e:
            error_msg = str(e)
            print(f"❌ Erro de requisição OpenAI: {error_msg}")
            
            if "audio_too_short" in error_msg:
                print("💡 SOLUÇÃO: Grave pelo menos 0.1 segundos (idealmente 2-3 segundos) de fala clara")
            elif "invalid_file" in error_msg:
                print("💡 SOLUÇÃO: Use formatos suportados (mp3, mp4, wav, webm, m4a)")
            else:
                print("💡 Possíveis causas: formato não suportado, arquivo corrompido, sem fala audível")
            
            return ""
            
        except openai.AuthenticationError as e:
            print(f"❌ Erro de autenticação OpenAI: {e}")
            print("💡 Verifique se a OPENAI_API_KEY está correta e ativa")
            return ""
            
        except openai.RateLimitError as e:
            print(f"❌ Limite de rate da OpenAI excedido: {e}")
            print("💡 Aguarde alguns segundos e tente novamente")
            return ""
            
        except Exception as e:
            print(f"❌ Erro inesperado na transcrição: {type(e).__name__}: {e}")
            print("💡 Verifique:")
            print("   - Formato do áudio (suportados: mp3, mp4, wav, webm, m4a)")
            print("   - Qualidade da gravação (sem muito ruído)")
            print("   - Duração mínima (pelo menos 1-2 segundos)")
            print("   - Conexão com a internet (para API OpenAI)")
            return ""
            
        finally:
            # Limpar arquivo temporário se foi criado
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    print("🗑️ Arquivo temporário removido")
                except Exception as e:
                    print(f"⚠️ Erro ao remover arquivo temporário: {e}")
    
    def _detect_audio_format(self, audio_bytes: bytes) -> str:
        """
        Detecta o formato do áudio baseado nos bytes iniciais
        """
        if len(audio_bytes) < 4:
            return ".wav"  # Default fallback
        
        # Magic numbers para diferentes formatos
        if audio_bytes[:4] == b'RIFF' and audio_bytes[8:12] == b'WAVE':
            return ".wav"
        elif audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
            return ".mp3"
        elif audio_bytes[:4] == b'ftyp':
            return ".m4a"
        elif audio_bytes[:4] == b'\x1a\x45\xdf\xa3':  # WebM
            return ".webm"
        elif audio_bytes[:4] == b'OggS':
            return ".ogg"
        else:
            print(f"⚠️ Formato não detectado, usando .webm como padrão")
            return ".webm"  # WebM é comum para captura de navegador
    
    # Método para compatibilidade com sistema dual
    async def transcribe_audio_bytes(self, audio_bytes: bytes, filename: str, audio_type: str = "consultation") -> dict:
        """
        Método específico para transcrição de bytes com metadados
        
        Args:
            audio_bytes: Dados binários do áudio
            filename: Nome do arquivo original
            audio_type: Tipo do áudio (consultation, doctor, patient, etc.)
        
        Returns:
            dict: Resultado estruturado da transcrição
        """
        try:
            print(f"🎤 Transcrevendo {audio_type}: {filename} ({len(audio_bytes)} bytes)")
            
            transcription = await self.transcribe_audio(audio_bytes)
            
            if transcription:
                return {
                    'success': True,
                    'transcription': transcription,
                    'audio_type': audio_type,
                    'filename': filename,
                    'file_size': len(audio_bytes),
                    'transcription_length': len(transcription)
                }
            else:
                return {
                    'success': False,
                    'error': 'Transcrição vazia ou falhou',
                    'audio_type': audio_type,
                    'filename': filename,
                    'file_size': len(audio_bytes),
                    'transcription_length': 0
                }
            
        except Exception as e:
            print(f"❌ Erro na transcrição de bytes para {audio_type}: {e}")
            return {
                'success': False,
                'error': str(e),
                'audio_type': audio_type,
                'filename': filename,
                'file_size': len(audio_bytes),
                'transcription_length': 0
            }
    
    def test_whisper_connection(self) -> bool:
        """Testa se a conexão com Whisper API está funcionando"""
        try:
            if not self.client:
                return False
            
            # Criar um arquivo de áudio vazio para teste
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                # Criar um arquivo WAV mínimo (apenas para teste de conexão)
                # Não vamos realmente fazer transcrição, só verificar se a API responde
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
            print(f"❌ Erro no teste Whisper: {e}")
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