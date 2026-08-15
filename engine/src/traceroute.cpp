#include "netscope/traceroute.hpp"
#include "netscope/packet_builder.hpp"
#include "netscope/platform.hpp"

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <regex>
#include <sstream>
#include <stdexcept>

namespace netscope {

TracerouteEngine::TracerouteEngine(const TraceConfig& config)
    : config_(config) {}

TracerouteEngine::~TracerouteEngine() = default;

void TracerouteEngine::cancel() {
    cancelled_.store(true, std::memory_order_release);
}

bool TracerouteEngine::is_cancelled() const {
    return cancelled_.load(std::memory_order_acquire);
}

void TracerouteEngine::reset() {
    cancelled_.store(false, std::memory_order_release);
}

void TracerouteEngine::compute_stats(HopResult& hop) {
    // Filter out timeout probes (-1.0)
    std::vector<double> valid;
    for (double rtt : hop.rtts) {
        if (rtt >= 0.0) valid.push_back(rtt);
    }

    if (valid.empty()) {
        hop.is_timeout = true;
        hop.avg_rtt = -1.0;
        hop.min_rtt = -1.0;
        hop.max_rtt = -1.0;
    } else {
        hop.is_timeout = false;
        hop.min_rtt = *std::min_element(valid.begin(), valid.end());
        hop.max_rtt = *std::max_element(valid.begin(), valid.end());
        double sum = 0.0;
        for (double v : valid) sum += v;
        hop.avg_rtt = sum / static_cast<double>(valid.size());
    }
}

bool TracerouteEngine::raw_sockets_available() {
#ifdef NETSCOPE_POSIX
    // Try to create a raw ICMP socket
    int sock = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    if (sock >= 0) {
        close(sock);
        return true;
    }
    return false;
#else
    return false;
#endif
}

void TracerouteEngine::trace(const std::string& target_ip,
                              std::function<void(const HopResult&)> on_hop) {
    reset();

    if (raw_sockets_available()) {
        trace_raw_socket(target_ip, on_hop);
    } else {
        trace_fallback(target_ip, on_hop);
    }
}

#ifdef NETSCOPE_POSIX

double TracerouteEngine::send_probe(int sock_send, int sock_recv,
                                     const std::string& target_ip,
                                     int ttl, uint16_t seq,
                                     std::string& reply_ip) {
    // Set TTL on the sending socket
    if (setsockopt(sock_send, IPPROTO_IP, IP_TTL, &ttl, sizeof(ttl)) < 0) {
        return -1.0;
    }

    // Build the destination address
    struct sockaddr_in dest{};
    dest.sin_family = AF_INET;
    inet_pton(AF_INET, target_ip.c_str(), &dest.sin_addr);

    // Build ICMP Echo Request packet
    PacketBuilder builder;
    uint16_t id = static_cast<uint16_t>(getpid() & 0xFFFF);
    auto packet = builder.build_echo_request(id, seq);

    // Record the send time
    auto start = Clock::now();

    // Send the packet
    ssize_t sent = sendto(sock_send, packet.data(), packet.size(), 0,
                          reinterpret_cast<struct sockaddr*>(&dest),
                          sizeof(dest));
    if (sent < 0) {
        return -1.0;
    }

    // Wait for a reply using poll() with timeout
    struct pollfd pfd{};
    pfd.fd = sock_recv;
    pfd.events = POLLIN;

    int ret = poll(&pfd, 1, config_.timeout_ms);
    if (ret <= 0) {
        // Timeout or error
        return -1.0;
    }

    // Read the reply
    uint8_t recv_buf[512];
    struct sockaddr_in from{};
    socklen_t from_len = sizeof(from);

    ssize_t received = recvfrom(sock_recv, recv_buf, sizeof(recv_buf), 0,
                                 reinterpret_cast<struct sockaddr*>(&from),
                                 &from_len);
    if (received < 0) {
        return -1.0;
    }

    auto end = Clock::now();

    // The reply includes the IP header (20 bytes) followed by ICMP header
    // Check the ICMP type to determine what kind of reply we got
    if (received < 28) {  // 20 (IP) + 8 (ICMP) minimum
        return -1.0;
    }

    // Skip IP header (usually 20 bytes, but check IHL field)
    int ip_header_len = (recv_buf[0] & 0x0F) * 4;
    uint8_t icmp_type = recv_buf[ip_header_len];

    // Extract the responding router's IP address
    char ip_str[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &from.sin_addr, ip_str, sizeof(ip_str));
    reply_ip = ip_str;

    // ICMP Type 11 = Time Exceeded (intermediate router)
    // ICMP Type 0  = Echo Reply (destination reached)
    if (icmp_type == 11 || icmp_type == 0) {
        double rtt = to_ms(end - start);
        return rtt;
    }

    return -1.0;
}

void TracerouteEngine::trace_raw_socket(const std::string& target_ip,
                                         std::function<void(const HopResult&)> on_hop) {
    // Create raw ICMP socket for sending
    int sock_send = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    if (sock_send < 0) {
        throw std::runtime_error("Failed to create raw socket (need CAP_NET_RAW or root)");
    }

    // We use the same socket for receiving ICMP replies
    int sock_recv = sock_send;

    uint16_t seq = 0;

    for (int ttl = 1; ttl <= config_.max_hops; ttl++) {
        if (is_cancelled()) break;

        HopResult hop;
        hop.hop_number = ttl;
        std::string last_ip;

        // Send multiple probes per hop for min/avg/max statistics
        for (int probe = 0; probe < config_.probes_per_hop; probe++) {
            if (is_cancelled()) break;

            std::string reply_ip;
            double rtt = send_probe(sock_send, sock_recv, target_ip,
                                    ttl, seq++, reply_ip);
            hop.rtts.push_back(rtt);

            if (rtt >= 0.0 && !reply_ip.empty()) {
                last_ip = reply_ip;
            }
        }

        hop.ip = last_ip;

        // Try reverse DNS lookup for hostname
        if (!hop.ip.empty() && config_.resolve_hostnames) {
            struct sockaddr_in sa{};
            sa.sin_family = AF_INET;
            inet_pton(AF_INET, hop.ip.c_str(), &sa.sin_addr);
            char host[NI_MAXHOST];
            if (getnameinfo(reinterpret_cast<struct sockaddr*>(&sa), sizeof(sa),
                           host, sizeof(host), nullptr, 0, NI_NAMEREQD) == 0) {
                hop.hostname = host;
            }
        }

        // Compute min/avg/max from the probe RTTs
        compute_stats(hop);

        // Check if we've reached the destination
        if (hop.ip == target_ip) {
            hop.is_destination = true;
        }

        // Report this hop
        on_hop(hop);

        // If we reached the destination, we're done
        if (hop.is_destination) break;
    }

    close(sock_send);
}

#else
// Windows stub — raw socket tracing not implemented for Windows
void TracerouteEngine::trace_raw_socket(const std::string&,
                                         std::function<void(const HopResult&)>) {
    throw std::runtime_error("Raw socket traceroute not implemented on this platform");
}

double TracerouteEngine::send_probe(int, int, const std::string&, int, uint16_t, std::string&) {
    return -1.0;
}
#endif

void TracerouteEngine::trace_fallback(const std::string& target_ip,
                                       std::function<void(const HopResult&)> on_hop) {
    // Spawn the system traceroute command and parse its output
    std::string cmd;
#ifdef NETSCOPE_POSIX
    cmd = "traceroute -n -q " + std::to_string(config_.probes_per_hop) +
          " -m " + std::to_string(config_.max_hops) +
          " -w " + std::to_string(config_.timeout_ms / 1000) +
          " " + target_ip + " 2>&1";
#else
    cmd = "tracert -d -h " + std::to_string(config_.max_hops) +
          " -w " + std::to_string(config_.timeout_ms) +
          " " + target_ip;
#endif

    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        throw std::runtime_error("Failed to run traceroute command");
    }

