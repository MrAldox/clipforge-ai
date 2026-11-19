import json
import uuid
from typing import List, Optional
from google import genai
from google.genai import types
from groq import Groq
from app.core.config import settings
from app.core.models import FullTranscript, ViralMoment

VIRAL_PROMPT_TEMPLATE = """
Eres un editor profesional de contenido viral para TikTok, YouTube Shorts e Instagram Reels (estilo OpusClip, Alex Hormozi, MrBeast).
Tu trabajo es analizar la transcripción de un video/stream y encontrar los {num_clips} momentos con mayor potencial de volverse virales.

Duración objetivo por clip: Entre {min_duration} y {max_duration} segundos.
Tema de enfoque: {focus_theme}

Criterios de selección para viralidad:
1. **Gancho inicial (Hook)**: Los primeros 3-5 segundos deben atrapar la atención de inmediato (una pregunta provocativa, una afirmación sorprendente, humor o drama).
2. **Arco completo**: El clip debe comenzar y terminar de forma natural sin cortar palabras a la mitad ni dejar una idea inconclusa.
3. **Alto valor emocional o de retención**: Revelación, humor, debate candente, consejo de alto valor o momento épico.
4. **Marcas de tiempo exactas**: Las marcas `start_time` y `end_time` (en segundos con decimales) deben corresponder exactamente a la transcripción.

Transcripción con marcas de tiempo (inicio en segundos - fin en segundos):
---
{transcript_text}
---

Responde ÚNICAMENTE en formato JSON con la siguiente estructura (sin bloques markdown adicionales fuera del json):
[
  {{
    "title": "Título llamativo para el clip (máx 8 palabras)",
    "hook": "La frase exacta con la que arranca el clip para enganchar al espectador",
    "start_time": 12.5,
    "end_time": 47.0,
    "virality_score": 94,
    "virality_reason": "Por qué este momento tiene alto potencial (ej. genera curiosidad inmediata y remata con un chiste inesperado)",
    "suggested_caption": "Descripción lista para copiar y pegar para Shorts/TikTok con llamada a la acción",
    "hashtags": ["#shorts", "#fyp", "#viral", "#podcast"]
  }}
]
"""

