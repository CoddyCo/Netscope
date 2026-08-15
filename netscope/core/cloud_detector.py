"""
Cloud/CDN Provider Detection

Wraps the C++ CIDRTrie to provide a simple Python interface
for identifying cloud providers from IP addresses.
Falls back to a pure-Python implementation if the C++ module isn't available.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from netscope.core.models import CloudInfo


class CloudDetector:
    """Identifies cloud/CDN providers from IP addresses using CIDR matching."""

    def __init__(self, data_dir: str = "data/cloud-ranges"):
        self._trie = None
        self._python_ranges: list[tuple[int, int, int, CloudInfo]] = []
        self._data_dir = Path(data_dir)

        # Try to use the C++ CIDR trie (fast, O(32))
        try:
            import netscope_core
            self._trie = netscope_core.CIDRTrie()
            self._load_cpp()
        except ImportError:
            # Fallback to pure Python
            self._load_python()

    def _load_cpp(self):
        """Load cloud ranges into the C++ CIDR trie."""
        providers = {
            "aws.json": "aws",
            "gcp.json": "gcp",
            "azure.json": "azure",
            "cloudflare.json": "cloudflare",
        }
        for filename, provider in providers.items():
            filepath = self._data_dir / filename
            if filepath.exists():
                try:
                    self._trie.load_from_json(str(filepath), provider)
                except Exception as e:
                    print(f"Warning: Failed to load {filename}: {e}")

    def _load_python(self):
        """Pure Python fallback — load ranges for linear matching."""
        providers = {
            "aws.json": ("aws", "prefixes", "ip_prefix", "region"),
            "gcp.json": ("gcp", "prefixes", "ipv4Prefix", "scope"),
            "cloudflare.json": ("cloudflare", "prefixes", None, None),
        }

        for filename, (prov_name, array_key, cidr_key, region_key) in providers.items():
            filepath = self._data_dir / filename
            if not filepath.exists():
                continue
            try:
                with open(filepath) as f:
                    data = json.load(f)
                for entry in data.get(array_key, []):
                    if cidr_key:
                        cidr = entry.get(cidr_key, "")
                        region = entry.get(region_key, "") if region_key else ""
                    else:
                        cidr = entry if isinstance(entry, str) else ""
                        region = ""
                    if cidr and ":" not in cidr:  # Skip IPv6
                        ip_int, prefix_len = self._parse_cidr(cidr)
                        display_name = {
                            "aws": "AWS", "gcp": "Google Cloud",
                            "cloudflare": "Cloudflare", "azure": "Azure"
                        }.get(prov_name, prov_name)
                        self._python_ranges.append((
                            ip_int, prefix_len, 0,
                            CloudInfo(provider=display_name, region=region)
                        ))
            except Exception:
                pass

    @staticmethod
    def _parse_cidr(cidr: str) -> tuple[int, int]:
        parts = cidr.split("/")
        ip_parts = parts[0].split(".")
        ip_int = 0
        for p in ip_parts:
            ip_int = (ip_int << 8) | int(p)
        prefix_len = int(parts[1]) if len(parts) > 1 else 32
        return ip_int, prefix_len

    @staticmethod
    def _ip_to_int(ip: str) -> int:
        parts = ip.split(".")
        result = 0
        for p in parts:
            result = (result << 8) | int(p)
        return result

    def detect(self, ip: str) -> Optional[CloudInfo]:
        """Identify the cloud/CDN provider for a given IP address."""
        if not ip:
            return None

        # Use C++ trie if available (fast path)
        if self._trie is not None:
            try:
                result = self._trie.lookup(ip)
                if result:
                    return CloudInfo(
                        provider=result.provider,
                        region=result.region,
                        service=result.service,
                    )
            except Exception:
                pass
            return None

        # Pure Python fallback (slow but works without C++ build)
        try:
            ip_int = self._ip_to_int(ip)
        except (ValueError, IndexError):
            return None

        best_match = None
        best_prefix_len = -1

        for range_ip, prefix_len, _, info in self._python_ranges:
            mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
            if (ip_int & mask) == (range_ip & mask):
                if prefix_len > best_prefix_len:
                    best_match = info
                    best_prefix_len = prefix_len

        return best_match

    @property
    def size(self) -> int:
        if self._trie is not None:
            return self._trie.size()
        return len(self._python_ranges)