    char line[512];

    // Linux traceroute -n output format:
    //  1  192.168.1.1  1.234 ms  1.567 ms  1.890 ms
    //  2  * * *
    //  3  72.14.236.73  18.234 ms  17.891 ms  19.123 ms
    std::regex hop_regex(R"(^\s*(\d+)\s+(.+)$)");
    std::regex rtt_regex(R"(([\d.]+)\s*ms)");
    std::regex ip_regex(R"((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}))");

    while (fgets(line, sizeof(line), pipe) && !is_cancelled()) {
        std::string line_str(line);
        std::smatch match;

        if (std::regex_match(line_str, match, hop_regex)) {
            HopResult hop;
            hop.hop_number = std::stoi(match[1].str());
            std::string rest = match[2].str();

            // Extract IP address
            std::smatch ip_match;
            if (std::regex_search(rest, ip_match, ip_regex)) {
                hop.ip = ip_match[1].str();
            }

            // Extract all RTT values
            auto rtt_begin = std::sregex_iterator(rest.begin(), rest.end(), rtt_regex);
            auto rtt_end = std::sregex_iterator();
            for (auto it = rtt_begin; it != rtt_end; ++it) {
                hop.rtts.push_back(std::stod((*it)[1].str()));
            }

            // If no RTTs found but we have *, it's a timeout
            if (hop.rtts.empty()) {
                for (int i = 0; i < config_.probes_per_hop; i++) {
                    hop.rtts.push_back(-1.0);
                }
            }

            compute_stats(hop);
            hop.is_destination = (hop.ip == target_ip);

            on_hop(hop);

            if (hop.is_destination) break;
        }
    }

    pclose(pipe);
}

}  // namespace netscope
