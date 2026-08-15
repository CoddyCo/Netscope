"""
DNS Diagnostics Module

Tests DNS resolution across multiple providers to detect:
- Slow DNS servers
- DNS hijacking (ISP resolving to different IPs)
- Optimal DNS provider recommendation
"""

from __future__ import annotations

import socket
import struct
import time
from typing import Optional

from netscope.core.models import DNSResult


# Well-known public DNS servers to compare against
DNS_SERVERS = [
    ("Google DNS", "8.8.8.8"),
    ("Cloudflare", "1.1.1.1"),
    ("Quad9", "9.9.9.9"),
]


class DNSDiagnostics:
    """Analyzes DNS resolution across multiple providers."""

    def analyze(self, domain: str) -> list[DNSResult]:
        """Resolve a domain using multiple DNS servers and compare results."""
        results = []

        # First, resolve using the system default DNS (ISP)
        isp_result = self._resolve_system(domain)
        if isp_result:
            results.append(isp_result)

        # Then resolve using well-known public DNS servers
        for name, server_ip in DNS_SERVERS:
            result = self._resolve_with_server(domain, name, server_ip)
            if result:
                results.append(result)

        # Check if all servers resolve to the same IP
        if results:
            reference_ip = results[0].resolved_ip
            for r in results:
                r.is_match = (r.resolved_ip == reference_ip)

        return results

    def _resolve_system(self, domain: str) -> Optional[DNSResult]:
        """Resolve using the system's default DNS server."""
        try:
            start = time.perf_counter()
            ip = socket.gethostbyname(domain)
            elapsed = (time.perf_counter() - start) * 1000

            return DNSResult(
                server_name="System DNS (ISP)",
                server_ip="default",
                resolved_ip=ip,
                response_time_ms=round(elapsed, 2),
                is_match=True,
            )
        except socket.gaierror:
            return None

    def _resolve_with_server(self, domain: str, server_name: str,
                              server_ip: str) -> Optional[DNSResult]:
        """Resolve a domain using a specific DNS server via raw UDP query."""
        try:
            # Build a minimal DNS query packet
            query = self._build_dns_query(domain)

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)

            start = time.perf_counter()
            sock.sendto(query, (server_ip, 53))
            response, _ = sock.recvfrom(512)
            elapsed = (time.perf_counter() - start) * 1000

            sock.close()

            # Parse the response to extract the resolved IP
            resolved_ip = self._parse_dns_response(response)

            return DNSResult(
                server_name=server_name,
                server_ip=server_ip,
                resolved_ip=resolved_ip or "",
                response_time_ms=round(elapsed, 2),
                is_match=True,
            )
        except Exception:
            return None

    def _build_dns_query(self, domain: str) -> bytes:
        """Build a minimal DNS A record query packet."""
        # Header: ID, flags, qdcount=1, ancount=0, nscount=0, arcount=0
        header = struct.pack(">HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)

        # Question section: domain name + type A (1) + class IN (1)
        question = b""
        for label in domain.split("."):
            question += struct.pack("B", len(label)) + label.encode()
        question += b"\x00"  # Root label
        question += struct.pack(">HH", 1, 1)  # Type A, Class IN

        return header + question

    def _parse_dns_response(self, response: bytes) -> Optional[str]:
        """Extract the first A record IP from a DNS response."""
        if len(response) < 12:
            return None

        # Skip header (12 bytes) and question section
        offset = 12

        # Skip question section
        while offset < len(response) and response[offset] != 0:
            length = response[offset]
            if length & 0xC0 == 0xC0:  # Compressed label
                offset += 2
                break
            offset += length + 1
        else:
            offset += 1  # Skip null terminator

        offset += 4  # Skip QTYPE and QCLASS

        # Parse answer section
        while offset < len(response):
            # Skip name (might be compressed)
            if offset < len(response) and response[offset] & 0xC0 == 0xC0:
                offset += 2
            else:
                while offset < len(response) and response[offset] != 0:
                    offset += response[offset] + 1
                offset += 1

            if offset + 10 > len(response):
                break

            rtype, rclass, ttl, rdlength = struct.unpack(
                ">HHIH", response[offset:offset + 10]
            )
            offset += 10

            if rtype == 1 and rdlength == 4:  # A record
                ip_bytes = response[offset:offset + 4]
                return socket.inet_ntoa(ip_bytes)

            offset += rdlength

        return None
