"""aiohttp web server for the DubStudio AI app.

Hosts the web UI and exposes a small JSON API that drives the same
dubbing pipeline used by the CLI. Job state is shared between an
in-memory dictionary and a per-run status.json so the History view
survives server restarts.
"""

import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aiohttp import web

from src.config import (
    DEFAULT_TARGET_LANG,
    DEFAULT_WHISPER_MODEL,
    LANGUAGE_CATALOG,
)
from src.pipeline import run_pipeline


BASE_DIR = Path(__file__).parent.resolve()
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
WEB_DIR = BASE_DIR / "web"


# =============================================================================
#  Job state
# =============================================================================
@dataclass
class JobState:
    run_id: str
    status: str = "pending"  # pending | processing | completed | failed | cancelled
    progress: int = 0
    current_step: int = 0
    logs: List[str] = field(default_factory=list)
    result: Optional[dict] = None
    error: Optional[str] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    log_lock: threading.Lock = field(default_factory=threading.Lock)

    def log(self, message: str, step: Optional[int] = None, progress: Optional[int] = None) -> None:
        with self.log_lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            entry = f"[{timestamp}] {message}"
            self.logs.append(entry)
            if step is not None:
                self.current_step = step
            if progress is not None:
                self.progress = progress
        if step is not None or progress is not None:
            tag = f"[step {step}/6 · {progress:>3}%]"
            print(f"[{self.run_id}] {tag} {message}")
        else:
            print(f"[{self.run_id}] {message}")

    def request_cancel(self) -> None:
        self.cancel_event.set()
        self.log("Cancellation requested by user.")

    @property
    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def snapshot(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "logs": list(self.logs),
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
        }


JOB_STORE: Dict[str, JobState] = {}
JOB_LOCK = threading.RLock()
ACTIVE_JOB_ID: Optional[str] = None
JOB_STORE_LAST_MODIFIED: Dict[str, float] = {}

# Cached list_runs results — invalidated when any output dir mtime changes.
_LIST_RUNS_CACHE: Dict[str, Any] = {"runs": None, "scanned": 0.0}
_LIST_RUNS_LOCK = threading.Lock()
_LIST_RUNS_TTL_S = 5.0


# =============================================================================
#  Status persistence
# =============================================================================
def _status_file(run_id: str) -> Path:
    return OUTPUTS_DIR / run_id / "status.json"