class AIAnalyzerService:
    def __init__(self):
        self.gemini_key = settings.GEMINI_API_KEY
        self.groq_key = settings.GROQ_API_KEY

    def _prepare_transcript_text(self, transcript: FullTranscript) -> str:
        """Formats the transcript into timed blocks for the LLM to read easily."""
        lines = []
        for seg in transcript.segments:
            lines.append(f"[{seg.start:.2f}s - {seg.end:.2f}s] {seg.text}")
        return "\n".join(lines)

    def _get_duration_bounds(self, target_duration: str) -> tuple[int, int]:
        if target_duration == "short":
            return (15, 30)
        elif target_duration == "long":
            return (60, 90)
        return (30, 60) # default medium

    def analyze_with_gemini(
        self, 
        transcript: FullTranscript, 
        num_clips: int = 3, 
        target_duration: str = "medium",
        focus_theme: str = "Viral hooks and highlights",
        custom_key: Optional[str] = None
    ) -> List[ViralMoment]:
        api_key = custom_key or self.gemini_key
        if not api_key:
            raise ValueError("No se proporcionó una clave de API de Gemini.")

        min_dur, max_dur = self._get_duration_bounds(target_duration)
        transcript_formatted = self._prepare_transcript_text(transcript)

        client = genai.Client(api_key=api_key)
        prompt = VIRAL_PROMPT_TEMPLATE.format(
            num_clips=num_clips,
            min_duration=min_dur,
            max_duration=max_dur,
            focus_theme=focus_theme,
            transcript_text=transcript_formatted
        )

        models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
        last_err = None
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7
                    )
                )
                raw_data = json.loads(response.text)
                return self._parse_moments(raw_data)
            except Exception as e:
                last_err = e
                print(f"Gemini model '{model_name}' failed: {e}. Trying fallback...")
        raise last_err or RuntimeError("No se pudo analizar con ningún modelo de Gemini.")

    def analyze_with_groq(
        self, 
        transcript: FullTranscript, 
        num_clips: int = 3, 
        target_duration: str = "medium",
        focus_theme: str = "Viral hooks and highlights",
        custom_key: Optional[str] = None
    ) -> List[ViralMoment]:
        api_key = custom_key or self.groq_key
        if not api_key:
            raise ValueError("No se proporcionó una clave de API de Groq.")

        min_dur, max_dur = self._get_duration_bounds(target_duration)
        transcript_formatted = self._prepare_transcript_text(transcript)

        client = Groq(api_key=api_key)
        prompt = VIRAL_PROMPT_TEMPLATE.format(
            num_clips=num_clips,
            min_duration=min_dur,
            max_duration=max_dur,
            focus_theme=focus_theme,
            transcript_text=transcript_formatted
        )

        models_to_try = [
            "llama-3.1-8b-instant",       # 100% universal access on all free accounts & ultra fast
            "llama-3.3-70b-versatile",    # 70B if accessible
            "llama3-70b-8192",            # Fallback 70B
            "mixtral-8x7b-32768"          # MoE fallback
        ]

        last_err = None
        for model_name in models_to_try:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "Eres un asistente experto en edición de video y virales. Devuelve únicamente JSON válido."},
                        {"role": "user", "content": prompt}
                    ],
                    model=model_name,
                    response_format={"type": "json_object"},
                    temperature=0.7
                )

                content = chat_completion.choices[0].message.content
                raw_json = json.loads(content)
                
                # Handle cases where json_object wraps array inside a key
                if isinstance(raw_json, dict):
                    for k in ["clips", "moments", "viral_moments", "results"]:
                        if k in raw_json and isinstance(raw_json[k], list):
                            raw_json = raw_json[k]
                            break
                    if isinstance(raw_json, dict):
                        # If still a dict, see if values are a list
                        raw_json = list(raw_json.values())[0] if raw_json else []

                return self._parse_moments(raw_json)
            except Exception as e:
                last_err = e
                print(f"Groq model '{model_name}' failed: {e}. Trying fallback model...")

        raise last_err or RuntimeError("No se pudo analizar con ningún modelo de Groq.")

    def _parse_moments(self, raw_list: list) -> List[ViralMoment]:
        moments: List[ViralMoment] = []
        if not isinstance(raw_list, list):
            return moments

        for item in raw_list:
            if not isinstance(item, dict):
                continue
            start = float(item.get("start_time", 0.0))
            end = float(item.get("end_time", 0.0))
            duration = max(1.0, end - start)
            
            # Score clamping
            score = int(item.get("virality_score", 85))
            score = max(50, min(99, score))

            moment = ViralMoment(
                id=str(uuid.uuid4())[:8],
                title=str(item.get("title", "Momento Viral")),
                hook=str(item.get("hook", "")),
                start_time=start,
                end_time=end,
                duration=round(duration, 2),
                virality_score=score,
                virality_reason=str(item.get("virality_reason", "Gancho dinámico y alta retención.")),
                suggested_caption=str(item.get("suggested_caption", "")),
                hashtags=item.get("hashtags", ["#shorts", "#viral", "#reels"])
            )
            moments.append(moment)

        # Sort by virality score descending
        moments.sort(key=lambda m: m.virality_score, reverse=True)
        return moments

    def find_viral_moments(
        self,
        transcript: FullTranscript,
        num_clips: int = 3,
        target_duration: str = "medium",
        focus_theme: str = "Viral hooks and highlights",
        groq_key: Optional[str] = None,
        gemini_key: Optional[str] = None
    ) -> List[ViralMoment]:
        """Tries Gemini first for complex viral reasoning, falls back to Groq Llama-3.3-70b."""
        if gemini_key or self.gemini_key:
            try:
                return self.analyze_with_gemini(transcript, num_clips, target_duration, focus_theme, custom_key=gemini_key)
            except Exception as e:
                print(f"Gemini analysis warning: {e}, attempting Groq...")
                if groq_key or self.groq_key:
                    return self.analyze_with_groq(transcript, num_clips, target_duration, focus_theme, custom_key=groq_key)
                raise
        elif groq_key or self.groq_key:
            return self.analyze_with_groq(transcript, num_clips, target_duration, focus_theme, custom_key=groq_key)
        else:
            raise ValueError("Se requiere una API Key de Google Gemini o de Groq para analizar los momentos virales.")

ai_analyzer = AIAnalyzerService()
