"""
Trace Controller

Orchestrates the full diagnostic pipeline:
1. DNS resolution
2. Route tracing (via C++ engine)
3. Per-hop enrichment (GeoIP, ASN, cloud detection)
4. DNS diagnostics (multi-provider comparison)
5. Connection profiling (DNS/TCP/TLS/TTFB breakdown)
6. Bandwidth estimation
7. Auto-diagnosis
8. Health scoring
9. Database persistence

Runs in a QThread so the GUI stays responsive.
Communicates with the GUI via Qt Signals.
"""

from __future__ import annotations

import json
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from netscope.core.auto_diagnosis import AutoDiagnosisEngine
from netscope.core.bandwidth_estimator import BandwidthEstimator
from netscope.core.cloud_detector import CloudDetector
from netscope.core.connection_profiler import ConnectionProfiler
from netscope.core.database import NetScopeDB
from netscope.core.dns_diagnostics import DNSDiagnostics
from netscope.core.dynamodb_client import DynamoDBClient
from netscope.core.enrichment import EnrichmentPipeline
from netscope.core.health_score import compute_health_score
from netscope.core.models import Hop, TraceSummary
from netscope.utils.validators import is_valid_ip, resolve_target, sanitize_input


class TraceWorker(QObject):
    """Worker that runs the diagnostic pipeline in a background thread."""

    # Signals emitted during the trace
    hop_received = pyqtSignal(object)       # Emits enriched Hop
    trace_complete = pyqtSignal(object)     # Emits TraceSummary
    trace_error = pyqtSignal(str)           # Emits error message
    status_update = pyqtSignal(str)         # Emits status text for the UI
    dns_results_ready = pyqtSignal(object)  # Emits list[DNSResult]
    connection_ready = pyqtSignal(object)   # Emits ConnectionBreakdown
    bandwidth_ready = pyqtSignal(object)    # Emits BandwidthResult

    def __init__(self, target: str, demo_mode: bool = False,
                 data_dir: str = "data"):
        super().__init__()
        self._target = target
        self._demo_mode = demo_mode
        self._data_dir = data_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        """Execute the full diagnostic pipeline."""
        try:
            if self._demo_mode:
                self._run_demo()
            else:
                self._run_live()
        except Exception as e:
            self.trace_error.emit(str(e))

    def _run_live(self):
        """Run a live diagnostic."""
        target = sanitize_input(self._target)
        self.status_update.emit(f"Resolving {target}...")

        # 1. Resolve target
        try:
            target_ip = resolve_target(target)
        except ValueError as e:
            self.trace_error.emit(str(e))
            return

        # 2. Initialize components
        cloud_detector = CloudDetector(
            str(Path(self._data_dir) / "cloud-ranges")
        )
        enrichment = EnrichmentPipeline(
            maxmind_city_path=str(Path(self._data_dir) / "maxmind" / "GeoLite2-City.mmdb"),
            maxmind_asn_path=str(Path(self._data_dir) / "maxmind" / "GeoLite2-ASN.mmdb"),
            cloud_detector=cloud_detector,
        )

        hops: list[Hop] = []
        start_time = time.perf_counter()

        # 3. Run traceroute
        self.status_update.emit(f"Tracing route to {target} ({target_ip})...")

        try:
            import netscope_core

            config = netscope_core.TraceConfig()
            config.max_hops = 30
            config.timeout_ms = 3000
            config.probes_per_hop = 3
            config.resolve_hostnames = True

            engine = netscope_core.TracerouteEngine(config)

            def on_hop(hop_result):
                if self._cancelled:
                    engine.cancel()
                    return

                enriched = enrichment.enrich_hop(
                    hop_number=hop_result.hop_number,
                    ip=hop_result.ip,
                    hostname=hop_result.hostname,
                    rtts=list(hop_result.rtts),
                    avg_rtt=hop_result.avg_rtt,
                    min_rtt=hop_result.min_rtt,
                    max_rtt=hop_result.max_rtt,
                    is_timeout=hop_result.is_timeout,
                    is_destination=hop_result.is_destination,
                )
                hops.append(enriched)
                self.hop_received.emit(enriched)

            engine.trace(target_ip, on_hop)

        except ImportError:
            # C++ module not available — use fallback traceroute parsing
            self._run_fallback_traceroute(target_ip, enrichment, hops)

        if self._cancelled:
            return

        # 4. DNS Diagnostics
        self.status_update.emit("Analyzing DNS...")
        dns_diag = DNSDiagnostics()
        dns_results = dns_diag.analyze(target)
        self.dns_results_ready.emit(dns_results)

        if self._cancelled:
            return

        # 5. Connection Profiling
        self.status_update.emit("Profiling connection layers...")
        profiler = ConnectionProfiler()
        conn = profiler.profile(target)
        self.connection_ready.emit(conn)

        if self._cancelled:
            return

        # 6. Bandwidth Estimation
        self.status_update.emit("Estimating bandwidth...")
        bw_estimator = BandwidthEstimator()
        bw_result = bw_estimator.estimate(timeout=10)
        if bw_result:
            self.bandwidth_ready.emit(bw_result)

        # 7. Build summary
        duration = (time.perf_counter() - start_time) * 1000

        valid_rtts = [h.avg_rtt for h in hops if not h.is_timeout and h.avg_rtt > 0]
        total_probes = sum(len(h.rtts) for h in hops)
        lost_probes = sum(sum(1 for r in h.rtts if r < 0) for h in hops)
        countries = list(dict.fromkeys(
            h.geo.country_code for h in hops if h.geo and h.geo.country_code
        ))
        cloud_providers = list(dict.fromkeys(
            h.cloud.provider for h in hops if h.cloud
        ))

        avg_latency = sum(valid_rtts) / len(valid_rtts) if valid_rtts else 0
        packet_loss = (lost_probes / total_probes * 100) if total_probes > 0 else 0

        health = compute_health_score(
            hops, avg_latency, packet_loss
        )

        # Fetch historical baseline
        hist_avg = None
        try:
            ddb = DynamoDBClient()
            hist_avg = ddb.get_historical_average_latency(target)
        except Exception:
            pass
            
        summary = TraceSummary(
            target=target,
            resolved_ip=target_ip,
            total_hops=len(hops),
            avg_latency=round(avg_latency, 1),
            max_latency=round(max(valid_rtts), 1) if valid_rtts else 0,
            min_latency=round(min(valid_rtts), 1) if valid_rtts else 0,
            packet_loss=round(packet_loss, 1),
            countries=countries,
            cloud_providers=cloud_providers,
            health=health,
            duration_ms=round(duration, 1),
            timestamp=datetime.now().isoformat(),
            hops=hops,
            connection=conn,
            dns_results=dns_results,
            bandwidth=bw_result,
            historical_average=hist_avg,
        )

        # 8. Auto-diagnosis
        self.status_update.emit("Running diagnosis...")
        diagnosis_engine = AutoDiagnosisEngine()
        summary.diagnosis = diagnosis_engine.diagnose(summary)

        # 9. Save to database
        try:
            db = NetScopeDB()
            db.save_trace(summary)
            db.close()
            
            ddb = DynamoDBClient()
            ddb.save_trace(
                target=summary.target,
                ip=summary.resolved_ip,
                timestamp=summary.timestamp,
                latency=summary.avg_latency
            )
        except Exception:
            pass  # DB errors shouldn't break the trace

        enrichment.close()
        self.status_update.emit("Complete")
        self.trace_complete.emit(summary)

    def _run_fallback_traceroute(self, target_ip: str,
                                  enrichment: EnrichmentPipeline,
                                  hops: list[Hop]):
        """Fallback: parse OS traceroute command output."""
        import subprocess
        import re

        cmd = ["traceroute", "-n", "-q", "3", "-m", "30", "-w", "3", target_ip]
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
        except FileNotFoundError:
            self.trace_error.emit("traceroute command not found. Install with: sudo apt install traceroute")
            return

        ip_re = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
        rtt_re = re.compile(r"([\d.]+)\s*ms")

        for line in proc.stdout:
            if self._cancelled:
                proc.kill()
                break

            line = line.strip()
            parts = line.split()
            if not parts or not parts[0].isdigit():
                continue

            hop_num = int(parts[0])
            rest = " ".join(parts[1:])

            ip_match = ip_re.search(rest)
            ip = ip_match.group(1) if ip_match else ""

            rtts = [float(m.group(1)) for m in rtt_re.finditer(rest)]
            if not rtts:
                rtts = [-1.0, -1.0, -1.0]

            valid = [r for r in rtts if r >= 0]
            avg_rtt = sum(valid) / len(valid) if valid else -1
            is_timeout = len(valid) == 0

            enriched = enrichment.enrich_hop(
                hop_number=hop_num, ip=ip, hostname="",
                rtts=rtts, avg_rtt=avg_rtt,
                min_rtt=min(valid) if valid else -1,
                max_rtt=max(valid) if valid else -1,
                is_timeout=is_timeout,
                is_destination=(ip == target_ip),
            )
            hops.append(enriched)
            self.hop_received.emit(enriched)

            if ip == target_ip:
                break

        proc.wait()

    def _run_demo(self):
        """Run in demo mode — load pre-recorded trace data."""
        demo_dir = Path("demo")
        target = sanitize_input(self._target)

        # Try to find a demo file matching the target
        demo_file = demo_dir / f"{target.split('.')[0]}.json"
        if not demo_file.exists():
            # Try any available demo file
            demo_files = list(demo_dir.glob("*.json"))
            if demo_files:
                demo_file = demo_files[0]
            else:
                self.trace_error.emit("No demo data available")
                return

        self.status_update.emit(f"Loading demo trace for {target}...")

        with open(demo_file) as f:
            data = json.load(f)

        summary = TraceSummary.from_dict(data)

        # Simulate hop-by-hop discovery with delays
        for hop in summary.hops:
            if self._cancelled:
                return
            time.sleep(0.3)  # Simulate network delay
            self.hop_received.emit(hop)

        self.status_update.emit("Complete (demo mode)")
        self.trace_complete.emit(summary)


