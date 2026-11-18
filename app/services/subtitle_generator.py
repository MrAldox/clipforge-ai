import os
from pathlib import Path
from typing import List, Literal, Optional
from app.core.config import settings
from app.core.models import FullTranscript, WordTimestamp, TranscriptSegment

class SubtitleGeneratorService:
    def __init__(self):
        self.subtitles_dir = settings.SUBTITLES_DIR

    def _format_ass_time(self, seconds: float) -> str:
        """Formats seconds into ASS timestamp: H:MM:SS.cs (centiseconds)."""
        seconds = max(0.0, seconds)
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int(round((seconds - int(seconds)) * 100))
        if cs >= 100:
            cs = 99
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def generate_ass_subtitles(
        self,
        transcript: FullTranscript,
        clip_start: float,
        clip_end: float,
        output_filename: str,
        style: Literal["tiktok_yellow", "neon_cyan", "clean_white", "none"] = "tiktok_yellow",
        resolution: str = "720x1280"
    ) -> Optional[str]:
        """
        Generates an ASS subtitle file tailored for vertical 9:16 video.
        Uses animated karaoke-style highlighting for spoken words (Hormozi / TikTok style).
        """
        if style == "none":
            return None

        width, height = [int(x) for x in resolution.split("x")]
        font_size = 52 if width == 720 else 76
        margin_v = int(height * 0.18) # 18% from the bottom, safely above UI buttons

        # Colors in BGR ASS hex format
        highlight_color = "&H0000FFFF&" if style == "tiktok_yellow" else "&H00FFFF00&" # Yellow or Cyan
        base_color = "&H00FFFFFF&" # Pure White
        outline_color = "&H00000000&" # Deep Black Outline

        header = f"""[Script Info]
Title: ClipForge TikTok Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokActive,Arial Black,{font_size},{base_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,1,0,1,5,3,2,30,30,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        # Filter words within clip bounds
        clip_words: List[WordTimestamp] = []
        for seg in transcript.segments:
            if seg.words:
                for w in seg.words:
                    if w.end >= clip_start and w.start <= clip_end:
                        clip_words.append(w)
            else:
                # If no word-level timestamps, break segment text into approximated words
                if seg.end >= clip_start and seg.start <= clip_end:
                    words = seg.text.strip().split()
                    if words:
                        duration = max(0.1, seg.end - seg.start)
                        w_dur = duration / len(words)
                        for i, w in enumerate(words):
                            w_st = seg.start + (i * w_dur)
                            w_en = w_st + w_dur
                            clip_words.append(WordTimestamp(word=w, start=w_st, end=w_en))

        if not clip_words:
            return None

        # Group words into chunks of 3-4 words (snappy TikTok pacing)
        CHUNK_SIZE = 3
        chunks = [clip_words[i:i + CHUNK_SIZE] for i in range(0, len(clip_words), CHUNK_SIZE)]

        dialogue_lines: List[str] = []

        for chunk in chunks:
            if not chunk:
                continue

            chunk_start = max(0.0, chunk[0].start - clip_start)
            chunk_end = max(chunk_start + 0.3, chunk[-1].end - clip_start)
            
            # For each word in chunk, create a mini-dialogue entry highlighting that word
            for active_idx, target_word in enumerate(chunk):
                w_rel_start = max(0.0, target_word.start - clip_start)
                w_rel_end = max(w_rel_start + 0.15, target_word.end - clip_start)

                # Build line text with active word highlighted
                line_parts = []
                for idx, w in enumerate(chunk):
                    clean_w = w.word.upper().replace("{", "").replace("}", "")
                    if idx == active_idx and style in ("tiktok_yellow", "neon_cyan"):
                        line_parts.append(f"{{\\c{highlight_color}\\fscx110\\fscy110}}{clean_w}{{\\c{base_color}\\fscx100\\fscy100}}")
                    else:
                        line_parts.append(clean_w)

                styled_text = " ".join(line_parts)
                start_str = self._format_ass_time(w_rel_start)
                end_str = self._format_ass_time(w_rel_end)
                dialogue_lines.append(f"Dialogue: 0,{start_str},{end_str},TikTokActive,,0,0,0,,{styled_text}")

        output_path = str(self.subtitles_dir / output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(dialogue_lines))
            f.write("\n")

        return output_path

subtitle_generator = SubtitleGeneratorService()
