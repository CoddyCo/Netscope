#pragma once
// ^ This tells the compiler: "Only include this file once, even if
//   multiple files try to include it." Without this, you get duplicate
//   definition errors.

#include <atomic>
#include <functional>
#include <optional>
#include <string>
#include <vector>


namespace netscope {
// Everything lives inside the 'netscope' namespace so our names
// (like 'HopResult') don't clash with anyone else's code.

// ── Configuration ──────────────────────────────────────────────
// This is what the user can tweak before running a trace.
// Think of it as the "settings" panel.
struct TraceConfig {
  int max_hops = 30;      // Stop after 30 routers (most traces finish in 15-20)
  int timeout_ms = 3000;  // Wait 3 seconds for each router to respond
  int probes_per_hop = 3; // Send 3 packets per hop (for min/avg/max RTT)
  bool resolve_hostnames = true; // Try to find hostnames for each IP
};

// ── Hop Result ─────────────────────────────────────────────────
// This is what we learn about ONE router along the path.
// If the trace has 13 hops, we'll have 13 of these.
struct HopResult {
  int hop_number = 0;   // Which hop is this? (1, 2, 3, ...)
  std::string ip;       // The router's IP address (e.g., "72.14.236.73")
  std::string hostname; // The router's name (e.g., "ae12.mumbai.google.com")

  std::vector<double>
      rtts; // Round-Trip Times in milliseconds
            // We send 3 probes, so this might be [17.2, 18.4, 19.8]
            // A value of -1.0 means that probe timed out

  double avg_rtt = 0.0; // Average of the successful RTTs
  double min_rtt = 0.0; // Fastest probe
  double max_rtt = 0.0; // Slowest probe

  bool is_timeout = false;     // True if ALL probes timed out (* * *)
  bool is_destination = false; // True if this hop IS the final destination
};

// ── Cloud Info ─────────────────────────────────────────────────
// When we identify that an IP belongs to a cloud provider,
// this struct holds that information.
struct CloudInfo {
  std::string provider; // "AWS", "Google Cloud", "Cloudflare"
  std::string region;   // "ap-south-1", "us-east-1", "asia-south1"
  std::string service;  // "EC2", "CloudFront", "CDN"
};

} // namespace netscope
