#include "netscope/cidr_trie.hpp"
#include <nlohmann/json.hpp>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <arpa/inet.h>

namespace netscope {

CIDRTrie::CIDRTrie() : root_(std::make_unique<TrieNode>()) {}
CIDRTrie::~CIDRTrie() = default;

uint32_t CIDRTrie::ip_to_uint32(const std::string& ip) {
    // Convert "104.20.34.165" → 32-bit integer
    // Uses inet_pton which handles all valid IPv4 formats
    struct in_addr addr;
    if (inet_pton(AF_INET, ip.c_str(), &addr) != 1) {
        throw std::invalid_argument("Invalid IP address: " + ip);
    }
    // ntohl converts from network byte order (big-endian) to host byte order
    return ntohl(addr.s_addr);
}

std::pair<uint32_t, int> CIDRTrie::parse_cidr(const std::string& cidr) {
    // Parse "104.16.0.0/12" → (ip_uint32, 12)
    auto slash = cidr.find('/');
    if (slash == std::string::npos) {
        // No prefix length — treat as /32 (exact match)
        return {ip_to_uint32(cidr), 32};
    }
    std::string ip_str = cidr.substr(0, slash);
    int prefix_len = std::stoi(cidr.substr(slash + 1));
    if (prefix_len < 0 || prefix_len > 32) {
        throw std::invalid_argument("Invalid prefix length in: " + cidr);
    }
    return {ip_to_uint32(ip_str), prefix_len};
}

void CIDRTrie::insert(const std::string& cidr, const std::string& provider,
                       const std::string& region, const std::string& service) {
    auto [ip, prefix_len] = parse_cidr(cidr);

    // Walk the trie bit-by-bit from MSB (bit 31) to the prefix_length
    TrieNode* node = root_.get();
    for (int i = 31; i >= (32 - prefix_len); i--) {
        int bit = (ip >> i) & 1;  // Extract the i-th bit
        if (!node->children[bit]) {
            node->children[bit] = std::make_unique<TrieNode>();
        }
        node = node->children[bit].get();
    }

    // Store the cloud info at the terminal node of this prefix
    node->info = CloudInfo{provider, region, service};
    prefix_count_++;
}

std::optional<CloudInfo> CIDRTrie::lookup(const std::string& ip) const {
    uint32_t addr;
    try {
        addr = ip_to_uint32(ip);
    } catch (...) {
        return std::nullopt;
    }

    // Walk all 32 bits, tracking the last node with info (longest prefix match)
    const TrieNode* node = root_.get();
    std::optional<CloudInfo> best_match = std::nullopt;

    for (int i = 31; i >= 0; i--) {
        if (!node) break;

        // If this node has info, it's a valid prefix match.
        // We keep walking to find a potentially longer (more specific) match.
        if (node->info.has_value()) {
            best_match = node->info;
        }

        int bit = (addr >> i) & 1;
        node = node->children[bit].get();
    }

    // Check the final node too (for /32 exact matches)
    if (node && node->info.has_value()) {
        best_match = node->info;
    }

    return best_match;
}

void CIDRTrie::load_from_json(const std::string& filepath, const std::string& provider) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filepath);
    }

    nlohmann::json data = nlohmann::json::parse(file);

    if (provider == "aws") {
        // AWS format: { "prefixes": [{ "ip_prefix": "3.5.140.0/22", "region": "ap-northeast-2", "service": "AMAZON" }] }
        if (data.contains("prefixes")) {
            for (const auto& entry : data["prefixes"]) {
                if (entry.contains("ip_prefix")) {
                    std::string cidr = entry["ip_prefix"].get<std::string>();
                    std::string region = entry.value("region", "");
                    std::string service = entry.value("service", "");
                    insert(cidr, "AWS", region, service);
                }
            }
        }
    } else if (provider == "gcp") {
        // GCP format: { "prefixes": [{ "ipv4Prefix": "34.0.0.0/15", "scope": "asia-east1" }] }
        if (data.contains("prefixes")) {
            for (const auto& entry : data["prefixes"]) {
                if (entry.contains("ipv4Prefix")) {
                    std::string cidr = entry["ipv4Prefix"].get<std::string>();
                    std::string scope = entry.value("scope", "");
                    insert(cidr, "Google Cloud", scope, "GCE");
                }
            }
        }
    } else if (provider == "azure") {
        // Azure format: { "values": [{ "properties": { "addressPrefixes": ["13.64.0.0/11"] }, "name": "AzureCloud.westus" }] }
        if (data.contains("values")) {
            for (const auto& entry : data["values"]) {
                std::string name = entry.value("name", "");
                if (entry.contains("properties") && entry["properties"].contains("addressPrefixes")) {
                    for (const auto& prefix : entry["properties"]["addressPrefixes"]) {
                        std::string cidr = prefix.get<std::string>();
                        // Only IPv4
                        if (cidr.find(':') == std::string::npos) {
                            insert(cidr, "Azure", name, "");
                        }
                    }
                }
            }
        }
    } else if (provider == "cloudflare") {
        // Cloudflare format can be an array of strings OR an array of objects
        if (data.contains("prefixes")) {
            for (const auto& entry : data["prefixes"]) {
                if (entry.is_string()) {
                    insert(entry.get<std::string>(), "Cloudflare", "", "CDN");
                } else if (entry.is_object() && entry.contains("ip_prefix")) {
                    insert(entry["ip_prefix"].get<std::string>(), "Cloudflare", entry.value("region", ""), "CDN");
                }
            }
        }
    } else {
        // Generic format: { "prefixes": [{ "cidr": "...", "region": "..." }] }
        if (data.contains("prefixes")) {
            for (const auto& entry : data["prefixes"]) {
                std::string cidr = entry.value("cidr", entry.value("ip_prefix", ""));
                std::string region = entry.value("region", "");
                if (!cidr.empty()) {
                    insert(cidr, provider, region, "");
                }
            }
        }
    }
}

size_t CIDRTrie::size() const {
    return prefix_count_;
}

void CIDRTrie::clear() {
    root_ = std::make_unique<TrieNode>();
    prefix_count_ = 0;
}

}  // namespace netscope