class TraceController(QObject):
    """Controls trace execution from the GUI layer."""

    # Re-export worker signals for GUI binding
    hop_received = pyqtSignal(object)
    trace_complete = pyqtSignal(object)
    trace_error = pyqtSignal(str)
    status_update = pyqtSignal(str)
    dns_results_ready = pyqtSignal(object)
    connection_ready = pyqtSignal(object)
    bandwidth_ready = pyqtSignal(object)

    def __init__(self, demo_mode: bool = False):
        super().__init__()
        self._thread: Optional[QThread] = None
        self._worker: Optional[TraceWorker] = None
        self._demo_mode = demo_mode

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def start_trace(self, target: str):
        """Start a new diagnostic trace."""
        if self.is_running:
            self.cancel()

        self._thread = QThread()
        self._worker = TraceWorker(target, demo_mode=self._demo_mode)
        self._worker.moveToThread(self._thread)

        # Connect worker signals to controller signals (relay to GUI)
        self._worker.hop_received.connect(self.hop_received)
        self._worker.trace_complete.connect(self._on_complete)
        self._worker.trace_error.connect(self.trace_error)
        self._worker.status_update.connect(self.status_update)
        self._worker.dns_results_ready.connect(self.dns_results_ready)
        self._worker.connection_ready.connect(self.connection_ready)
        self._worker.bandwidth_ready.connect(self.bandwidth_ready)

        self._thread.started.connect(self._worker.run)
        self._thread.start()

    def cancel(self):
        """Cancel the running trace."""
        if self._worker:
            self._worker.cancel()
        if self._thread:
            self._thread.quit()
            self._thread.wait(5000)
            self._thread = None
            self._worker = None

    def _on_complete(self, summary):
        """Handle trace completion."""
        self.trace_complete.emit(summary)
        if self._thread:
            self._thread.quit()
            self._thread.wait(5000)
