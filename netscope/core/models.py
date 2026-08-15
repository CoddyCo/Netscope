"""
NetScope Data Models

Core dataclasses representing hops, traces, and diagnostic results.
These are the common language shared between the C++ engine,
the enrichment pipeline, the GUI, and the export system.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class GeoInfo:
    """Geographic location for a network hop."""
    country: str = ""
    country_code: str = ""
    city: str = ""
    latitude: float = 0.0
    longitude: float = 0.0


@dataclass
class NetworkInfo:
    """ASN and ISP information for a network hop."""
    asn: int = 0
    isp: str = ""
    org: str = ""


@dataclass
class CloudInfo:
    """Cloud/CDN provider identification."""
    provider: str = ""      # "AWS", "Google Cloud", "Cloudflare"
    region: str = ""        # "ap-south-1", "us-east-1"
    service: str = ""       # "EC2", "CDN", "GCE"


@dataclass
class Hop:
    """Enriched data for a single hop in a traceroute."""
    hop_number: int = 0
    ip: str = ""
    hostname: str = ""
    rtts: list[float] = field(default_factory=list)
    avg_rtt: float = 0.0
    min_rtt: float = 0.0
    max_rtt: float = 0.0
    geo: Optional[GeoInfo] = None
    network: Optional[NetworkInfo] = None
    cloud: Optional[CloudInfo] = None
    packet_loss: float = 0.0
    is_timeout: bool = False
    is_destination: bool = False

    @property
    def latency_jump(self) -> float:
        """Latency increase compared to what would be stored as previous hop."""
        return 0.0  # Computed externally by the diagnosis engine

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Hop":
        hop = cls()
        for key, value in data.items():
            if key == "geo" and isinstance(value, dict):
                hop.geo = GeoInfo(**value)
            elif key == "network" and isinstance(value, dict):
                hop.network = NetworkInfo(**value)
            elif key == "cloud" and isinstance(value, dict):
                hop.cloud = CloudInfo(**value)
            elif hasattr(hop, key):
                setattr(hop, key, value)
        return hop


@dataclass
class ConnectionBreakdown:
    """Latency breakdown for a connection to a destination."""
    dns_ms: float = 0.0
    tcp_ms: float = 0.0
    tls_ms: float = 0.0
    ttfb_ms: float = 0.0     # Time to first byte
    total_ms: float = 0.0
    dns_server: str = ""
    tls_version: str = ""
    certificate_valid: bool = True
    certificate_expiry: str = ""


@dataclass
class DNSResult:
    """DNS analysis result for a single DNS server."""
    server_name: str = ""       # "Google DNS", "Cloudflare", "ISP DNS"
    server_ip: str = ""         # "8.8.8.8"
    resolved_ip: str = ""
    response_time_ms: float = 0.0
    is_match: bool = True       # Does it resolve to the same IP as others?


@dataclass
class BandwidthResult:
    """Bandwidth estimation result."""
    download_mbps: float = 0.0
    upload_mbps: float = 0.0
    test_server: str = ""
    test_duration_ms: float = 0.0


@dataclass
class Bottleneck:
    """An identified bottleneck in the network path."""
    hop_number: int = 0
    hop_ip: str = ""
    hop_location: str = ""
    latency_jump_ms: float = 0.0
    percentage_of_total: float = 0.0
    category: str = ""          # "ISP Gateway", "International Link", "CDN Edge"
    description: str = ""


@dataclass
class Diagnosis:
    """Automated diagnosis result."""
    root_cause: str = ""
    description: str = ""
    recommendations: list[str] = field(default_factory=list)
    bottlenecks: list[Bottleneck] = field(default_factory=list)
    severity: str = "info"      # "info", "warning", "critical"


@dataclass
class HealthScore:
    """Detailed breakdown of network health and penalties."""
    score: int = 100
    rating: str = ""
    packet_loss_penalty: int = 0
    latency_penalty: int = 0
    jitter_penalty: int = 0
    timeout_penalty: int = 0
    hop_loss_penalty: int = 0


@dataclass
class TraceSummary:
    """Complete result of a network diagnostic session."""
    target: str = ""
    resolved_ip: str = ""
    total_hops: int = 0
    avg_latency: float = 0.0
    max_latency: float = 0.0
    min_latency: float = 0.0
    packet_loss: float = 0.0
    countries: list[str] = field(default_factory=list)
    cloud_providers: list[str] = field(default_factory=list)
    health: Optional[HealthScore] = None
    duration_ms: float = 0.0
    timestamp: str = ""
    hops: list[Hop] = field(default_factory=list)
    connection: Optional[ConnectionBreakdown] = None
    dns_results: list[DNSResult] = field(default_factory=list)
    bandwidth: Optional[BandwidthResult] = None
    diagnosis: Optional[Diagnosis] = None
    historical_average: Optional[float] = None

    def to_dict(self) -> dict:
        d = {
            "target": self.target,
            "resolved_ip": self.resolved_ip,
            "total_hops": self.total_hops,
            "avg_latency": self.avg_latency,
            "max_latency": self.max_latency,
            "min_latency": self.min_latency,
            "packet_loss": self.packet_loss,
            "countries": self.countries,
            "cloud_providers": self.cloud_providers,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "historical_average": self.historical_average,
            "hops": [h.to_dict() for h in self.hops],
        }
        if self.connection:
            d["connection"] = asdict(self.connection)
        if self.dns_results:
            d["dns_results"] = [asdict(r) for r in self.dns_results]
        if self.bandwidth:
            d["bandwidth"] = asdict(self.bandwidth)
        if self.diagnosis:
            d["diagnosis"] = asdict(self.diagnosis)
        if self.health:
            d["health"] = asdict(self.health)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "TraceSummary":
        summary = cls()
        for key, value in data.items():
            if key == "hops" and isinstance(value, list):
                summary.hops = [Hop.from_dict(h) for h in value]
            elif key == "connection" and isinstance(value, dict):
                summary.connection = ConnectionBreakdown(**value)
            elif key == "dns_results" and isinstance(value, list):
                summary.dns_results = [DNSResult(**r) for r in value]
            elif key == "bandwidth" and isinstance(value, dict):
                summary.bandwidth = BandwidthResult(**value)
            elif key == "diagnosis" and isinstance(value, dict):
                bottlenecks = [Bottleneck(**b) for b in value.pop("bottlenecks", [])]
                summary.diagnosis = Diagnosis(**value, bottlenecks=bottlenecks)
            elif key == "health" and isinstance(value, dict):
                summary.health = HealthScore(**value)
            elif hasattr(summary, key):
                setattr(summary, key, value)
        return summary

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "TraceSummary":
        return cls.from_dict(json.loads(json_str))
