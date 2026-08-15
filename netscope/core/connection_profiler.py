"""
Connection Profiler

Decomposes total connection latency into separate phases:
1. DNS Resolution
2. TCP Handshake (SYN → SYN-ACK)
3. TLS Handshake
4. Time to First Byte (TTFB)

This answers: "WHERE in the connection process is the delay?"
"""

from __future__ import annotations

import socket
import ssl
import time
from typing import Optional

from netscope.core.models import ConnectionBreakdown


class ConnectionProfiler:
    """Measures latency for each phase of a TCP/TLS connection."""

    def profile(self, host: str, port: int = 443,
                timeout: float = 10.0) -> ConnectionBreakdown:
        """Profile a connection to host:port, measuring each phase."""
        result = ConnectionBreakdown()

        # Phase 1: DNS Resolution
        dns_start = time.perf_counter()
        try:
            ip = socket.gethostbyname(host)
            result.dns_ms = round((time.perf_counter() - dns_start) * 1000, 2)
            result.dns_server = "system"
        except socket.gaierror:
            result.dns_ms = -1
            result.total_ms = -1
            return result

        # Phase 2: TCP Handshake
        tcp_start = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((ip, port))
            result.tcp_ms = round((time.perf_counter() - tcp_start) * 1000, 2)
        except (socket.timeout, ConnectionRefusedError, OSError):
            result.tcp_ms = -1
            result.total_ms = -1
            sock.close()
            return result

        # Phase 3: TLS Handshake (if port 443 or TLS expected)
        if port == 443:
            tls_start = time.perf_counter()
            try:
                context = ssl.create_default_context()
                tls_sock = context.wrap_socket(sock, server_hostname=host)
                result.tls_ms = round((time.perf_counter() - tls_start) * 1000, 2)

                # Extract TLS info
                result.tls_version = tls_sock.version() or ""
                cert = tls_sock.getpeercert()
                if cert:
                    result.certificate_valid = True
                    result.certificate_expiry = cert.get("notAfter", "")

                # Phase 4: Time to First Byte (send HTTP request, measure response)
                ttfb_start = time.perf_counter()
                request = (
                    f"GET / HTTP/1.1\r\n"
                    f"Host: {host}\r\n"
                    f"Connection: close\r\n"
                    f"User-Agent: NetScope/1.0\r\n"
                    f"\r\n"
                )
                tls_sock.sendall(request.encode())
                _ = tls_sock.recv(1)  # First byte of response
                result.ttfb_ms = round((time.perf_counter() - ttfb_start) * 1000, 2)

                tls_sock.close()
            except Exception:
                result.tls_ms = -1
                sock.close()
        else:
            # Non-TLS connection — skip TLS, measure TTFB directly
            result.tls_ms = 0
            try:
                ttfb_start = time.perf_counter()
                request = (
                    f"GET / HTTP/1.1\r\n"
                    f"Host: {host}\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                )
                sock.sendall(request.encode())
                _ = sock.recv(1)
                result.ttfb_ms = round((time.perf_counter() - ttfb_start) * 1000, 2)
            except Exception:
                result.ttfb_ms = -1
            sock.close()

        # Compute total
        phases = [result.dns_ms, result.tcp_ms, result.tls_ms, result.ttfb_ms]
        valid = [p for p in phases if p >= 0]
        result.total_ms = round(sum(valid), 2)

        return result
