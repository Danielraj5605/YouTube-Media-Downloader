from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import os
import json
import asyncio
from typing import Dict, Any

from downloader import get_video_info, download_video
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


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, get_video_info, request.url)
        return info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _run_download_task(url: str, format_id: str, task_id: str):
    """Synchronous wrapper that runs yt-dlp and updates the task manager."""
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

    # Cleanup after sending
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
