import openai
import os
import tempfile
from typing import Dict, Any

class TranscriptionService:
    """Serviço de transcrição com Whisper"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcrição REAL com Whisper API"""
        try:
            print(f"🎤 Transcrevendo: {audio_file_path}")
            
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"
                )
            
            transcription_text = transcript.text
            print(f"✅ Transcrição concluída: {len(transcription_text)} caracteres")
            
            return {
                "transcription": transcription_text,
                "language": "pt",
                "model": "whisper-1",
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Erro Whisper: {str(e)}")
            # Fallback para simulação
            return {
                "transcription": "Simulação: Paciente relata sintomas conforme consulta médica",
                "language": "pt",
                "model": "fallback",
                "success": False,
                "error": str(e)
            }
    
    async def transcribe_audio_bytes(self, audio_bytes: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """Transcrever áudio a partir de bytes"""
        try:
            # Salvar temporariamente
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            # Transcrever
            result = await self.transcribe_audio(temp_path)
            
            # Limpar arquivo temporário
            os.unlink(temp_path)
            
            return result
            
        except Exception as e:
            return {
                "transcription": f"Erro na transcrição: {str(e)}",
                "success": False,
                "error": str(e)
            }
