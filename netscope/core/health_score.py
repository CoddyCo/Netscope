"""
Health Score Calculator

Computes a 0-100 network quality score from trace data.
Score breakdown:
- Base score: 100
- Packet loss penalty:   up to -30 points
- Latency penalty:       up to -25 points
- Jitter penalty:        up to -15 points
- Timeout hop penalty:   up to -20 points
- Bottleneck penalty:    up to -10 points
"""

from __future__ import annotations

from netscope.core.models import Hop, HealthScore


def compute_health_score(hops: list[Hop], avg_latency: float,
                          packet_loss: float) -> HealthScore:
    """
    Compute a network health score from trace data.

    Returns:
        HealthScore object containing the final score and exact deductions.
    """
    health = HealthScore()
    score = 100.0

    # 1. Packet loss penalty (up to -30)
    if packet_loss > 0:
        if packet_loss > 20:
            health.packet_loss_penalty = -30
        elif packet_loss > 10:
            health.packet_loss_penalty = -25
        elif packet_loss > 5:
            health.packet_loss_penalty = -20
        elif packet_loss > 1:
            health.packet_loss_penalty = -10
        else:
            health.packet_loss_penalty = -5
        score += health.packet_loss_penalty

    # 2. Latency penalty (up to -25)
    if avg_latency > 500:
        health.latency_penalty = -25
    elif avg_latency > 300:
        health.latency_penalty = -20
    elif avg_latency > 200:
        health.latency_penalty = -15
    elif avg_latency > 100:
        health.latency_penalty = -8
    elif avg_latency > 50:
        health.latency_penalty = -3
    score += health.latency_penalty

    # 3. Jitter penalty (up to -15)
    valid_rtts = [h.avg_rtt for h in hops if not h.is_timeout and h.avg_rtt > 0]
    if len(valid_rtts) >= 2:
        jitter = max(valid_rtts) - min(valid_rtts)
        if jitter > 200:
            health.jitter_penalty = -15
        elif jitter > 100:
            health.jitter_penalty = -10
        elif jitter > 50:
            health.jitter_penalty = -5
        score += health.jitter_penalty

    # 4. Timeout hop penalty (up to -20)
    timeout_count = sum(1 for h in hops if h.is_timeout)
    if timeout_count > 0:
        health.timeout_penalty = -min(timeout_count * 4, 20)
        score += health.timeout_penalty

    # 5. Per-hop packet loss penalty (up to -10)
    hops_with_loss = sum(1 for h in hops if h.packet_loss > 0)
    if hops_with_loss > 0:
        health.hop_loss_penalty = -min(hops_with_loss * 3, 10)
        score += health.hop_loss_penalty

    # Clamp to 0-100
    health.score = max(0, min(100, int(round(score))))

    # Star rating
    if health.score >= 90:
        health.rating = "★★★★★"
    elif health.score >= 75:
        health.rating = "★★★★☆"
    elif health.score >= 60:
        health.rating = "★★★☆☆"
    elif health.score >= 40:
        health.rating = "★★☆☆☆"
    elif health.score >= 20:
        health.rating = "★☆☆☆☆"
    else:
        health.rating = "☆☆☆☆☆"

    return health