def _persist_status(job: JobState) -> None:
    try:
        path = _status_file(job.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_id": job.run_id,
                    "status": job.status,
                    "progress": job.progress,
                    "current_step": job.current_step,
                    "error": job.error,
                    "created_at": job.created_at,
                    "updated_at": datetime.now().isoformat(),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
    except OSError as exc:
        print(f"[{job.run_id}] Failed to persist status: {exc}")


def _restore_status(run_id: str) -> Optional[JobState]:
    """Reconstruct a JobState from disk after server restart."""
    path = _status_file(run_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    job = JobState(
        run_id=run_id,
        status=data.get("status", "unknown"),
        progress=data.get("progress", 0),
        current_step=data.get("current_step", 0),
        error=data.get("error"),
        created_at=data.get("created_at", datetime.now().isoformat()),
    )
    return job


def _sync_status_from_disk() -> None:
    """Scan outputs/ at startup and revive completed/failed jobs into JOB_STORE."""
    if not OUTPUTS_DIR.exists():
        return
    for run_dir in OUTPUTS_DIR.iterdir():
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        if run_id in JOB_STORE:
            continue
        restored = _restore_status(run_id)
        if restored is not None:
            JOB_STORE[run_id] = restored


# =============================================================================
#  Pipeline worker
# =============================================================================
def _cancel_check_factory(job: JobState) -> Callable[[], bool]:
    def _check() -> bool:
        return job.is_cancelled
    return _check


def _log_factory(job: JobState, persist: bool = True) -> Callable:
    def _log(message: str, step: Optional[int], progress: Optional[int]) -> None:
        job.log(message, step=step, progress=progress)
        if persist:
            _persist_status(job)
    return _log


def _run_dubbing_job(job: JobState, params: dict) -> None:
    """Worker function executed in background thread."""
    global ACTIVE_JOB_ID

    try:
        job.status = "processing"
        job.log("Starting dubbing worker.", step=1, progress=5)
        _persist_status(job)

        result = run_pipeline(
            source_input=params["source_input"],
            target_lang=params.get("target_lang", DEFAULT_TARGET_LANG),
            gender=params.get("gender", "female"),
            model_name=params.get("model", DEFAULT_WHISPER_MODEL),
            voice=params.get("voice"),
            embed_subs=params.get("embed_subs", False),
            source_lang=params.get("source_lang"),
            log=_log_factory(job),
            is_cancelled=_cancel_check_factory(job),
        )

        if result.get("cancelled"):
            job.status = "cancelled"
            job.log("Pipeline acknowledged cancellation.")
            _persist_status(job)
            return

        # Translate pipeline output into the front-end shape it already expects.
        run_id = result["run_id"]
        rel_video = f"/files/{run_id}/output/{Path(result['final_video_path']).name}"
        rel_audio = f"/files/{run_id}/output/{Path(result['dubbed_audio_path']).name}"
        rel_srt = f"/files/{run_id}/subtitles/{Path(result['translated_srt_path']).name}"
        rel_vtt = f"/files/{run_id}/subtitles/{Path(result['translated_vtt_path']).name}"
        rel_transcript = f"/files/{run_id}/transcripts/transcript.json"

        job.status = "completed"
        job.result = {
            "run_id": run_id,
            "source_language": result["source_language"],
            "target_language": params.get("target_lang", DEFAULT_TARGET_LANG),
            "segments_count": result["segments_count"],
            "video_url": rel_video,
            "audio_url": rel_audio,
            "srt_url": rel_srt,
            "vtt_url": rel_vtt,
            "transcript_url": rel_transcript,
            "segments": result["translated_segments"],
        }
        job.progress = 100
        job.current_step = 6
        job.log("Dubbing completed.", step=6, progress=100)
        _persist_status(job)
    except Exception as e:
        job.status = "failed"
        job.error = f"{type(e).__name__}: {e}"
        job.log(f"ERROR: {job.error}")
        _persist_status(job)
    finally:
        with JOB_LOCK:
            if ACTIVE_JOB_ID == job.run_id:
                ACTIVE_JOB_ID = None


# =============================================================================
#  REST API handlers
# =============================================================================
async def handle_languages(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "ok",
        "default": DEFAULT_TARGET_LANG,
        "languages": LANGUAGE_CATALOG,
    })


async def handle_create_dub(request: web.Request) -> web.Response:
    """Start a dubbing job via URL or file upload."""
    content_type = request.content_type or ""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    params = {
        "source_lang": None,
        "target_lang": DEFAULT_TARGET_LANG,
        "gender": "female",
        "model": DEFAULT_WHISPER_MODEL,
        "voice": None,
        "embed_subs": False,
    }

    if "multipart" in content_type:
        reader = await request.multipart()
        saved_file_path = None

        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == "file" and part.filename:
                upload_dir = run_dir / "uploads"
                upload_dir.mkdir(parents=True, exist_ok=True)
                dest = upload_dir / part.filename
                with open(dest, "wb") as f:
                    while True:
                        chunk = await part.read_chunk()
                        if not chunk:
                            break
                        f.write(chunk)
                saved_file_path = str(dest.resolve())
            elif part.name in ("embed_subs", "embed_subtitles"):
                value = (await part.text()).strip()
                params["embed_subs"] = value.lower() in ("true", "1", "yes")
            elif part.name in params:
                value = (await part.text()).strip()
                params[part.name] = value

        if not saved_file_path:
            return web.json_response(
                {"status": "error", "message": "No file uploaded."},
                status=400,
            )
        params["source_input"] = saved_file_path
    else:
        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"status": "error", "message": "Invalid JSON body."},
                status=400,
            )

        url = data.get("url", "").strip()
        if not url:
            return web.json_response(
                {"status": "error", "message": "URL cannot be empty."},
                status=400,
            )
        params["source_input"] = url
        params["source_lang"] = data.get("source_lang", None)
        params["target_lang"] = data.get("target_lang", DEFAULT_TARGET_LANG)
        params["gender"] = data.get("gender", "female")
        params["model"] = data.get("model", DEFAULT_WHISPER_MODEL)
        params["voice"] = data.get("voice", None)
        params["embed_subs"] = bool(data.get("embed_subs", data.get("embed_subtitles", False)))

    # Decide what to do about any currently-active job.
    global ACTIVE_JOB_ID
    with JOB_LOCK:
        prev_id = ACTIVE_JOB_ID
        prev_job = JOB_STORE.get(prev_id) if prev_id else None
        if prev_job and prev_job.status in ("pending", "processing"):
            prev_job.request_cancel()
        ACTIVE_JOB_ID = run_id

        job = JobState(run_id=run_id, status="pending", progress=0, current_step=0)
        JOB_STORE[run_id] = job

    if prev_id:
        print(f"[{prev_id}] Cancelled to make room for new job {run_id}.")

    _persist_status(job)

    # Run the pipeline in a daemon thread. The pipeline cooperatively checks
    # job.cancel_event between heavy steps, so the previous job will exit as
    # soon as it reaches the next checkpoint.
    worker = threading.Thread(
        target=_run_dubbing_job,
        args=(job, params),
        daemon=True,
        name=f"dub-{run_id}",
    )
    worker.start()

    return web.json_response({
        "status": "ok",
        "run_id": run_id,
        "message": "Dubbing job started successfully.",
    })


