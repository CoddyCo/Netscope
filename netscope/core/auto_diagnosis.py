"""
Auto-Diagnosis Engine

Analyzes all collected data (route trace, DNS, connection breakdown,
bandwidth) and produces a plain-language diagnosis with:
- Root cause identification
- Bottleneck detection (which hop causes the most delay)
- Actionable recommendations
"""

from __future__ import annotations

from netscope.core.dynamodb_client import DynamoDBClient
from netscope.core.models import (
    Bottleneck, ConnectionBreakdown, Diagnosis, DNSResult,
    BandwidthResult, Hop, TraceSummary,
)


class AutoDiagnosisEngine:
    """Analyzes trace data and produces automated diagnostics."""

    def diagnose(self, summary: TraceSummary) -> Diagnosis:
        """Run full diagnosis on a completed trace."""
        diagnosis = Diagnosis()
        diagnosis.bottlenecks = self._find_bottlenecks(summary.hops)

        # Analyze each layer
        issues = []

        # 1. Route analysis
        route_issue = self._analyze_route(summary)
        if route_issue:
            issues.append(route_issue)

        # 2. DNS analysis
        dns_issue = self._analyze_dns(summary.dns_results)
        if dns_issue:
            issues.append(dns_issue)

        # 3. Connection breakdown analysis
        conn_issue = self._analyze_connection(summary.connection)
        if conn_issue:
            issues.append(conn_issue)

        # 4. Bandwidth analysis
        bw_issue = self._analyze_bandwidth(summary.bandwidth, summary.avg_latency)
        if bw_issue:
            issues.append(bw_issue)

        # Determine root cause and severity
        if not issues:
            diagnosis.root_cause = "No issues detected"
            diagnosis.description = (
                f"Connection to {summary.target} is healthy. "
                f"Average latency is {summary.avg_latency:.0f}ms with "
                f"{summary.packet_loss:.0f}% packet loss across {summary.total_hops} hops."
            )
            diagnosis.severity = "info"
        else:
            # Pick the most severe issue as root cause
            primary = issues[0]
            diagnosis.root_cause = primary["cause"]
            diagnosis.description = primary["description"]
            diagnosis.severity = primary["severity"]

            for issue in issues:
                diagnosis.recommendations.extend(issue.get("recommendations", []))

        return diagnosis

    def _find_bottlenecks(self, hops: list[Hop]) -> list[Bottleneck]:
        """Find hops with the largest latency jumps."""
        if len(hops) < 2:
            return []

        bottlenecks = []
        total_latency = max(h.avg_rtt for h in hops if not h.is_timeout and h.avg_rtt > 0) if hops else 0

        prev_rtt = 0.0
        for hop in hops:
            if hop.is_timeout or hop.avg_rtt <= 0:
                continue

            jump = hop.avg_rtt - prev_rtt
            if jump > 0:
                pct = (jump / total_latency * 100) if total_latency > 0 else 0

                # Flag as bottleneck if jump is >30% of total OR >50ms
                if pct > 30 or jump > 50:
                    location = ""
                    if hop.geo and hop.geo.city:
                        location = f"{hop.geo.city}, {hop.geo.country_code}"
                    elif hop.geo and hop.geo.country:
                        location = hop.geo.country

                    category = self._categorize_hop(hop)

                    bottlenecks.append(Bottleneck(
                        hop_number=hop.hop_number,
                        hop_ip=hop.ip,
                        hop_location=location,
                        latency_jump_ms=round(jump, 1),
                        percentage_of_total=round(pct, 1),
                        category=category,
                        description=(
                            f"Latency jumped by {jump:.0f}ms at hop {hop.hop_number} "
                            f"({location or hop.ip}) — {pct:.0f}% of total delay"
                        ),
                    ))

            prev_rtt = hop.avg_rtt

        # Sort by impact (largest jump first)
        bottlenecks.sort(key=lambda b: b.latency_jump_ms, reverse=True)
        return bottlenecks

    def _categorize_hop(self, hop: Hop) -> str:
        """Categorize a hop based on its network info."""
        if hop.cloud:
            return f"Cloud ({hop.cloud.provider})"
        if hop.network and hop.network.isp:
            isp = hop.network.isp.lower()
            if any(kw in isp for kw in ["airtel", "jio", "bsnl", "vodafone", "at&t", "comcast"]):
                return "ISP Gateway"
        if hop.geo:
            # Check if this is an international hop
            # (comparing countries would require knowing previous hop)
            pass
        return "Network Router"

    def _analyze_route(self, summary: TraceSummary) -> dict | None:
        """Analyze the route for issues."""
        issues = []
        recommendations = []
        severity = "info"

        # Check for packet loss
        end_to_end_loss = 0.0
        if summary.hops:
            end_to_end_loss = summary.hops[-1].packet_loss

        intermediate_loss = any(h.packet_loss > 0 for h in summary.hops[:-1]) if summary.hops else False

        if end_to_end_loss > 5:
            severity = "critical"
            issues.append(f"{end_to_end_loss:.0f}% end-to-end packet loss detected")
            recommendations.append(
                "High end-to-end packet loss indicates network congestion or hardware issues. "
                "Contact your ISP if this persists."
            )
        elif intermediate_loss:
            if severity == "info":
                severity = "warning"
            issues.append("ICMP response loss detected on intermediate hops (likely rate limiting)")
            recommendations.append(
                "Intermediate hops are dropping packets but the destination is fine. "
                "This is usually normal router behavior (ICMP rate limiting) and can be ignored."
            )

        # Check for high latency
        if summary.avg_latency > 200:
            if severity != "critical":
                severity = "warning"
            issues.append(f"High average latency ({summary.avg_latency:.0f}ms)")
            
        # Routing-Regression Detector
        try:
            ddb = DynamoDBClient()
            hist_avg = ddb.get_historical_average_latency(summary.target)
            
            if hist_avg is not None and hist_avg > 0:
                if summary.avg_latency > (hist_avg * 1.5):
                    if severity == "info":
                        severity = "warning"
                    issues.append(f"Routing Regression Detected! Current latency ({summary.avg_latency:.0f}ms) is >50% higher than historical average ({hist_avg:.0f}ms)")
                    recommendations.append("A routing regression has been detected. This suggests that the current path is suboptimal compared to historical routes to this target.")
        except Exception:
            pass

        # Check for bottleneck hops
        bottlenecks = self._find_bottlenecks(summary.hops)
        if bottlenecks:
            top = bottlenecks[0]
            if top.percentage_of_total > 50:
                if severity == "info":
                    severity = "warning"
                issues.append(
                    f"Hop {top.hop_number} ({top.category}) at {top.hop_location or top.hop_ip} "
                    f"accounts for {top.percentage_of_total:.0f}% of total latency"
                )

                if "ISP" in top.category:
                    recommendations.append(
                        f"Your ISP's gateway at {top.hop_location or top.hop_ip} is causing "
                        f"{top.latency_jump_ms:.0f}ms of delay. A VPN routing around this "
                        f"gateway may reduce latency."
                    )
                elif "Cloud" in top.category:
                    recommendations.append(
                        f"The {top.category} hop is adding significant latency. "
                        f"Consider using a closer cloud region or CDN."
                    )

        if not issues:
            return None

        return {
            "cause": "ISP routing inefficiency" if any("ISP" in b.category for b in bottlenecks) else "Network latency",
            "description": ". ".join(issues),
            "severity": severity,
            "recommendations": recommendations,
        }

    def _analyze_dns(self, dns_results: list[DNSResult]) -> dict | None:
        """Analyze DNS results for issues."""
        if not dns_results:
            return None

        issues = []
        recommendations = []

        # Check for DNS hijacking
        ips = set(r.resolved_ip for r in dns_results if r.resolved_ip)
        if len(ips) > 1:
            issues.append("DNS servers resolve to different IPs — possible DNS hijacking")
            recommendations.append(
                "Your ISP DNS may be hijacking DNS responses. "
                "Switch to Cloudflare (1.1.1.1) or Google (8.8.8.8) DNS."
            )

        # Check for slow DNS
        system_dns = next((r for r in dns_results if "System" in r.server_name), None)
        fastest = min(dns_results, key=lambda r: r.response_time_ms) if dns_results else None

        if system_dns and fastest and system_dns != fastest:
            if system_dns.response_time_ms > fastest.response_time_ms * 2:
                saving = system_dns.response_time_ms - fastest.response_time_ms
                issues.append(
                    f"System DNS is {system_dns.response_time_ms:.0f}ms vs "
                    f"{fastest.server_name} at {fastest.response_time_ms:.0f}ms"
                )
                recommendations.append(
                    f"Switch to {fastest.server_name} ({fastest.server_ip}) "
                    f"to save {saving:.0f}ms on DNS resolution."
                )

        if not issues:
            return None

        return {
            "cause": "DNS issue",
            "description": ". ".join(issues),
            "severity": "warning",
            "recommendations": recommendations,
        }

    def _analyze_connection(self, conn: ConnectionBreakdown | None) -> dict | None:
        """Analyze connection breakdown for issues."""
        if not conn:
            return None

        issues = []
        recommendations = []

        if conn.tls_ms > 200:
            issues.append(f"TLS handshake is slow ({conn.tls_ms:.0f}ms)")
            recommendations.append(
                "Slow TLS handshake may indicate server is far away or overloaded."
            )

        if conn.ttfb_ms > 500:
            issues.append(f"Time to First Byte is high ({conn.ttfb_ms:.0f}ms)")
            recommendations.append(
                "High TTFB suggests the server is processing slowly. "
                "This is a server-side issue, not a network issue."
            )

        if not issues:
            return None

        return {
            "cause": "Server response delay",
            "description": ". ".join(issues),
            "severity": "warning",
            "recommendations": recommendations,
        }

    def _analyze_bandwidth(self, bw: BandwidthResult | None,
                            avg_latency: float) -> dict | None:
        """Analyze bandwidth vs latency to distinguish the two."""
        if not bw:
            return None

        if bw.download_mbps < 5 and avg_latency < 100:
            return {
                "cause": "Low bandwidth",
                "description": (
                    f"Download speed is {bw.download_mbps:.1f} Mbps but latency is fine "
                    f"({avg_latency:.0f}ms). The issue is bandwidth, not routing."
                ),
                "severity": "warning",
                "recommendations": [
                    "Your connection has low bandwidth. This affects download speeds "
                    "but not latency. Consider upgrading your internet plan."
                ],
            }

        return None
