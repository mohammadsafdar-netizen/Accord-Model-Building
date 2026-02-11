import pytest
from src.tools.monitoring import (
    log_event,
    publish_metric,
    get_logs,
    get_metrics,
    LOGS,
    METRICS
)

def setup_function():
    LOGS.clear()
    METRICS.clear()

def test_logging():
    log_event("INFO", "TEST", "Hello")
    assert len(LOGS) == 1
    assert LOGS[0]["message"] == "Hello"

def test_metrics():
    publish_metric("latency", 0.5)
    assert "latency" in METRICS
    assert METRICS["latency"][0]["value"] == 0.5
