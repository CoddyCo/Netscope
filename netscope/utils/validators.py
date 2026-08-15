"""
Input Validation Utilities
"""

from __future__ import annotations

import re
import socket


def is_valid_domain(s: str) -> bool:
    """Check if string is a valid domain name."""
    pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,}$"
    return bool(re.match(pattern, s.strip()))


def is_valid_ip(s: str) -> bool:
    """Check if string is a valid IPv4 address."""
    try:
        socket.inet_pton(socket.AF_INET, s.strip())
        return True
    except (socket.error, OSError):
        return False


def is_private_ip(ip: str) -> bool:
    """Check if IP is in RFC 1918 private ranges."""
    try:
        parts = [int(p) for p in ip.split(".")]
        if len(parts) != 4:
            return False
        # 10.0.0.0/8
        if parts[0] == 10:
            return True
        # 172.16.0.0/12
        if parts[0] == 172 and 16 <= parts[1] <= 31:
            return True
        # 192.168.0.0/16
        if parts[0] == 192 and parts[1] == 168:
            return True
        # 127.0.0.0/8 (loopback)
        if parts[0] == 127:
            return True
        return False
    except (ValueError, IndexError):
        return False


def sanitize_input(s: str) -> str:
    """Clean and validate user input."""
    s = s.strip().lower()
    # Remove protocol prefix if present
    for prefix in ["http://", "https://", "ftp://"]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    # Remove trailing path
    s = s.split("/")[0]
    # Remove port
    s = s.split(":")[0]
    return s


def resolve_target(target: str) -> str:
    """Resolve a domain name to an IP address."""
    if is_valid_ip(target):
        return target
    try:
        return socket.gethostbyname(target)
    except socket.gaierror as e:
        raise ValueError(f"Cannot resolve '{target}': {e}")