async def handle_cancel_job(request: web.Request) -> web.Response:
    """Explicitly cancel a running job."""
    run_id = request.match_info.get("run_id")
    with JOB_LOCK:
        job = JOB_STORE.get(run_id)
        if not job:
            return web.json_response(
                {"status": "error", "message": "Job not found."},
                status=404,
            )
        if job.status not in ("pending", "processing"):
            return web.json_response({
                "status": "ok",
                "message": f"Job is already {job.status}; nothing to cancel.",
            })
        job.request_cancel()

    return web.json_response({"status": "ok", "message": "Cancellation requested."})


async def handle_job_status(request: web.Request) -> web.Response:
    run_id = request.match_info.get("run_id")
    job = JOB_STORE.get(run_id)
    if job is None:
        # Maybe it's an old run we didn't keep in memory; try disk.
        job = _restore_status(run_id)
        if job is None:
            return web.json_response(
                {"status": "error", "message": "Job not found."},
                status=404,
            )
        JOB_STORE[run_id] = job
    return web.json_response(job.snapshot())


def _list_runs_sync(limit: int = 30) -> List[dict]:
    """Walk OUTPUTS_DIR and build a run summary list. Cached for 5 seconds."""
    runs: List[dict] = []
    if not OUTPUTS_DIR.exists():
        return runs

    for item in sorted(OUTPUTS_DIR.iterdir(), reverse=True):
        if not item.is_dir():
            continue
        run_id = item.name

        # Pull status from in-memory if available; else from disk.
        with JOB_LOCK:
            job = JOB_STORE.get(run_id)
        status_from_job = job.status if job else None

        output_sub = item / "output"
        transcripts_sub = item / "transcripts"
        downloads_sub = item / "downloads"
        uploads_sub = item / "uploads"

        videos = (
            [v for v in output_sub.glob("*.mp4") if not v.name.startswith("temp_")]
            if output_sub.exists() else []
        )
        has_video = len(videos) > 0
        video_file = videos[0] if has_video else None

        size_mb = 0.0
        if video_file and video_file.exists():
            size_mb = round(video_file.stat().st_size / (1024 * 1024), 1)

        orig_name = "Video Project"
        if uploads_sub.exists():
            upload_files = list(uploads_sub.iterdir())
            if upload_files:
                orig_name = upload_files[0].name
        elif downloads_sub.exists():
            dl_files = [
                f for f in downloads_sub.iterdir()
                if f.is_file() and not f.name.endswith(".temp.mp4")
            ]
            if dl_files:
                orig_name = dl_files[0].name

        source_lang = "en"
        target_lang = "es"
        segment_count = 0
        duration_str = "03:50"

        t_file = transcripts_sub / "transcript.json"
        if t_file.exists():
            try:
                with open(t_file, "r", encoding="utf-8") as tf:
                    t_data = json.load(tf)
                source_lang = t_data.get("language", "en")
                segments = t_data.get("segments", [])
                segment_count = len(segments)
                if segments:
                    last_end = int(segments[-1].get("end", 0))
                    mins, secs = divmod(last_end, 60)
                    duration_str = f"{mins:02d}:{secs:02d}"
            except (OSError, json.JSONDecodeError):
                pass

        if video_file:
            stem_parts = video_file.stem.split("_")
            for part in stem_parts:
                if len(part) == 2 and part in LANGUAGE_CATALOG:
                    target_lang = part
                    break

        mtime = item.stat().st_mtime
        created_date = datetime.fromtimestamp(mtime).strftime("%b %d, %Y %I:%M %p")

        # Status: prefer in-memory state; fall back to disk; default completed if a video exists.
        if status_from_job:
            status = status_from_job
        else:
            persisted = _restore_status(run_id)
            if persisted:
                status = persisted.status
            else:
                status = "completed" if has_video else "unknown"

        runs.append({
            "run_id": run_id,
            "title": orig_name,
            "has_output": has_video,
            "status": status,
            "source_language": source_lang,
            "target_language": target_lang,
            "segment_count": segment_count,
            "duration": duration_str,
            "size_mb": f"{size_mb} MB" if size_mb > 0 else "N/A",
            "date": created_date,
            "video_name": video_file.name if video_file else None,
            "video_url": f"/files/{run_id}/output/{video_file.name}" if video_file else None,
            "audio_url": (
                f"/files/{run_id}/output/dubbed_{target_lang}_audio.wav"
                if (output_sub / f"dubbed_{target_lang}_audio.wav").exists()
                else None
            ),
            "srt_url": (
                f"/files/{run_id}/subtitles/dubbed_{target_lang}.srt"
                if (item / "subtitles" / f"dubbed_{target_lang}.srt").exists()
                else None
            ),
            "vtt_url": (
                f"/files/{run_id}/subtitles/dubbed_{target_lang}.vtt"
                if (item / "subtitles" / f"dubbed_{target_lang}.vtt").exists()
                else None
            ),
        })

        if len(runs) >= limit:
            break

    return runs


