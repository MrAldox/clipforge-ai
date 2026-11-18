import os
import shutil
import uuid
import asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.models import ClipOptions, JobStatus
from app.services.pipeline import pipeline_manager
from app.services.downloader import downloader

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Herramienta moderna de generación automática de clips virales para Shorts y TikTok"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and Templates
app.mount("/static", StaticFiles(directory=str(settings.BASE_DIR / "app" / "static")), name="static")
app.mount("/outputs/clips", StaticFiles(directory=str(settings.CLIPS_DIR)), name="clips")
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Serves the main application dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": settings.APP_NAME}
    )

@app.get("/api/video-info")
async def get_video_info(url: str):
    """Extracts YouTube metadata to preview title and thumbnail before clipping."""
    try:
        info = downloader.get_video_info(url)
        return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo obtener información del video: {str(e)}")

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Uploads a local video file (MP4/MOV/WebM) as an alternative to YouTube URLs."""
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".mp4", ".mov", ".mkv", ".webm", ".avi"]:
            raise HTTPException(status_code=400, detail="Formato de video no soportado. Usa MP4, MOV o WebM.")

        file_id = f"upload_{uuid.uuid4().hex[:8]}{ext}"
        destination = settings.UPLOAD_DIR / file_id

        with open(destination, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size_mb = round(os.path.getsize(destination) / (1024 * 1024), 2)
        return {
            "filename": file_id,
            "original_name": file.filename,
            "size_mb": file_size_mb
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir archivo: {str(e)}")

@app.post("/api/clips/create")
async def create_clips_job(options: ClipOptions, background_tasks: BackgroundTasks):
    """Initializes a new clipping job."""
    if not options.video_url and not options.uploaded_filename:
        raise HTTPException(status_code=400, detail="Debes ingresar una URL de YouTube o subir un archivo de video.")

    job_id = pipeline_manager.create_job()

    # Launch background processing pipeline
    background_tasks.add_task(pipeline_manager.run_pipeline, job_id, options)

    return {"job_id": job_id, "status": "pending"}

@app.get("/api/clips/status/{job_id}")
async def get_job_status(job_id: str):
    """Returns real-time status, progress, and generated clips for a job."""
    job = pipeline_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
    return job

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Render/HuggingFace keepalive."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "low_memory_mode": settings.LOW_MEMORY_MODE,
        "groq_configured": bool(settings.GROQ_API_KEY),
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "r2_configured": bool(settings.R2_ACCOUNT_ID and settings.R2_BUCKET_NAME)
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860)) # 7860 is default for HuggingFace Spaces & local
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
