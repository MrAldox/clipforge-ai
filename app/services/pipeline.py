import os
import uuid
import time
import asyncio
from typing import Dict, Optional
from datetime import datetime
from app.core.config import settings
from app.core.models import (
    ClipOptions, JobStatus, GeneratedClip, ViralMoment, FullTranscript
)
from app.services.downloader import downloader
from app.services.transcriber import transcriber
from app.services.ai_analyzer import ai_analyzer
from app.services.subtitle_generator import subtitle_generator
from app.services.video_editor import video_editor
from app.services.storage import storage

# In-memory store for active jobs
active_jobs: Dict[str, JobStatus] = {}

class PipelineManager:
    def create_job(self) -> str:
        job_id = str(uuid.uuid4())[:8]
        active_jobs[job_id] = JobStatus(
            job_id=job_id,
            status="pending",
            progress=5,
            step_message="Iniciando trabajo de clipping...",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        return job_id

    def get_job(self, job_id: str) -> Optional[JobStatus]:
        return active_jobs.get(job_id)

    async def run_pipeline(self, job_id: str, options: ClipOptions):
        """Asynchronous execution of the complete clipping workflow."""
        job = active_jobs.get(job_id)
        if not job:
            return

        cookies_file_path = None
        temp_files_to_cleanup = []

        try:
            # Handle cookies if provided (for YouTube bot bypass)
            if options.cookies_content and options.cookies_content.strip():
                cookies_file_path = str(settings.UPLOAD_DIR / f"{job_id}_cookies.txt")
                with open(cookies_file_path, "w", encoding="utf-8") as f:
                    f.write(options.cookies_content.strip())
                temp_files_to_cleanup.append(cookies_file_path)

            # Step 1: Audio Extraction
            job.status = "downloading"
            job.progress = 15
            job.step_message = "Extrayendo audio del video..."

            audio_path = None
            is_local_upload = bool(options.uploaded_filename)

            if is_local_upload:
                local_video_path = str(settings.UPLOAD_DIR / options.uploaded_filename)
                if not os.path.exists(local_video_path):
                    raise FileNotFoundError(f"Archivo subido no encontrado: {options.uploaded_filename}")
                audio_path = str(settings.UPLOAD_DIR / f"{job_id}_audio.aac")
                downloader.extract_audio_from_local_file(local_video_path, audio_path)
                temp_files_to_cleanup.append(audio_path)
            else:
                if not options.video_url:
                    raise ValueError("Se debe proporcionar una URL de video o subir un archivo.")
                audio_path, _ = downloader.download_audio_from_youtube(
                    options.video_url, job_id, cookies_path=cookies_file_path
                )
                temp_files_to_cleanup.append(audio_path)

            # Step 2: Transcription with Word Timestamps
            job.status = "transcribing"
            job.progress = 35
            job.step_message = "Transcribiendo audio y extrayendo marcas de tiempo con IA..."

            transcript: FullTranscript = transcriber.transcribe(
                audio_path=audio_path,
                groq_key=options.groq_api_key,
                gemini_key=options.gemini_api_key
            )

            if not transcript.segments:
                raise ValueError("No se detectó diálogo o habla en el audio del video.")

            # Step 3: AI Virality Analysis & Hook Detection
            job.status = "analyzing"
            job.progress = 55
            job.step_message = "Analizando contenido: detectando ganchos, remates y puntuación de viralidad..."

            viral_moments = ai_analyzer.find_viral_moments(
                transcript=transcript,
                num_clips=options.num_clips,
                target_duration=options.target_duration,
                focus_theme=options.focus_theme,
                groq_key=options.groq_api_key,
                gemini_key=options.gemini_api_key
            )

            if not viral_moments:
                raise ValueError("La IA no pudo determinar momentos con suficiente potencial viral.")

            job.total_clips = len(viral_moments)

            # Step 4: Video Clipping, 9:16 Reformatting & Subtitle Burning
            job.status = "clipping"
            job.step_message = f"Procesando {len(viral_moments)} clips en formato vertical con subtítulos..."

            progress_per_clip = 35.0 / max(1, len(viral_moments))
            clips_output = []

            for idx, moment in enumerate(viral_moments):
                current_clip_num = idx + 1
                job.step_message = f"Editando clip {current_clip_num}/{len(viral_moments)}: '{moment.title}'..."

                raw_clip_filename = f"{job_id}_raw_{current_clip_num}.mp4"
                raw_clip_path = str(settings.UPLOAD_DIR / raw_clip_filename)
                temp_files_to_cleanup.append(raw_clip_path)

                # Cut video section
                if is_local_upload:
                    downloader.cut_local_video_section(
                        local_video_path, moment.start_time, moment.end_time, raw_clip_path
                    )
                else:
                    downloader.download_video_section(
                        options.video_url,
                        moment.start_time,
                        moment.end_time,
                        raw_clip_path,
                        cookies_path=cookies_file_path
                    )

                # Generate subtitles
                sub_filename = f"{job_id}_sub_{current_clip_num}.ass"
                sub_path = subtitle_generator.generate_ass_subtitles(
                    transcript=transcript,
                    clip_start=moment.start_time,
                    clip_end=moment.end_time,
                    output_filename=sub_filename,
                    style=options.subtitles_style,
                    resolution=settings.DEFAULT_RESOLUTION
                )
                if sub_path:
                    temp_files_to_cleanup.append(sub_path)

                # Process vertical video + burn subtitles
                final_filename = f"clip_{job_id}_{current_clip_num}_{moment.virality_score}.mp4"
                processed_path = video_editor.process_clip(
                    raw_clip_path=raw_clip_path,
                    output_filename=final_filename,
                    layout=options.layout,
                    subtitles_path=sub_path,
                    resolution=settings.DEFAULT_RESOLUTION
                )

                # Upload to R2 or prepare local URL
                video_url = storage.upload_file(processed_path)
                file_size_mb = round(os.path.getsize(processed_path) / (1024 * 1024), 2)

                generated_clip = GeneratedClip(
                    id=f"{job_id}_{current_clip_num}",
                    moment=moment,
                    video_filename=final_filename,
                    video_url=video_url,
                    subtitles_filename=sub_filename if sub_path else None,
                    file_size_mb=file_size_mb,
                    duration_seconds=moment.duration,
                    status="ready"
                )
                clips_output.append(generated_clip)
                job.clips = clips_output
                job.progress = int(55 + (current_clip_num * progress_per_clip))

            # Step 5: Completed!
            job.status = "completed"
            job.progress = 100
            job.step_message = "¡Todos los clips virales han sido procesados y están listos!"

        except Exception as e:
            import traceback
            traceback.print_exc()
            job.status = "failed"
            job.error = str(e)
            job.step_message = f"Error en el proceso: {str(e)}"

        finally:
            # Clean up temporary raw files to save disk space
            for temp_file in temp_files_to_cleanup:
                try:
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception:
                    pass

pipeline_manager = PipelineManager()
