import yt_dlp
import os
from typing import Dict, Any, List


def get_video_info(url: str) -> Dict[str, Any]:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # Handle playlists
        is_playlist = info.get('_type') == 'playlist' or 'entries' in info
        
        if is_playlist:
            entries = list(info.get('entries', []))
            return {
                'is_playlist': True,
                'title': info.get('title', 'Playlist'),
                'thumbnail': entries[0].get('thumbnail') if entries else None,
                'video_count': len(entries),
                'uploader': info.get('uploader', 'Unknown'),
                'url': url,
                'formats': _extract_formats(entries[0]) if entries else [],
                'videos': [
                    {
                        'title': e.get('title', 'Unknown'),
                        'duration': e.get('duration', 0),
                        'thumbnail': e.get('thumbnail'),
                    }
                    for e in entries[:25]  # Limit preview to 25 videos
                ]
            }
        
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


def _extract_formats(info: Dict) -> List[Dict]:
    """Extract and deduplicate formats from video info, grouped by resolution."""
    seen_resolutions = set()
    formats = []
    
    # Sort by height descending so we pick the best format_id per resolution
    raw_formats = sorted(
        info.get('formats', []),
        key=lambda f: f.get('height') or 0,
        reverse=True
    )
    
    for f in raw_formats:
        res = f.get('height')
        ext = f.get('ext')
        vcodec = f.get('vcodec')
        acodec = f.get('acodec')

        if res and vcodec != 'none' and res not in seen_resolutions:
            seen_resolutions.add(res)
            formats.append({
                'format_id': f.get('format_id'),
                'resolution': f'{res}p',
                'ext': ext,
                'filesize': f.get('filesize') or f.get('filesize_approx'),
                'vcodec': vcodec,
                'acodec': acodec,
                'note': f.get('format_note')
            })

    # Add audio only option
    formats.append({
        'format_id': 'bestaudio',
        'resolution': 'Audio Only',
        'ext': 'mp3',
        'note': 'Best Audio (MP3)'
    })

    return formats


def download_video(url: str, format_id: str, output_path: str, progress_hook=None):
    """Synchronous download function – called from FastAPI BackgroundTasks."""
    
    # Build output template
    outtmpl = os.path.join(output_path, '%(title)s.%(ext)s')
    
    ydl_opts = {
        'format': f'{format_id}+bestaudio/best' if format_id != 'bestaudio' else 'bestaudio/best',
        'outtmpl': outtmpl,
        'merge_output_format': 'mp4' if format_id != 'bestaudio' else None,
        'progress_hooks': [progress_hook] if progress_hook else [],
        'quiet': True,
        'no_warnings': True,
    }
    
    # Remove None values
    ydl_opts = {k: v for k, v in ydl_opts.items() if v is not None}
    
    if format_id == 'bestaudio':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
        # Get the final filepath after any post-processing
        if info and 'requested_downloads' in info:
            final_path = info['requested_downloads'][0].get('filepath')
        elif info:
            # Fallback: construct from template
            final_path = ydl.prepare_filename(info)
            # For audio, the extension changes after post-processing
            if format_id == 'bestaudio':
                base, _ = os.path.splitext(final_path)
                final_path = base + '.mp3'
        else:
            final_path = None
        
        return final_path
