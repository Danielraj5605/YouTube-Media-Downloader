# StreamGrab Backend (FastAPI)

## Requirements

- Python 3.7+
- **ffmpeg** (Essential for video/audio merging and MP3 conversion)

### Installing ffmpeg

- **Windows**: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`.
