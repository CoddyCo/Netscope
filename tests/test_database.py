import os
import sqlite3
import pytest
from netscope.core.database import NetScopeDB
from netscope.core.models import TraceSummary, Hop, HealthScore

@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "test.db"
    db = NetScopeDB(str(db_file))
    yield db
    db.close()
    if db_file.exists():
        os.remove(db_file)

def test_save_and_retrieve_trace(db):
    summary = TraceSummary(
        target="google.com",
        resolved_ip="8.8.8.8",
        total_hops=5,
        avg_latency=25.0,
        max_latency=50.0,
        min_latency=10.0,
        packet_loss=0.0,
        countries=["US"],
        cloud_providers=["Google Cloud"],
        health=HealthScore(score=95, rating="★★★★★"),
        duration_ms=1500,
        timestamp="2023-10-25T10:00:00",
        hops=[],
        connection=None,
        dns_results=[],
        bandwidth=None
    )
    
    db.save_trace(summary)
    
    history = db.get_trace_history("google.com")
    assert len(history) == 1
    assert history[0]["target"] == "google.com"
    assert history[0]["avg_latency"] == 25.0
    
    recent = db.get_recent_searches()
    assert len(recent) == 1
    assert recent[0]["target"] == "google.com"
    
    full = db.get_full_trace(history[0]["id"])
    assert full is not None
    assert full.target == "google.com"
    assert full.resolved_ip == "8.8.8.8"
