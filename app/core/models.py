from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ClipOptions(BaseModel):
    video_url: Optional[str] = None
    uploaded_filename: Optional[str] = None
    layout: Literal["blur_9_16", "crop_9_16", "original"] = "blur_9_16"
    target_duration: Literal["short", "medium", "long"] = "medium"  # short: 15-30s, medium: 30-60s, long: 60-90s
    num_clips: int = Field(default=3, ge=1, le=8)
    focus_theme: str = "High virality, catchy hooks, humor, drama, controversial or insightful statements"
    subtitles_style: Literal["tiktok_yellow", "neon_cyan", "clean_white", "none"] = "tiktok_yellow"
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    cookies_content: Optional[str] = None

class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float

class TranscriptSegment(BaseModel):
    id: Optional[int] = None
    start: float
    end: float
    text: str
    words: List[WordTimestamp] = []

class FullTranscript(BaseModel):
    language: str = "es"
    duration: float = 0.0
    text: str = ""
    segments: List[TranscriptSegment] = []

class ViralMoment(BaseModel):
    id: str
    title: str
    hook: str
    start_time: float
    end_time: float
    duration: float
    virality_score: int = Field(ge=0, le=100)
    virality_reason: str
    suggested_caption: str
    hashtags: List[str] = []

class GeneratedClip(BaseModel):
    id: str
    moment: ViralMoment
    video_filename: str
    video_url: str
    subtitles_filename: Optional[str] = None
    subtitles_url: Optional[str] = None
    file_size_mb: float = 0.0
    duration_seconds: float = 0.0
    status: str = "ready"

class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "downloading", "transcribing", "analyzing", "clipping", "completed", "failed"] = "pending"
    progress: int = 0  # 0 to 100
    step_message: str = "Iniciando proceso..."
    created_at: str = ""
    total_clips: int = 0
    clips: List[GeneratedClip] = []
    error: Optional[str] = None
