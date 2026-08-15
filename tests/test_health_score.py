import pytest
from netscope.core.models import Hop
from netscope.core.health_score import compute_health_score

def test_perfect_health():
    hops = [
        Hop(1, "192.168.1.1", rtts=[1.0, 1.1, 1.2], avg_rtt=1.1),
        Hop(2, "8.8.8.8", rtts=[10.0, 10.1, 10.2], avg_rtt=10.1, is_destination=True),
    ]
    health = compute_health_score(hops, 5.0, 0.0)
    assert health.score == 100
    assert health.rating == "★★★★★"

def test_high_latency_penalty():
    hops = [
        Hop(1, "192.168.1.1", rtts=[1.0, 1.1, 1.2], avg_rtt=1.1),
        Hop(2, "8.8.8.8", rtts=[250.0, 250.1, 250.2], avg_rtt=250.1, is_destination=True),
    ]
    health = compute_health_score(hops, 250.0, 0.0)
    assert health.score <= 85 # Should penalize for >200ms latency

def test_packet_loss_penalty():
    hops = [
        Hop(1, "192.168.1.1", rtts=[1.0, 1.1, 1.2], avg_rtt=1.1),
    ]
    # Simulate 15% packet loss
    health = compute_health_score(hops, 1.0, 15.0)
    assert health.score <= 75 # Should heavily penalize for >10% packet loss

def test_timeout_hop_penalty():
    hops = [
        Hop(1, "192.168.1.1", rtts=[1.0, 1.1, 1.2], avg_rtt=1.1),
        Hop(2, "", is_timeout=True),
        Hop(3, "8.8.8.8", rtts=[10.0, 10.1, 10.2], avg_rtt=10.1, is_destination=True),
    ]
    health = compute_health_score(hops, 5.0, 0.0)
    assert health.score < 100
    assert health.score >= 80 # Penalty should exist but not destroy score
