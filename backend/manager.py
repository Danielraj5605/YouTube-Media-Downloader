from typing import Dict, Any, Optional


class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self, task_id: str):
        self.tasks[task_id] = {
            'status': 'starting',
            'progress': 0,
            'speed': '',
            'eta': '',
            'filename': None,
            'completed': False,
            'error': None
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
                p = d.get('_percent_str', '0%').replace('%', '').strip()
                try:
                    p = float(p)
                except ValueError:
                    p = 0

                self.update_task(task_id, {
                    'status': 'downloading',
                    'progress': p,
                    'speed': d.get('_speed_str', 'N/A'),
                    'eta': d.get('_eta_str', 'N/A'),
                })
            elif d['status'] == 'finished':
                # Mark as processing (post-processing may still happen)
                self.update_task(task_id, {
                    'status': 'processing',
                    'progress': 100,
                })
        return hook


manager = TaskManager()
