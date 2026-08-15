"""
GeoIP and Network Enrichment Pipeline

Takes raw HopResult from the C++ engine and enriches it with:
1. GeoIP data (country, city, lat/lng) from MaxMind or ip-api.com
2. ASN/ISP data from MaxMind ASN database
3. Reverse DNS hostnames
4. Cloud/CDN provider identification via the C++ CIDR trie
"""

from __future__ import annotations

import json
import socket
import urllib.request
from pathlib import Path
from typing import Optional

from netscope.core.models import CloudInfo, GeoInfo, Hop, NetworkInfo


class EnrichmentPipeline:
    """Multi-source data enrichment for traceroute hops."""

    def __init__(self, maxmind_city_path: Optional[str] = None,
                 maxmind_asn_path: Optional[str] = None,
                 cloud_detector=None):
        self._geo_db = None
        self._asn_db = None
        self._cloud_detector = cloud_detector

        # Try to load MaxMind databases
        if maxmind_city_path and Path(maxmind_city_path).exists():
            try:
                import maxminddb
                self._geo_db = maxminddb.open_database(maxmind_city_path)
            except Exception:
                pass

        if maxmind_asn_path and Path(maxmind_asn_path).exists():
            try:
                import maxminddb
                self._asn_db = maxminddb.open_database(maxmind_asn_path)
            except Exception:
                pass

    def enrich_hop(self, hop_number: int, ip: str, hostname: str,
                   rtts: list[float], avg_rtt: float, min_rtt: float,
                   max_rtt: float, is_timeout: bool,
                   is_destination: bool) -> Hop:
        """Enrich a raw hop result with GeoIP, ASN, and cloud data."""
        hop = Hop(
            hop_number=hop_number,
            ip=ip,
            hostname=hostname,
            rtts=rtts,
            avg_rtt=avg_rtt,
            min_rtt=min_rtt,
            max_rtt=max_rtt,
            is_timeout=is_timeout,
            is_destination=is_destination,
        )

        if is_timeout or not ip:
            return hop

        # Compute packet loss from RTTs (-1.0 = timeout probe)
        total_probes = len(rtts)
        lost_probes = sum(1 for r in rtts if r < 0)
        hop.packet_loss = (lost_probes / total_probes * 100) if total_probes > 0 else 0.0

        # GeoIP lookup
        hop.geo = self._lookup_geoip(ip)

        # ASN/ISP lookup
        hop.network = self._lookup_asn(ip)

        # Reverse DNS (if not already set by the C++ engine)
        if not hop.hostname:
            hop.hostname = self._reverse_dns(ip)

        # Cloud/CDN detection
        if self._cloud_detector:
            cloud = self._cloud_detector.detect(ip)
            if cloud:
                hop.cloud = cloud

        return hop

    def _lookup_geoip(self, ip: str) -> Optional[GeoInfo]:
        """Lookup GeoIP data from MaxMind or fallback to ip-api.com."""
        if self._geo_db:
            return self._lookup_geoip_maxmind(ip)
        return self._lookup_geoip_api(ip)

    def _lookup_geoip_maxmind(self, ip: str) -> Optional[GeoInfo]:
        """Lookup GeoIP from local MaxMind database."""
        try:
            data = self._geo_db.get(ip)
            if not data:
                return None
            return GeoInfo(
                country=data.get("country", {}).get("names", {}).get("en", ""),
                country_code=data.get("country", {}).get("iso_code", ""),
                city=data.get("city", {}).get("names", {}).get("en", ""),
                latitude=data.get("location", {}).get("latitude", 0.0),
                longitude=data.get("location", {}).get("longitude", 0.0),
            )
        except Exception:
            return None

    def _lookup_geoip_api(self, ip: str) -> Optional[GeoInfo]:
        """Fallback: use free ip-api.com for GeoIP data."""
        try:
            url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,lat,lon"
            req = urllib.request.Request(url, headers={"User-Agent": "NetScope/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
            if data.get("status") == "success":
                return GeoInfo(
                    country=data.get("country", ""),
                    country_code=data.get("countryCode", ""),
                    city=data.get("city", ""),
                    latitude=data.get("lat", 0.0),
                    longitude=data.get("lon", 0.0),
                )
        except Exception:
            pass
        return None

    def _lookup_asn(self, ip: str) -> Optional[NetworkInfo]:
        """Lookup ASN/ISP from MaxMind ASN database."""
        if not self._asn_db:
            return None
        try:
            data = self._asn_db.get(ip)
            if not data:
                return None
            return NetworkInfo(
                asn=data.get("autonomous_system_number", 0),
                isp=data.get("autonomous_system_organization", ""),
                org=data.get("autonomous_system_organization", ""),
            )
        except Exception:
            return None

    def _reverse_dns(self, ip: str) -> str:
        """Reverse DNS lookup with short timeout."""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except (socket.herror, socket.gaierror, OSError):
            return ""

    def close(self):
        """Clean up database connections."""
        if self._geo_db:
            self._geo_db.close()
        if self._asn_db:
            self._asn_db.close()
