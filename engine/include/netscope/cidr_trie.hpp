#pragma once

#include <string>
#include <optional>
#include <memory>
#include <vector>
#include "netscope/types.hpp"

namespace netscope {

// Binary trie for longest-prefix matching of CIDR blocks.
// Each IP is treated as a 32-bit binary string. We walk bit-by-bit
// from MSB to LSB, following children[0] or children[1].
// When a node has CloudInfo, it means "all IPs matching this prefix
// belong to this provider."
class CIDRTrie {
public:
    CIDRTrie();
    ~CIDRTrie();

    // Insert a CIDR block (e.g., "104.16.0.0/12") with its provider info
    void insert(const std::string& cidr, const std::string& provider,
                const std::string& region = "", const std::string& service = "");

    // Lookup an IP address — returns the most specific (longest prefix) match
    std::optional<CloudInfo> lookup(const std::string& ip) const;

    // Load cloud IP ranges from a JSON file
    // Supports AWS, GCP, Azure, and Cloudflare formats
    void load_from_json(const std::string& filepath, const std::string& provider);

    // Number of prefixes stored
    size_t size() const;

    // Clear all entries
    void clear();

private:
    struct TrieNode {
        std::unique_ptr<TrieNode> children[2];  // 0-bit child and 1-bit child
        std::optional<CloudInfo> info;           // Set if this node terminates a prefix
    };

    std::unique_ptr<TrieNode> root_;
    size_t prefix_count_ = 0;

    // Convert dotted-decimal IP string to a 32-bit unsigned integer
    // "104.20.34.165" → 0x68142AA5
    static uint32_t ip_to_uint32(const std::string& ip);

    // Parse CIDR notation into IP and prefix length
    // "104.16.0.0/12" → (ip=0x68100000, prefix_len=12)
    static std::pair<uint32_t, int> parse_cidr(const std::string& cidr);
};

}  // namespace netscope
