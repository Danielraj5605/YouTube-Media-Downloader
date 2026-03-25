# StreamGrab – Smart YouTube Media Downloader

A modern web application to download YouTube videos and playlists in high quality (up to 4K) and convert them to MP4 or MP3 formats.

## Tech Stack

- **Frontend:** React (Vite) + Tailwind CSS + Axios
- **Backend:** Python + FastAPI
- **Core Engine:** yt-dlp

## Features

- 🔗 Single video & playlist URL support
- 📊 Video analysis with thumbnail, title, duration
- 🎥 Quality selector (144p → 4K)
- 🎵 Audio-only MP3 extraction
- 📈 Real-time download progress tracking
- 🧹 Auto-cleanup after download

## Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Analyze a YouTube URL |
| POST | `/api/download` | Start a download task |
| GET | `/api/progress/{task_id}` | Get download progress |
| GET | `/api/fetch/{task_id}` | Fetch the downloaded file |

## License

MIT
