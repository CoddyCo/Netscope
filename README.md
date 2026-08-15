<div align="center">

# 🌐 NetScope

https://github.com/user-attachments/assets/66bd2077-5577-4d05-af64-be242bebdb23

### Network Diagnostic & Intelligence Platform

*A high-performance, real-time network analysis tool that combines the raw speed of a C++ packet engine with the analytical depth of Python — wrapped in a cyberpunk-themed desktop interface.*

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![C++](https://img.shields.io/badge/C++-17-00599C?style=for-the-badge&logo=c%2B%2B&logoColor=white)
![AWS](https://img.shields.io/badge/AWS_DynamoDB-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

</div>

---

## 🔍 What is NetScope?

NetScope goes far beyond a standard `traceroute`. It is a **full network intelligence platform** that traces the path your packets take across the internet, enriches every hop with geographic and organizational data, diagnoses bottlenecks using heuristic algorithms, and persists historical baselines to the cloud so you can detect routing regressions over time.

**The core question NetScope answers is not just *"where do my packets go?"* but *"why is my connection slow, and where exactly is the problem?"***

---

## ✨ Key Features

### ⚡ High-Performance C++ Tracing Engine
The packet generation layer is written in **C++17** and exposed to Python via **PyBind11**. Unlike standard sequential traceroutes that take 10-15 seconds, NetScope fires packets with sliding TTLs in **parallel asynchronous bursts**, completing full traces in under 300ms.

### 🧠 Automated Diagnosis Engine
NetScope doesn't just show you raw data — it **tells you what's wrong**. The heuristics engine automatically detects:
- **ICMP Rate Limiting** — Distinguishes routers that deprioritize diagnostic packets from actual failures
- **International Link Crossings** — Suppresses latency warnings caused by the physics of undersea fiber optic cables
- **Last-Mile ISP Congestion** — Identifies WiFi/local network saturation vs upstream problems
- **Routing Regressions** — Compares current traces against historical AWS baselines to flag degradation

### 📊 Interactive Latency Visualization
Real-time **matplotlib** scatter plots embedded directly in the Qt interface. Click any data point on the chart to drill into that specific hop's details — IP, hostname, geolocation, ASN, cloud provider, and exact RTT breakdown.

### 🔬 Connection Profiling (Sub-millisecond Breakdown)
Decomposes total connection time into its individual TCP/IP phases:

| Phase | What It Measures |
|-------|-----------------|
| **DNS Lookup** | Time to resolve the hostname to an IP address |
| **TCP Connect** | The SYN → SYN-ACK handshake duration |
| **TLS Handshake** | Certificate negotiation time (reports TLS version) |
| **Time to First Byte** | Server processing + initial response delay |

### 🏥 Network Health Scoring
Every trace receives a score from **0 to 100** with a detailed penalty breakdown:
- Packet loss penalties (weighted by severity)
- Latency spike detection via standard deviation analysis
- Timeout penalties for unreachable endpoints
- Hop loss penalties for routes with excessive dead hops

### ☁️ Dual-Tier Persistence (Local + Cloud)
- **SQLite** — Local database (`~/.netscope/history.db`) for offline history, recent searches, and instant retrieval
- **AWS DynamoDB** — Cloud-synchronized latency telemetry via Boto3, enabling cross-session historical baseline overlays on the latency chart

### 🗺️ Geographic Route Mapping
Every hop is enriched with **MaxMind GeoIP** data, showing the countries your packets traverse. The hop timeline displays city names and country flags, revealing the physical path of your data across continents.

### ☁️ Cloud Provider Detection
A custom **C++ Radix Trie** loads 10,000+ CIDR blocks for AWS, GCP, and Cloudflare at startup. When your packets enter a cloud network, NetScope instantly identifies the provider — useful for understanding CDN routing behavior.

### 📡 Multi-Provider DNS Analysis
Compares DNS resolution across **Google DNS (8.8.8.8)**, **Cloudflare (1.1.1.1)**, and **Quad9 (9.9.9.9)** against your ISP's default resolver. Detects DNS hijacking (where your ISP resolves domains to different IPs) and recommends the fastest DNS provider.

### 📈 Bandwidth Estimation
Measures approximate download throughput by fetching test payloads from Cloudflare's speed test CDN, answering the critical question: *"Is this a latency problem or a bandwidth problem?"*

### 💾 JSON Export
One-click export of the complete trace data (all hops, enrichment, diagnosis) to a structured JSON file for integration with external monitoring tools or archival.

---

## 🏗️ Architecture

NetScope is a **hybrid C++/Python** application with strict separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation Layer (PyQt6)                   │
│  ┌──────────┐  ┌──────────────────┐  ┌───────────────────────┐ │
│  │   Left   │  │   Diagnostic     │  │    Right Sidebar      │ │
│  │ Sidebar  │  │   Dashboard      │  │  (Health, Stats,      │ │
│  │ (Route   │  │  (Latency Chart  │  │   Connection Profile) │ │
│  │  Info,   │  │   + Timeline)    │  │                       │ │
│  │ Recent)  │  │                  │  │  Diagnosis Panel      │ │
│  └──────────┘  └──────────────────┘  │  Hop Detail Drawer    │ │
│                                      └───────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                    Python Core (Orchestration)                  │
│  TraceController → Enrichment → AutoDiagnosis → HealthScore    │
│  ConnectionProfiler    DNSDiagnostics    BandwidthEstimator     │
├─────────────────────────────────────────────────────────────────┤
│                    C++ Engine (PyBind11)                        │
│  PacketBuilder    Traceroute (Async Burst)    CidrTrie (O(1))  │
├─────────────────────────────────────────────────────────────────┤
│                    Data Tier                                    │
│  ┌─────────────────────┐    ┌────────────────────────────────┐ │
│  │  SQLite (Local)      │    │  AWS DynamoDB (Cloud)          │ │
│  │  history.db          │    │  Historical Baselines          │ │
│  └─────────────────────┘    └────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

> For detailed technical documentation, see:
> - [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System design, concurrency model, and layer boundaries
> - [`docs/DIAGNOSTICS_ENGINE.md`](docs/DIAGNOSTICS_ENGINE.md) — Heuristic algorithms and scoring math
> - [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md) — Data flow from raw sockets to cloud persistence

---

## 🧰 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Packet Engine** | C++17, Raw Sockets | ICMP/UDP packet crafting, parallel TTL probing |
| **C++↔Python Bridge** | PyBind11 | Zero-copy data marshaling between engine and core |
| **Core Logic** | Python 3.10+ | Trace orchestration, enrichment, diagnostics |
| **GUI Framework** | PyQt6 | Reactive desktop interface with signal/slot architecture |
| **Visualization** | Matplotlib (QtAgg) | Embedded interactive latency charts |
| **GeoIP** | MaxMind MMDB | Offline IP-to-location mapping (<1ms per lookup) |
| **Cloud Detection** | Custom C++ Radix Trie | O(1) IP-to-cloud-provider attribution |
| **Local Storage** | SQLite | Offline trace history and recent search persistence |
| **Cloud Storage** | AWS DynamoDB + Boto3 | Cross-session latency baselines |
| **Build System** | CMake + setuptools | Compiles C++ engine and packages Python modules |
| **CI/CD** | GitHub Actions | Automated testing on push |

---

## 📁 Project Structure

```
netscope/
├── engine/                          # C++ High-Performance Core
│   ├── include/netscope/
│   │   ├── traceroute.hpp           # Async burst traceroute engine
│   │   ├── packet_builder.hpp       # Raw ICMP/UDP packet construction
│   │   ├── cidr_trie.hpp            # Radix Trie for cloud IP lookups
│   │   ├── platform.hpp             # Cross-platform socket abstraction
│   │   └── types.hpp                # Shared C++ data structures
│   ├── src/                         # C++ implementations
│   ├── bindings/py_netscope.cpp     # PyBind11 bridge to Python
│   └── tests/                       # C++ unit tests
│
├── netscope/                        # Python Application
│   ├── core/
│   │   ├── trace_controller.py      # QThread trace lifecycle manager
│   │   ├── enrichment.py            # Concurrent DNS + GeoIP + ASN enrichment
│   │   ├── auto_diagnosis.py        # Heuristic bottleneck detection
│   │   ├── health_score.py          # Penalty-based network scoring
│   │   ├── connection_profiler.py   # TCP/TLS phase decomposition
│   │   ├── dns_diagnostics.py       # Multi-provider DNS comparison
│   │   ├── bandwidth_estimator.py   # CDN-based throughput estimation
│   │   ├── cloud_detector.py        # AWS/GCP/Cloudflare IP attribution
│   │   ├── database.py              # SQLite persistence layer
│   │   ├── dynamodb_client.py       # AWS DynamoDB integration
│   │   └── models.py                # Core dataclasses (Hop, TraceSummary, etc.)
│   │
│   ├── gui/
│   │   ├── main_window.py           # Application shell and layout
│   │   ├── diagnostic_dashboard.py  # Central latency chart widget
│   │   ├── left_sidebar.py          # Route info + recent searches
│   │   ├── right_sidebar.py         # Health score + statistics + connection profile
│   │   ├── diagnosis_panel.py       # Auto-diagnosis results display
│   │   ├── hop_drawer.py            # Per-hop detail inspector
│   │   ├── hop_timeline.py          # Visual timeline of all hops
│   │   └── search_bar.py            # Target input with validation
│   │
│   ├── themes/cyberpunk.qss         # Custom Qt stylesheet (dark cyberpunk theme)
│   └── utils/                       # Formatting helpers and validators
│
├── data/cloud-ranges/               # AWS, GCP, Cloudflare CIDR block databases
├── docs/                            # Technical documentation
├── tests/                           # Python test suite
├── scripts/                         # Utility scripts
└── demo/                            # Sample trace output (google.com.json)
```

---

## 🚀 Installation

### Prerequisites
- **Linux / WSL** (requires raw socket access for ICMP)
- **Python 3.10+**
- **CMake 3.15+** and a C++17 compiler (g++ / clang++)
- **MaxMind GeoLite2 City database** (place `GeoLite2-City.mmdb` in `data/maxmind/`)

### Setup
```bash
# Clone the repository
git clone https://github.com/CoddyCo/Netscope.git
cd Netscope

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -e .

# Build the C++ engine
mkdir -p engine/build && cd engine/build
cmake ..
make -j$(nproc)
cp netscope_core*.so ../../    # Copy the compiled extension to root
cd ../..
```

### Run
```bash
# Requires sudo for raw ICMP socket access
sudo venv/bin/python -m netscope
```

### Optional: AWS DynamoDB (Cloud Baselines)
To enable historical baseline overlays via AWS:
```bash
pip install boto3
aws configure    # Set your AWS Access Key, Secret Key, and Region
```
> NetScope gracefully degrades if AWS is not configured — all local features work without it.

---

## 🎮 Usage

1. **Enter a target** — Type any domain (`google.com`) or IP address in the search bar
2. **Click Trace Route** — The C++ engine fires parallel ICMP probes across all TTLs
3. **Explore the results:**
   - **Left Panel** — Route summary: target IP, hop count, countries traversed, ISP, cloud provider
   - **Center** — Interactive latency chart (click any point to inspect that hop)
   - **Right Panel** — Health score with penalty breakdown, connection profiling, and statistics
   - **Bottom** — Visual hop timeline showing city names and per-hop latency
4. **Switch tabs** — Toggle between Diagnostics, Diagnosis (root cause analysis), and Hop Details
5. **Export** — Save the full trace as a structured JSON file

---

## 🧪 Testing

```bash
# Run the Python test suite
pytest tests/ -v

# Run C++ engine tests (after building)
cd engine/build
ctest --output-on-failure
```

## 👤 Author

**Mohd Mursaleen**

---

## 📄 License

This project is licensed under the MIT License.
