from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import uuid
import os
import json
import asyncio
import zipfile
import shutil
from typing import Dict, Any, List, Optional

from downloader import get_video_info, download_video, download_playlist_video
from manager import manager

app = FastAPI(title="StreamGrab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)


class AnalyzeRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format_id: str


class PlaylistDownloadRequest(BaseModel):
    url: str
    format_id: str
    videos: List[Dict[str, Any]]


class CookiesRequest(BaseModel):
    cookies: str


# ─── Cookie management ────────────────────────────────────────

COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")


@app.post("/api/set-cookies")
async def set_cookies(request: CookiesRequest):
    """Save YouTube cookies (Netscape format) to the server."""
    try:
        with open(COOKIES_FILE, 'w') as f:
            f.write(request.cookies)
        # Also set env var so downloader picks it up
        os.environ['YT_COOKIES'] = request.cookies
        # Force downloader to recreate cookie file
        from downloader import _ensure_cookies_file
        import downloader
        downloader._COOKIES_PATH = None
        _ensure_cookies_file()
        return {"status": "ok", "message": "Cookies saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cookies-status")
async def cookies_status():
    """Check if cookies are configured."""
    has_env = bool(os.environ.get('YT_COOKIES', '').strip())
    has_file = os.path.exists(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0
    return {"configured": has_env or has_file}


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, get_video_info, request.url)
        return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Single video download ────────────────────────────────────

def _run_download_task(url: str, format_id: str, task_id: str):
    """Synchronous wrapper for single video download."""
    try:
        progress_hook = manager.hook_factory(task_id)
        final_path = download_video(url, format_id, TEMP_DIR, progress_hook)

        if final_path and os.path.exists(final_path):
            manager.update_task(task_id, {
                'status': 'finished',
                'progress': 100,
                'filename': final_path,
                'completed': True,
            })
        else:
            manager.update_task(task_id, {
                'status': 'error',
                'error': 'Download completed but file not found.',
            })
    except Exception as e:
        manager.update_task(task_id, {
            'status': 'error',
            'error': str(e),
        })


@app.post("/api/download")
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    manager.create_task(task_id)
    background_tasks.add_task(_run_download_task, request.url, request.format_id, task_id)
    return {"task_id": task_id}


# ─── Playlist download ────────────────────────────────────────

def _run_playlist_download_task(
    videos: List[Dict[str, Any]],
    format_id: str,
    task_id: str,
):
    """Download each video in a playlist sequentially, track per-video progress."""
    total = len(videos)
    completed_files = []

    # Create a subfolder for this playlist
    playlist_dir = os.path.join(TEMP_DIR, task_id)
    os.makedirs(playlist_dir, exist_ok=True)

    for idx, video in enumerate(videos):
        video_url = video.get('url', '')
        video_title = video.get('title', f'Video {idx + 1}')

        manager.update_task(task_id, {
            'status': 'downloading',
            'current_video': idx + 1,
            'current_video_title': video_title,
            'progress': 0,
            'speed': '',
            'eta': '',
        })

        try:
            progress_hook = manager.hook_factory(task_id)
            final_path = download_playlist_video(
                video_url, str(idx), format_id, playlist_dir, progress_hook
            )
            if final_path and os.path.exists(final_path):
                completed_files.append(final_path)
        except Exception as e:
            # Log but continue with next video
            print(f"[Playlist] Failed to download '{video_title}': {e}")

        manager.update_task(task_id, {
            'completed_files': list(completed_files),
        })

    if not completed_files:
        manager.update_task(task_id, {
            'status': 'error',
            'error': 'No videos could be downloaded from this playlist.',
        })
        return

    # Create a zip file with all downloaded videos
    zip_path = os.path.join(TEMP_DIR, f"{task_id}.zip")
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fpath in completed_files:
                zf.write(fpath, os.path.basename(fpath))
    except Exception as e:
        manager.update_task(task_id, {
            'status': 'error',
            'error': f'Failed to create zip: {str(e)}',
        })
        return

    # Cleanup individual files
    try:
        shutil.rmtree(playlist_dir, ignore_errors=True)
    except Exception:
        pass

    manager.update_task(task_id, {
        'status': 'finished',
        'progress': 100,
        'filename': zip_path,
        'completed': True,
        'current_video': total,
    })


@app.post("/api/download-playlist")
async def start_playlist_download(
    request: PlaylistDownloadRequest,
    background_tasks: BackgroundTasks,
):
    task_id = str(uuid.uuid4())
    manager.create_task(task_id, is_playlist=True, total_videos=len(request.videos))
    background_tasks.add_task(
        _run_playlist_download_task,
        request.videos,
        request.format_id,
        task_id,
    )
    return {"task_id": task_id}


# ─── Progress & file fetch ────────────────────────────────────

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    task = manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/api/fetch/{task_id}")
async def fetch_file(task_id: str, background_tasks: BackgroundTasks):
    task = manager.get_task(task_id)
    if not task or not task.get('completed'):
        raise HTTPException(status_code=400, detail="Task not completed or not found")

    filename = task.get('filename')
    if not filename or not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="File not found")

    def cleanup():
        try:
            if os.path.exists(filename):
                os.remove(filename)
            manager.delete_task(task_id)
        except Exception:
            pass

    background_tasks.add_task(cleanup)

    return FileResponse(
        filename,
        filename=os.path.basename(filename),
        media_type='application/octet-stream',
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
