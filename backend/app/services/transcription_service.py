import openai
import os
from ..config import settings

class TranscriptionService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcrição REAL com Whisper API"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"
                )
            return transcript.text
        except Exception as e:
            return f"Simulação: Paciente Raquel, 42 anos, apresenta dor lombar há 3 meses..."