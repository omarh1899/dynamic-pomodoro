import json
import os

class SessionStorage:
    def __init__(self, path="stats.json"):
        self.path = path
        self._data = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {
                "completed_sessions": 0,
                "total_focus_minutes": 0.0,
                "total_overtime_minutes": 0.0,
                "streak": 0
            }
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except Exception:
            return {
                "completed_sessions": 0,
                "total_focus_minutes": 0.0,
                "total_overtime_minutes": 0.0,
                "streak": 0
            }

    def load(self):
        return dict(self._data)

    def save(self, stats=None):
        data_to_save = self._data if stats is None else stats
        with open(self.path, "w") as f:
            json.dump(data_to_save, f)

    def record_session(self, focus_minutes, overtime_minutes=0.0):
        self._data["completed_sessions"] += 1
        self._data["total_focus_minutes"] += float(focus_minutes)
        self._data["total_overtime_minutes"] += float(overtime_minutes)
        self._data["streak"] += 1
        self.save()
        return dict(self._data)

    def reset_stats(self):
        self._data = {
            "completed_sessions": 0,
            "total_focus_minutes": 0.0,
            "total_overtime_minutes": 0.0,
            "streak": 0
        }
        self.save()
        return dict(self._data)

    def get_stats(self):
        return dict(self._data)
