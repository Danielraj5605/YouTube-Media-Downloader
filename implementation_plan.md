# StreamGrab – Bug Fix & Run Implementation Plan

Fix all issues preventing the StreamGrab (YouTube Media Downloader) app from working, then run it successfully.

---

## Bugs Found

### Backend
1. **[download_video](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/backend/downloader.py#54-71) is `async` but called from `BackgroundTasks`** — FastAPI's `BackgroundTasks` calls sync functions in a thread pool and coroutines natively, but the current function uses `asyncio.get_event_loop()` inside a background task which creates a new event loop clash. The fix: make it a plain sync function.
2. **Filename after post-processing is wrong** — The `'finished'` hook gets `d['filename']` which is the *pre-postprocessing* file (e.g. `.webm`). After FFmpeg converts to `.mp3`, the actual output filename changes. Fix: capture the final path from `ydl_opts` using `paths` or from the `postprocessors` callback.
3. **No error propagation** — If [_run_ydl](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/backend/downloader.py#72-75) raises an exception, the `manager` task stays in 'starting' forever. Fix: wrap [_run_ydl](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/backend/downloader.py#72-75) call in try/except and call `manager.update_task` with an error.
4. **SSE generator exits too fast** — The SSE stream yields one event and if the task isn't done, loops and sleeps 1s. This is fine, but the [onerror](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/frontend/src/App.tsx#114-118) callback on the frontend closes the stream. The EventSource fires [onerror](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/frontend/src/App.tsx#114-118) when the connection closes naturally (task done). This is handled in the frontend fix.

### Frontend
5. **`lucide-react` v1.x doesn't exist** — [package.json](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/frontend/package.json) has `"lucide-react": "^1.6.0"` which will fail to install. The correct version is `^0.484.0`.
6. **`downloading` state never resets to `false` after completion** — The button stays in "Preparing..." if the user doesn't click away. Fix: reset `downloading` to `false` when `progress.completed` becomes true.
7. **[Video](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/frontend/src/App.tsx#27-35) icon imported but doesn't exist in lucide-react** — Import uses [Video](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/frontend/src/App.tsx#27-35) which is not exported from lucide-react (it's `VideoIcon` or similar). Replace with `Film`.

---

## Proposed Changes

### Backend

#### [MODIFY] [downloader.py](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/backend/downloader.py)
- Remove `async` from [download_video](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/backend/downloader.py#54-71); make it synchronous
- Add try/except around [_run_ydl](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/backend/downloader.py#72-75) to propagate errors to the manager
- Track final filename properly using a `postprocessor_hooks` entry that fires after FFmpeg finishes (or by reading `info_dict['requested_downloads'][0]['filepath']` from the finished hook)

#### [MODIFY] [manager.py](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/backend/manager.py)
- Add `delete_task` method for cleanup
- No other changes needed

#### [MODIFY] [main.py](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/backend/main.py)
- Update `background_tasks.add_task` call signature: since [download_video](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/backend/downloader.py#54-71) is now sync, pass args directly
- Wrap the background task call in a lambda that catches exceptions and updates manager

### Frontend

#### [MODIFY] [package.json](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/frontend/package.json)
- Change `lucide-react` from `"^1.6.0"` to `"^0.484.0"`

#### [MODIFY] [App.tsx](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/frontend/src/App.tsx)
- Replace [Video](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/frontend/src/App.tsx#27-35) import with `Film` (not in lucide-react v0.x)
- In the SSE [onmessage](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/frontend/src/App.tsx#102-113) handler: when `data.completed`, call `setDownloading(false)` 
- In the SSE [onerror](file:///d:/Personal%20Projects/YouTube%20Media%20Downloader/frontend/src/App.tsx#114-118) handler: only close if stream is in a terminal state, otherwise it re-reconnects naturally (EventSource will reconnect on network errors — we should only set `downloading: false` if we get consecutive onerror with no recovery)

---

## Verification Plan

> [!IMPORTANT]
> Both backend and frontend servers must be running simultaneously for end-to-end testing.

### Automated – Backend Install
```
cd "d:\Personal Projects\YouTube Media Downloader\backend"
pip install -r requirements.txt
```

### Automated – Frontend Install
```
cd "d:\Personal Projects\YouTube Media Downloader\frontend"
npm install
```

### Manual – Start Servers
1. Terminal 1: `cd backend && python main.py`
2. Terminal 2: `cd frontend && npm run dev`

### Browser Test (via browser_subagent)
1. Open `http://localhost:5173`
2. Paste a short public YouTube URL (e.g. `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)
3. Click **Analyze** → video card should appear with thumbnail, title, duration
4. Select a format and click **Start Download**
5. Progress bar should animate to 100%
6. **Save to Device** button appears → clicking it downloads the file
