import json
import os

class SessionStorage:
    def __init__(self, path="stats.json"):
        self.path = path
        self._data = self._load()

    def _load(self):
        # Always create required structure (not just return dict, but update in-place if partial or corrupted file)
        default = {
            "completed_sessions": 0,
            "total_focus_minutes": 0.0,
            "total_overtime_minutes": 0.0,
            "streak": 0
        }
        if not os.path.exists(self.path):
            return dict(default)
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
                # Defensive: Fill missing keys (if file is partial/corrupt)
                for k, v in default.items():
                    if k not in data:
                        data[k] = v
            # Type fixes: session counts int, totals float, streak int
                data["completed_sessions"] = int(data.get("completed_sessions", 0))
                data["total_focus_minutes"] = float(data.get("total_focus_minutes", 0.0))
                data["total_overtime_minutes"] = float(data.get("total_overtime_minutes", 0.0))
                data["streak"] = int(data.get("streak", 0))
                return data
        except Exception:
            return dict(default)

    def load(self):
        # Return a copy for caller
        return dict(self._data)

    def save(self, stats=None):
        to_save = self._data if stats is None else stats
        # Defensive: ensure always contains all required keys
        default = {
            "completed_sessions": 0,
            "total_focus_minutes": 0.0,
            "total_overtime_minutes": 0.0,
            "streak": 0
        }
        for k, v in default.items():
            if k not in to_save:
                to_save[k] = v
        with open(self.path, "w") as f:
            json.dump(to_save, f)

    def record_session(self, focus_minutes, overtime_minutes=0.0):
        self._data["completed_sessions"] = int(self._data.get("completed_sessions", 0)) + 1
        self._data["total_focus_minutes"] = float(self._data.get("total_focus_minutes", 0.0)) + float(focus_minutes)
        self._data["total_overtime_minutes"] = float(self._data.get("total_overtime_minutes", 0.0)) + float(overtime_minutes)
        self._data["streak"] = int(self._data.get("streak", 0)) + 1
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
        # Always ensure copy and numeric types
        d = dict(self._data)
        d["completed_sessions"] = int(d.get("completed_sessions", 0))
        d["total_focus_minutes"] = float(d.get("total_focus_minutes", 0.0))
        d["total_overtime_minutes"] = float(d.get("total_overtime_minutes", 0.0))
        d["streak"] = int(d.get("streak", 0))
        return d
