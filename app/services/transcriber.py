import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from groq import Groq
from google import genai
from google.genai import types
from app.core.config import settings
from app.core.models import FullTranscript, TranscriptSegment, WordTimestamp

class TranscriberService:
    def __init__(self):
        self.groq_key = settings.GROQ_API_KEY
        self.gemini_key = settings.GEMINI_API_KEY

    def _ensure_audio_under_25mb(self, audio_path: str) -> str:
        """
        Groq has a 25MB file upload limit.
        If the file exceeds 24MB, compress to 32kbps mono mp3.
        A 2-hour audio at 32k mono is only ~28MB, 1 hour is ~14MB!
        """
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        if file_size_mb < 24.0:
            return audio_path

        compressed_path = audio_path.rsplit(".", 1)[0] + "_compressed.mp3"
        cmd = [
            settings.FFMPEG_CMD,
            "-y",
            "-i", audio_path,
            "-vn",
            "-ac", "1",           # mono
            "-ar", "16000",       # 16kHz sample rate optimal for Whisper
            "-b:a", "32k",        # 32kbps
            compressed_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(compressed_path):
            return compressed_path
        return audio_path

    def transcribe_with_groq(self, audio_path: str, custom_key: Optional[str] = None) -> FullTranscript:
        """
        Transcribes audio using Groq Whisper API (whisper-large-v3-turbo).
        Returns full text, segments, and word-level timestamps for animated karaoke subtitles.
        """
        api_key = custom_key or self.groq_key
        if not api_key:
            raise ValueError("No se proporcionó una clave de API de Groq (GROQ_API_KEY).")

        audio_file_to_send = self._ensure_audio_under_25mb(audio_path)
        client = Groq(api_key=api_key)

        with open(audio_file_to_send, "rb") as file_data:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_file_to_send), file_data.read()),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )

        # Parse segments and word timestamps
        segments: List[TranscriptSegment] = []
        raw_words = getattr(transcription, "words", []) or []
        
        # Build list of WordTimestamp
        all_words: List[WordTimestamp] = []
        for w in raw_words:
            word_str = w.get("word") if isinstance(w, dict) else getattr(w, "word", "")
            w_start = float(w.get("start", 0.0) if isinstance(w, dict) else getattr(w, "start", 0.0))
            w_end = float(w.get("end", 0.0) if isinstance(w, dict) else getattr(w, "end", 0.0))
            if word_str.strip():
                all_words.append(WordTimestamp(word=word_str.strip(), start=w_start, end=w_end))

        raw_segments = getattr(transcription, "segments", []) or []
        for s in raw_segments:
            s_start = float(s.get("start", 0.0) if isinstance(s, dict) else getattr(s, "start", 0.0))
            s_end = float(s.get("end", 0.0) if isinstance(s, dict) else getattr(s, "end", 0.0))
            s_text = (s.get("text") if isinstance(s, dict) else getattr(s, "text", "")).strip()
            
            # Match words falling within this segment
            seg_words = [w for w in all_words if s_start <= w.start <= s_end + 0.1]
            segments.append(TranscriptSegment(
                id=s.get("id", len(segments)) if isinstance(s, dict) else getattr(s, "id", len(segments)),
                start=s_start,
                end=s_end,
                text=s_text,
                words=seg_words
            ))

        full_text = getattr(transcription, "text", "") or " ".join([s.text for s in segments])
        duration = float(getattr(transcription, "duration", 0.0) or (segments[-1].end if segments else 0.0))

        return FullTranscript(
            language=getattr(transcription, "language", "es") or "es",
            duration=duration,
            text=full_text,
            segments=segments
        )

    def transcribe_with_gemini(self, audio_path: str, custom_key: Optional[str] = None) -> FullTranscript:
        """
        Fallback transcription using Google Gemini 2.5 Flash / 1.5 Flash multimodal audio capability.
        """
        api_key = custom_key or self.gemini_key
        if not api_key:
            raise ValueError("No se proporcionó una clave de API de Gemini (GEMINI_API_KEY).")

        audio_file_to_send = self._ensure_audio_under_25mb(audio_path)
        client = genai.Client(api_key=api_key)

        uploaded_file = client.files.upload(file=audio_file_to_send)

        prompt = """
        Transcribe este audio completo en formato JSON con la siguiente estructura exacta:
        {
          "language": "es",
          "segments": [
            {
              "start": 0.0,
              "end": 4.5,
              "text": "Texto hablado aquí...",
              "words": [
                {"word": "Texto", "start": 0.0, "end": 0.5},
                {"word": "hablado", "start": 0.6, "end": 1.2}
              ]
            }
          ]
        }
        Asegúrate de incluir marcas de tiempo precisas en segundos para cada segmento y palabras claves. Responde ÚNICAMENTE el JSON.
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        import json
        data = json.loads(response.text)
        
        segments: List[TranscriptSegment] = []
        for s in data.get("segments", []):
            words = [WordTimestamp(word=w["word"], start=float(w["start"]), end=float(w["end"])) for w in s.get("words", [])]
            segments.append(TranscriptSegment(
                start=float(s["start"]),
                end=float(s["end"]),
                text=s["text"],
                words=words
            ))

        total_duration = segments[-1].end if segments else 0.0
        full_text = " ".join([s.text for s in segments])

        return FullTranscript(
            language=data.get("language", "es"),
            duration=total_duration,
            text=full_text,
            segments=segments
        )

    def transcribe(self, audio_path: str, groq_key: Optional[str] = None, gemini_key: Optional[str] = None) -> FullTranscript:
        """Attempts transcription with Groq first (blazing fast + word timestamps), falls back to Gemini."""
        if groq_key or self.groq_key:
            return self.transcribe_with_groq(audio_path, custom_key=groq_key)
        elif gemini_key or self.gemini_key:
            return self.transcribe_with_gemini(audio_path, custom_key=gemini_key)
        else:
            raise ValueError("Debes ingresar una clave API de Groq (Recomendada, gratis en console.groq.com) o de Google Gemini en la barra de Ajustes.")

transcriber = TranscriberService()
