"""
Bandwidth Estimator

Measures approximate download speed by fetching a small test file
from a known CDN. This answers: "Is bandwidth the problem, or is it latency?"
"""

from __future__ import annotations

import time
import urllib.request
from typing import Optional

from netscope.core.models import BandwidthResult


# Test URLs — small files from well-known CDNs
# We use a ~1MB file for a quick test (takes ~1-3 seconds on most connections)
TEST_URLS = [
    (
        "Cloudflare",
        "https://speed.cloudflare.com/__down?bytes=1000000",
    ),
    (
        "Google",
        "https://www.google.com/generate_204",
    ),
]


class BandwidthEstimator:
    """Estimates download bandwidth by fetching test files."""

    def estimate(self, timeout: float = 15.0) -> Optional[BandwidthResult]:
        """Measure download speed using a CDN test file."""
        for server_name, url in TEST_URLS:
            result = self._test_download(server_name, url, timeout)
            if result:
                return result
        return None

    def _test_download(self, server_name: str, url: str,
                        timeout: float) -> Optional[BandwidthResult]:
        """Download a test file and measure throughput."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "NetScope/1.0"}
            )

            start = time.perf_counter()
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            elapsed = time.perf_counter() - start

            if elapsed <= 0 or len(data) == 0:
                return None

            # Calculate speed in Mbps
            bytes_downloaded = len(data)
            bits = bytes_downloaded * 8
            mbps = (bits / elapsed) / 1_000_000

            return BandwidthResult(
                download_mbps=round(mbps, 2),
                upload_mbps=0.0,  # Upload test not implemented
                test_server=server_name,
                test_duration_ms=round(elapsed * 1000, 2),
            )
        except Exception:
            return None
