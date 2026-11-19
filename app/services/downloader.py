import os
import re
import subprocess
import json
import uuid
import urllib.request
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import yt_dlp
from app.core.config import settings

class DownloaderService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.clips_dir = settings.CLIPS_DIR

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extracts YouTube 11-char video ID from various URL patterns."""
        patterns = [
            r'(?:v=|\/embed\/|\/live\/|\/shorts\/|youtu\.be\/|\/v\/)([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$'
        ]
        for p in patterns:
            match = re.search(p, url)
            if match:
                return match.group(1)
        return None

    def _get_yt_dlp_options(self, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'socket_timeout': 30,
            # User agent
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            },
            # Crucial: Use Android and iOS clients which bypass datacenter bot detection
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web_embedded', 'web'],
                    'player_skip': ['webpage', 'configs']
                }
            }
        }

        # Check for cookies (passed explicitly or saved on server)
        server_cookies = self.upload_dir / "server_cookies.txt"
        if cookies_path and os.path.exists(cookies_path):
            opts['cookiefile'] = cookies_path
        elif server_cookies.exists():
            opts['cookiefile'] = str(server_cookies)

        return opts

    def get_video_info(self, url: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts metadata safely.
        Uses YouTube oEmbed first (which NEVER blocks cloud IPs or requires cookies),
        then enriches with yt-dlp duration if available.
        """
        video_id = self._extract_video_id(url)
        oembed_data = {}

        # 1. Safe oEmbed retrieval
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                oembed_data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"oEmbed info fallback notice: {e}")

        # Base metadata from oEmbed
        title = oembed_data.get('title', 'Video de YouTube')
        channel = oembed_data.get('author_name', 'YouTube Creator')
        thumbnail = oembed_data.get('thumbnail_url', '')
        if not thumbnail and video_id:
            thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        duration = 0

        # 2. Try yt-dlp to get precise duration and formats
        try:
            opts = self._get_yt_dlp_options(cookies_path)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    duration = int(info.get('duration', 0) or 0)
                    title = info.get('title') or title
                    channel = info.get('uploader') or channel
                    thumbnail = info.get('thumbnail') or thumbnail
        except Exception as yt_err:
            print(f"yt-dlp metadata notice: {yt_err}")
            # If yt-dlp fails due to bot detection, but oEmbed succeeded, we DO NOT throw!
            # We return the oEmbed title & thumbnail so the user can continue smoothly.

        return {
            'id': video_id or str(uuid.uuid4()),
            'title': title,
            'duration': duration,
            'thumbnail': thumbnail,
            'channel': channel
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

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Find the actual downloaded file
                actual_file = target_path
                if not os.path.exists(actual_file):
                    for f in self.upload_dir.glob(f"{job_id}_audio.*"):
                        actual_file = str(f)
                        break
                        
                metadata = {
                    'id': info.get('id', job_id) if info else job_id,
                    'title': info.get('title', 'Video') if info else 'Video',
                    'duration': info.get('duration', 0) if info else 0,
                    'thumbnail': info.get('thumbnail', '') if info else ''
                }
                return actual_file, metadata
        except Exception as e:
            err_str = str(e)
            if "Sign in to confirm you’re not a bot" in err_str or "429" in err_str:
                raise RuntimeError(
                    "YouTube bloqueó la descarga en este servidor solicitando verificación de bot. "
                    "Soluciones inmediatas: "
                    "1) Sube el video directamente en la pestaña 'Subir Video (MP4 / MOV)', o "
                    "2) Abre 'Configurar APIs' y pega tus cookies de YouTube (exportadas con la extensión 'Get cookies.txt')."
                )
            raise

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

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return output_path
        except Exception as e:
            err_str = str(e)
            if "Sign in to confirm you’re not a bot" in err_str or "429" in err_str:
                raise RuntimeError(
                    "YouTube bloqueó la descarga de este segmento. "
                    "Sube el archivo de video en la pestaña 'Subir Video' para recortarlo sin restricciones de IP."
                )
            raise

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
