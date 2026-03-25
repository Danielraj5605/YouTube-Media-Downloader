import yt_dlp
import os
from typing import Dict, Any, List, Callable, Optional


def get_video_info(url: str) -> Dict[str, Any]:
    """Fast analysis — uses flat extraction for playlists (near-instant)."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    # First: detect if it's a playlist using flat extraction (instant)
    flat_opts = {**ydl_opts, 'extract_flat': 'in_playlist'}
    with yt_dlp.YoutubeDL(flat_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    is_playlist = info.get('_type') == 'playlist' or 'entries' in info

    if is_playlist:
        entries = list(info.get('entries', []))
        # For playlists, get formats from the first video only (fast)
        first_url = None
        if entries:
            first_url = entries[0].get('url') or entries[0].get('webpage_url')
            if first_url and not first_url.startswith('http'):
                first_url = f"https://www.youtube.com/watch?v={first_url}"

        formats = []
        first_thumb = None
        if first_url:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    first_info = ydl2.extract_info(first_url, download=False)
                    formats = _extract_formats(first_info)
                    first_thumb = first_info.get('thumbnail')
            except Exception:
                formats = _default_formats()

        return {
            'is_playlist': True,
            'title': info.get('title', 'Playlist'),
            'thumbnail': first_thumb or (entries[0].get('thumbnail') if entries else None),
            'video_count': len(entries),
            'uploader': info.get('uploader') or info.get('channel') or 'Unknown',
            'url': url,
            'formats': formats or _default_formats(),
            'videos': [
                {
                    'title': e.get('title', 'Unknown'),
                    'duration': e.get('duration') or 0,
                    'thumbnail': e.get('thumbnails', [{}])[-1].get('url') if e.get('thumbnails') else e.get('thumbnail'),
                    'url': e.get('url') or e.get('webpage_url') or e.get('id', ''),
                }
                for e in entries
            ]
        }

    # Single video — extract fully (fast, just 1 video)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = _extract_formats(info)

    return {
        'is_playlist': False,
        'title': info.get('title'),
        'thumbnail': info.get('thumbnail'),
        'duration': info.get('duration'),
        'uploader': info.get('uploader'),
        'formats': formats,
        'url': url
    }


def _default_formats() -> List[Dict]:
    """Safe default format options when extraction fails."""
    return [
        {'format_id': 'best[ext=mp4]', 'resolution': 'Best Quality', 'ext': 'mp4', 'note': 'Auto', 'needs_merge': False},
        {'format_id': 'best', 'resolution': 'Best Available', 'ext': 'mp4', 'note': 'Auto', 'needs_merge': False},
        {'format_id': 'bestaudio', 'resolution': 'Audio Only', 'ext': 'mp3', 'note': 'Best Audio', 'needs_merge': False},
    ]


def _extract_formats(info: Dict) -> List[Dict]:
    """Extract and deduplicate formats grouped by resolution."""
    seen_resolutions = set()
    formats = []

    raw_formats = info.get('formats', [])

    # Pass 1 — combined (muxed) formats: both video + audio
    combined = sorted(
        [f for f in raw_formats
         if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none'],
        key=lambda f: (f.get('height') or 0, f.get('tbr') or 0),
        reverse=True
    )

    for f in combined:
        res = f.get('height')
        if res and res not in seen_resolutions:
            seen_resolutions.add(res)
            formats.append({
                'format_id': f.get('format_id'),
                'resolution': f'{res}p',
                'ext': f.get('ext', 'mp4'),
                'filesize': f.get('filesize') or f.get('filesize_approx'),
                'vcodec': f.get('vcodec'),
                'acodec': f.get('acodec'),
                'note': f.get('format_note', ''),
                'needs_merge': False,
            })

    # Pass 2 — video-only to fill missing resolutions
    video_only = sorted(
        [f for f in raw_formats
         if f.get('vcodec', 'none') != 'none' and f.get('height')],
        key=lambda f: (f.get('height') or 0, f.get('tbr') or 0),
        reverse=True
    )

    for f in video_only:
        res = f.get('height')
        if res and res not in seen_resolutions:
            seen_resolutions.add(res)
            formats.append({
                'format_id': f.get('format_id'),
                'resolution': f'{res}p',
                'ext': 'mp4',
                'filesize': f.get('filesize') or f.get('filesize_approx'),
                'vcodec': f.get('vcodec'),
                'acodec': f.get('acodec'),
                'note': f.get('format_note', ''),
                'needs_merge': True,
            })

    # Audio-only
    formats.append({
        'format_id': 'bestaudio',
        'resolution': 'Audio Only',
        'ext': 'mp3',
        'note': 'Best Audio',
        'needs_merge': False,
    })

    return formats


def _build_format_string(format_id: str) -> str:
    """Build a yt-dlp format string that avoids requiring ffmpeg."""
    if format_id == 'bestaudio':
        return 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best'
    elif format_id.startswith('best'):
        return f'{format_id}/best'
    else:
        return f'{format_id}/best[ext=mp4]/best'


def download_video(url: str, format_id: str, output_path: str, progress_hook=None):
    """Download a single video. Works WITHOUT ffmpeg."""
    outtmpl = os.path.join(output_path, '%(title)s.%(ext)s')

    ydl_opts = {
        'format': _build_format_string(format_id),
        'outtmpl': outtmpl,
        'progress_hooks': [progress_hook] if progress_hook else [],
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        if info and 'requested_downloads' in info:
            final_path = info['requested_downloads'][0].get('filepath')
        elif info:
            final_path = ydl.prepare_filename(info)
        else:
            final_path = None

        return final_path


def download_playlist_video(
    video_url: str,
    video_id: str,
    format_id: str,
    output_path: str,
    progress_hook=None
) -> Optional[str]:
    """Download a single video from a playlist.
    
    video_url may be a full URL or just a video ID.
    """
    if not video_url.startswith('http'):
        video_url = f"https://www.youtube.com/watch?v={video_url}"

    return download_video(video_url, format_id, output_path, progress_hook)
