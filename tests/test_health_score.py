import pytest
from netscope.core.models import Hop
from netscope.core.health_score import compute_health_score

def test_perfect_health():
    hops = [
        Hop(1, "192.168.1.1", "", [1.0, 1.1, 1.2], 1.1, 1.0, 1.2, False, False),
        Hop(2, "8.8.8.8", "", [10.0, 10.1, 10.2], 10.1, 10.0, 10.2, False, True),
    ]
    score, rating = compute_health_score(hops, 5.0, 0.0)
    assert score == 100
    assert rating == "★★★★★"

def test_high_latency_penalty():
    hops = [
        Hop(1, "192.168.1.1", "", [1.0, 1.1, 1.2], 1.1, 1.0, 1.2, False, False),
        Hop(2, "8.8.8.8", "", [250.0, 250.1, 250.2], 250.1, 250.0, 250.2, False, True),
    ]
    score, rating = compute_health_score(hops, 250.0, 0.0)
    assert score <= 85 # Should penalize for >200ms latency

def test_packet_loss_penalty():
    hops = [
        Hop(1, "192.168.1.1", "", [1.0, 1.1, 1.2], 1.1, 1.0, 1.2, False, False),
    ]
    # Simulate 15% packet loss
    score, rating = compute_health_score(hops, 1.0, 15.0)
    assert score <= 75 # Should heavily penalize for >10% packet loss

def test_timeout_hop_penalty():
    hops = [
        Hop(1, "192.168.1.1", "", [1.0, 1.1, 1.2], 1.1, 1.0, 1.2, False, False),
        Hop(2, "", "", [-1.0, -1.0, -1.0], -1.0, -1.0, -1.0, True, False),
        Hop(3, "8.8.8.8", "", [10.0, 10.1, 10.2], 10.1, 10.0, 10.2, False, True),
    ]
    score, rating = compute_health_score(hops, 5.0, 0.0)
    assert score < 100
    assert score >= 80 # Penalty should exist but not destroy score
