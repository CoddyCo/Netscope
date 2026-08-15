#pragma once

#include <string>
#include <functional>
#include <atomic>
#include "netscope/types.hpp"

namespace netscope {

// The traceroute engine sends ICMP Echo Request packets with
// incrementing TTL values. Each router that decrements TTL to 0
// sends back an ICMP Time Exceeded reply, revealing its IP address.
//
// On Linux/WSL: uses raw ICMP sockets (SOCK_RAW, IPPROTO_ICMP)
// Fallback: spawns /usr/bin/traceroute and parses output
class TracerouteEngine {
public:
    explicit TracerouteEngine(const TraceConfig& config = TraceConfig{});
    ~TracerouteEngine();

    // Run a traceroute to the target IP address.
    // Calls on_hop for each discovered hop (streaming results).
    // Blocks until trace completes or is cancelled.
    void trace(const std::string& target_ip,
               std::function<void(const HopResult&)> on_hop);

    // Cancel a running trace (thread-safe)
    void cancel();

    // Check if a trace was cancelled
    bool is_cancelled() const;

    // Reset cancel state for reuse
    void reset();

private:
    TraceConfig config_;
    std::atomic<bool> cancelled_{false};

    // Primary: raw socket ICMP traceroute
    void trace_raw_socket(const std::string& target_ip,
                          std::function<void(const HopResult&)> on_hop);

    // Fallback: parse output of /usr/bin/traceroute
    void trace_fallback(const std::string& target_ip,
                        std::function<void(const HopResult&)> on_hop);

    // Send a single probe and wait for reply
    // Returns RTT in ms, or -1.0 on timeout
    double send_probe(int sock_send, int sock_recv,
                      const std::string& target_ip,
                      int ttl, uint16_t seq,
                      std::string& reply_ip);

    // Compute statistics from a vector of RTTs
    static void compute_stats(HopResult& hop);

    // Check if raw sockets are available (need CAP_NET_RAW or root)
    static bool raw_sockets_available();
};

}  // namespace netscope
