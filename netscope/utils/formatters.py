"""
Formatting Utilities
"""

from __future__ import annotations


# Country code to flag emoji mapping
COUNTRY_FLAGS = {
    "US": "🇺🇸", "IN": "🇮🇳", "GB": "🇬🇧", "DE": "🇩🇪", "FR": "🇫🇷",
    "JP": "🇯🇵", "SG": "🇸🇬", "AU": "🇦🇺", "CA": "🇨🇦", "BR": "🇧🇷",
    "NL": "🇳🇱", "SE": "🇸🇪", "IE": "🇮🇪", "HK": "🇭🇰", "KR": "🇰🇷",
    "TW": "🇹🇼", "FI": "🇫🇮", "IT": "🇮🇹", "ES": "🇪🇸", "CH": "🇨🇭",
    "RU": "🇷🇺", "CN": "🇨🇳", "ZA": "🇿🇦", "AE": "🇦🇪", "SA": "🇸🇦",
}


def format_latency(ms: float) -> str:
    """Format latency with color-coding indicator."""
    if ms < 0:
        return "* (timeout)"
    if ms < 30:
        return f"{ms:.1f}ms"
    if ms < 100:
        return f"{ms:.0f}ms"
    return f"{ms:.0f}ms"


def latency_color(ms: float) -> str:
    """Get a color for a latency value (for GUI use)."""
    if ms < 0:
        return "#FF4444"    # Red — timeout
    if ms < 30:
        return "#00FF88"    # Green — excellent
    if ms < 80:
        return "#88FF00"    # Light green — good
    if ms < 150:
        return "#FFBB00"    # Yellow — moderate
    if ms < 300:
        return "#FF8800"    # Orange — slow
    return "#FF4444"        # Red — very slow


def format_ip(ip: str, hostname: str = "") -> str:
    """Format IP with optional hostname."""
    if hostname and hostname != ip:
        return f"{hostname} ({ip})"
    return ip


def country_flag(country_code: str) -> str:
    """Get a flag emoji for a country code."""
    return COUNTRY_FLAGS.get(country_code.upper(), "🌍")


def format_route_countries(countries: list[str]) -> str:
    """Format a list of country codes as a route string with flags."""
    if not countries:
        return "—"
    flags = [f"{country_flag(c)} {c}" for c in countries]
    return " → ".join(flags)


def format_bytes(n: float) -> str:
    """Format a byte count to human-readable."""
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def format_mbps(mbps: float) -> str:
    """Format a Mbps value."""
    if mbps >= 100:
        return f"{mbps:.0f} Mbps"
    if mbps >= 10:
        return f"{mbps:.1f} Mbps"
    return f"{mbps:.2f} Mbps"
