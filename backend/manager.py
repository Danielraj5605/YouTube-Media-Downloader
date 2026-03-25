import re
from typing import Dict, Any, Optional

# Regex to strip ANSI escape codes from yt-dlp output strings
_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')


def _clean(s: str) -> str:
    """Remove ANSI color codes and extra whitespace."""
    return _ANSI_ESCAPE.sub('', s or '').strip()


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self, task_id: str, is_playlist: bool = False, total_videos: int = 1):
        self.tasks[task_id] = {
            'status': 'starting',
            'progress': 0,
            'speed': '',
            'eta': '',
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'filename': None,
            'completed': False,
            'error': None,
            # Playlist-specific fields
            'is_playlist': is_playlist,
            'total_videos': total_videos,
            'current_video': 0,
            'current_video_title': '',
            'completed_files': [],
        }

    def update_task(self, task_id: str, data: Dict[str, Any]):
        if task_id in self.tasks:
            self.tasks[task_id].update(data)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(task_id)

    def delete_task(self, task_id: str):
        self.tasks.pop(task_id, None)

    def hook_factory(self, task_id: str):
        """Creates a yt-dlp progress hook bound to a specific task_id."""
        def hook(d):
            if d['status'] == 'downloading':
                raw_pct = _clean(d.get('_percent_str', '0%')).replace('%', '')
                try:
                    p = float(raw_pct)
                except ValueError:
                    p = 0

                downloaded = d.get('downloaded_bytes') or 0
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                speed_raw = d.get('speed') or 0

                self.update_task(task_id, {
                    'status': 'downloading',
                    'progress': p,
                    'speed': _clean(d.get('_speed_str', '')),
                    'eta': _clean(d.get('_eta_str', '')),
                    'downloaded_bytes': downloaded,
                    'total_bytes': total,
                    'speed_bytes': speed_raw,
                })
            elif d['status'] == 'finished':
                self.update_task(task_id, {
                    'status': 'processing',
                    'progress': 100,
                })
        return hook


manager = TaskManager()
