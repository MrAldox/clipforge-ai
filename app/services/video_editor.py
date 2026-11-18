import os
import subprocess
from pathlib import Path
from typing import Optional, Literal
from app.core.config import settings

class VideoEditorService:
    def __init__(self):
        self.clips_dir = settings.CLIPS_DIR

    def _escape_ffmpeg_path(self, path: str) -> str:
        """Escapes path for FFmpeg filtergraph (forward slashes and escaped colons)."""
        clean_path = path.replace("\\", "/")
        return clean_path.replace(":", "\\:")

    def process_clip(
        self,
        raw_clip_path: str,
        output_filename: str,
        layout: Literal["blur_9_16", "crop_9_16", "original"] = "blur_9_16",
        subtitles_path: Optional[str] = None,
        resolution: str = "720x1280"
    ) -> str:
        """
        Converts a video segment into a short-form vertical video (9:16) with burnt-in animated subtitles.
        Optimized with low-memory flags for cloud environments like Render & Hugging Face.
        """
        output_path = str(self.clips_dir / output_filename)
        width, height = [int(x) for x in resolution.split("x")]

        # Build video filtergraph
        filters = []

        if layout == "blur_9_16":
            # Split stream: 1 for blurred background, 1 for sharp foreground centered
            vf_filter = (
                f"[0:v]split=2[bg_raw][fg_raw];"
                f"[bg_raw]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},boxblur=25:5,drawbox=color=black@0.35:t=fill[bg];"
                f"[fg_raw]scale={width}:-1[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[base]"
            )
            filters.append(vf_filter)
            last_pad = "[base]"
        elif layout == "crop_9_16":
            vf_filter = (
                f"[0:v]scale=-1:{height},crop={width}:{height}:(in_w-{width})/2:0[base]"
            )
            filters.append(vf_filter)
            last_pad = "[base]"
        else: # original
            last_pad = "[0:v]"

        # Add subtitles filter if available
        if subtitles_path and os.path.exists(subtitles_path):
            escaped_sub_path = self._escape_ffmpeg_path(subtitles_path)
            sub_filter = f"{last_pad}ass='{escaped_sub_path}'[outv]"
            filters.append(sub_filter)
            map_v = "[outv]"
        else:
            if layout != "original":
                map_v = "[base]"
            else:
                map_v = "0:v"

        filter_complex_str = ";".join(filters)

        # Build FFmpeg command
        cmd = [
            settings.FFMPEG_CMD,
            "-y",
            "-i", raw_clip_path,
        ]

        if filter_complex_str:
            cmd.extend(["-filter_complex", filter_complex_str, "-map", map_v, "-map", "0:a?"])
        else:
            cmd.extend(["-map", "0:v", "-map", "0:a?"])

        # Low-memory & fast encoding flags
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast" if settings.LOW_MEMORY_MODE else "veryfast",
            "-crf", "24",
            "-threads", "2" if settings.LOW_MEMORY_MODE else "0",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart", # allows progressive streaming in browser
            output_path
        ])

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print("FFmpeg Error STDERR:", result.stderr)
            raise RuntimeError(f"FFmpeg processing error: {result.stderr[-500:]}")

        return output_path

video_editor = VideoEditorService()
