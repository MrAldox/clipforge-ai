import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseModel):
    # App
    APP_NAME: str = "ClipForge AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1")
    
    # Storage Paths
    BASE_DIR: Path = BASE_DIR
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    CLIPS_DIR: Path = BASE_DIR / "outputs" / "clips"
    SUBTITLES_DIR: Path = BASE_DIR / "outputs" / "subtitles"
    
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    YOUTUBE_COOKIES: str = os.getenv("YOUTUBE_COOKIES", "")
    
    # Cloudflare R2 / S3
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "")
    R2_PUBLIC_URL: str = os.getenv("R2_PUBLIC_URL", "")
    
    # Memory & Processing Settings (crucial for Render free 512MB RAM)
    LOW_MEMORY_MODE: bool = os.getenv("LOW_MEMORY_MODE", "true").lower() in ("true", "1")
    MAX_VIDEO_DURATION_MINUTES: int = int(os.getenv("MAX_VIDEO_DURATION_MINUTES", "45"))
    DEFAULT_RESOLUTION: str = os.getenv("DEFAULT_RESOLUTION", "720x1280") # 720p 9:16 is lightweight and fast
    
    # FFmpeg executable path
    FFMPEG_CMD: str = os.getenv("FFMPEG_CMD", "")
    FFPROBE_CMD: str = os.getenv("FFPROBE_CMD", "")

def _discover_binary(name: str) -> str:
    import shutil
    env_val = os.getenv(f"{name.upper()}_CMD")
    if env_val and shutil.which(env_val):
        return env_val
    which_cmd = shutil.which(name)
    if which_cmd:
        return which_cmd
    local_app_data = os.getenv("LOCALAPPDATA", "")
    if local_app_data:
        winget_path = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_path.exists():
            for match in winget_path.glob(f"**/{name}.exe"):
                return str(match)
    return name

settings = Settings(
    FFMPEG_CMD=_discover_binary("ffmpeg"),
    FFPROBE_CMD=_discover_binary("ffprobe")
)

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.CLIPS_DIR.mkdir(parents=True, exist_ok=True)
settings.SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)

# Write server cookies if provided in environment
SERVER_COOKIES_FILE = settings.UPLOAD_DIR / "server_cookies.txt"
if settings.YOUTUBE_COOKIES and settings.YOUTUBE_COOKIES.strip():
    SERVER_COOKIES_FILE.write_text(settings.YOUTUBE_COOKIES.strip(), encoding="utf-8")

