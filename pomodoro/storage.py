import json
from pathlib import Path

class SessionStorage:
    def __init__(self, path: str | Path = "session_stats.json"):
        self.path = Path(path)
        self._default = {
            "completed_sessions": 0,
            "total_focus_minutes": 0.0,
            "total_overtime_minutes": 0.0,
            "streak": 0
        }

    def load(self) -> dict:
        if not self.path.exists():
            return self._default.copy()
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure all keys exist
            for k, v in self._default.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            return self._default.copy()

    def record_session(self, focus_minutes: float, overtime_minutes: float) -> dict:
        data = self.load()
        data["completed_sessions"] += 1
        data["total_focus_minutes"] += float(focus_minutes)
        data["total_overtime_minutes"] += float(overtime_minutes)
        data["streak"] += 1
        self._save(data)
        return data

    def reset_stats(self) -> dict:
        data = self._default.copy()
        self._save(data)
        return data

    def _save(self, data: dict):
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