async def handle_list_runs(request: web.Request) -> web.Response:
    """List recent run sessions; results are cached briefly."""
    now = time.time()
    with _LIST_RUNS_LOCK:
        cache = _LIST_RUNS_CACHE
        if (
            cache["runs"] is not None
            and (now - cache["scanned"]) < _LIST_RUNS_TTL_S
        ):
            runs = cache["runs"]
        else:
            # Run the disk walk in a thread so we don't block the event loop.
            runs = await asyncio.to_thread(_list_runs_sync, 30)
            _LIST_RUNS_CACHE["runs"] = runs
            _LIST_RUNS_CACHE["scanned"] = now
    return web.json_response({"status": "ok", "runs": runs})


async def handle_index(request: web.Request) -> web.Response:
    """Serve web application homepage."""
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return web.FileResponse(index_file)
    return web.Response(text="Web interface loading...", content_type="text/html")


# =============================================================================
#  App factory + entry point
# =============================================================================
def create_app() -> web.Application:
    _sync_status_from_disk()
    app = web.Application(client_max_size=1024 * 1024 * 500)  # 500MB cap

    # API routes
    app.router.add_get("/api/languages", handle_languages)
    app.router.add_post("/api/dub", handle_create_dub)
    app.router.add_get("/api/status/{run_id}", handle_job_status)
    app.router.add_post("/api/cancel/{run_id}", handle_cancel_job)
    app.router.add_get("/api/runs", handle_list_runs)

    # Serve ONLY files we know about — disabled directory listings.
    app.router.add_get("/", handle_index)
    app.router.add_static("/files", str(OUTPUTS_DIR.resolve()), show_index=False)
    if (WEB_DIR / "css").exists():
        app.router.add_static("/css", str((WEB_DIR / "css").resolve()), show_index=False)
    if (WEB_DIR / "js").exists():
        app.router.add_static("/js", str((WEB_DIR / "js").resolve()), show_index=False)
    if (WEB_DIR / "assets").exists():
        app.router.add_static("/assets", str((WEB_DIR / "assets").resolve()), show_index=False)

    return app


if __name__ == "__main__":
    import argparse
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="DubStudio AI Web Server")
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Host address to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 8080)),
        help="Port to listen on (default: 8080 or PORT env var)",
    )
    args = parser.parse_args()

    print("\n=======================================================")
    print(" [DubStudio AI] Automated Video Dubbing Server")
    print(f" Access Web UI: http://localhost:{args.port}")
    print(f" Host Binding:  {args.host}")
    print("=======================================================\n")
    web.run_app(create_app(), host=args.host, port=args.port)
