from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import json
import os

# Portable: logs next to langgraph_impl root (this file is in src/tools/)
_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR = str(_LOG_DIR)
LOG_FILE = str(_LOG_DIR / "events.jsonl")

# Ensure log directory exists
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# In-Memory stores (for fast access by dashboard if needed)
LOGS = []
METRICS = {}

def log_event(level: str, event_type: str, message: str, extra: Dict = None) -> Dict:
    """
    Logs structured event to both memory and file.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "type": event_type,
        "message": message,
        "extra": extra or {}
    }
    LOGS.append(entry)
    
    # Write to file (append mode)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except IOError as e:
        print(f"[WARN] Could not write to log file: {e}")
    
    print(f"[{level}] {event_type}: {message}") # Stdout
    return entry

def publish_metric(metric_name: str, value: float, labels: Dict = None) -> bool:
    """
    Mock generic metric publisher.
    """
    if metric_name not in METRICS:
        METRICS[metric_name] = []
    
    METRICS[metric_name].append({
        "value": value,
        "labels": labels,
        "ts": datetime.now()
    })
    return True

def get_logs():
    """Return in-memory logs."""
    return LOGS

def get_metrics():
    """Return in-memory metrics."""
    return METRICS

def read_logs_from_file(limit: int = 100) -> list:
    """Read last N logs from file for dashboard."""
    if not os.path.exists(LOG_FILE):
        return []
    
    logs = []
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                logs.append(json.loads(line.strip()))
    except Exception as e:
        print(f"[WARN] Could not read log file: {e}")
    return logs

