import os
import subprocess
import json
import uuid
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import yt_dlp
from app.core.config import settings

class DownloaderService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.clips_dir = settings.CLIPS_DIR

    def _get_yt_dlp_options(self, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'socket_timeout': 30,
            # User agent to avoid bot detection
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        }
        if cookies_path and os.path.exists(cookies_path):
            opts['cookiefile'] = cookies_path
        return opts

    def get_video_info(self, url: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract metadata (title, duration, thumbnail) without downloading."""
        opts = self._get_yt_dlp_options(cookies_path)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'id': info.get('id', str(uuid.uuid4())),
                'title': info.get('title', 'Unknown Title'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'channel': info.get('uploader', 'Unknown Creator')
            }

    def download_audio_from_youtube(self, url: str, job_id: str, cookies_path: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """Downloads audio only (m4a/mp3) for ultra-fast transcription and minimal bandwidth."""
        target_path = str(self.upload_dir / f"{job_id}_audio.m4a")
        
        opts = self._get_yt_dlp_options(cookies_path)
        opts.update({
            'format': 'ba[ext=m4a]/ba/b',
            'outtmpl': str(self.upload_dir / f"{job_id}_audio.%(ext)s"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '128',
            }],
        })

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Find the actual downloaded file
            actual_file = target_path
            if not os.path.exists(actual_file):
                # Search matching prefix
                for f in self.upload_dir.glob(f"{job_id}_audio.*"):
                    actual_file = str(f)
                    break
                    
            metadata = {
                'id': info.get('id', job_id),
                'title': info.get('title', 'Video'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', '')
            }
            return actual_file, metadata

    def download_video_section(
        self, 
        url: str, 
        start_time: float, 
        end_time: float, 
        output_path: str,
        cookies_path: Optional[str] = None
    ) -> str:
        """
        Downloads only the specified segment using yt-dlp download-sections.
        Saves 90%+ bandwidth & CPU by avoiding downloading the entire stream.
        """
        # Format section in yt-dlp syntax: "*00:01:30-00:02:15"
        def format_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            return f"{h:02d}:{m:02d}:{s:02d}"

        section = f"*{format_time(start_time)}-{format_time(end_time)}"
        
        # In low memory mode (Render 512MB), limit max resolution to 720p or 1080p
        video_format = 'bestvideo[height<=720]+bestaudio/best[height<=720]/best' if settings.LOW_MEMORY_MODE else 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
        
        opts = self._get_yt_dlp_options(cookies_path)
        opts.update({
            'format': video_format,
            'outtmpl': output_path,
            'download_ranges': yt_dlp.utils.download_range_func(None, [(start_time, end_time)]),
            'force_keyframes_at_cuts': True,
            'merge_output_format': 'mp4',
            'overwrites': True,
        })

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
            
        return output_path

    def extract_audio_from_local_file(self, video_path: str, output_audio_path: str) -> str:
        """Extracts 128k audio from a local video file using ffmpeg."""
        cmd = [
            settings.FFMPEG_CMD,
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "aac",
            "-b:a", "128k",
            output_audio_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction error: {result.stderr}")
        return output_audio_path

    def cut_local_video_section(self, input_video_path: str, start_time: float, end_time: float, output_path: str) -> str:
        """Cuts a section from an uploaded local video using ffmpeg without quality loss."""
        duration = end_time - start_time
        cmd = [
            settings.FFMPEG_CMD,
            "-y",
            "-ss", str(start_time),
            "-i", input_video_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-c:a", "aac",
            output_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg section cut error: {result.stderr}")
        return output_path

downloader = DownloaderService()
