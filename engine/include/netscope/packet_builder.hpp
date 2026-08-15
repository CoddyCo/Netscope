#pragma once

#include <cstdint>
#include <vector>

namespace netscope {

// The ICMP header structure — exactly 8 bytes.
// We use #pragma pack(push, 1) to tell the compiler:
// "Do NOT add any padding bytes between these fields."
// Without this, the compiler might insert gaps for alignment,
// and our packet would be the wrong size.
#pragma pack(push, 1)
struct ICMPHeader {
    uint8_t  type;        // 8 = Echo Request, 0 = Echo Reply
    uint8_t  code;        // Always 0 for echo
    uint16_t checksum;    // RFC 1071 checksum
    uint16_t id;          // Identifier (we use process ID)
    uint16_t sequence;    // Sequence number (we use hop number)
};
#pragma pack(pop)

class PacketBuilder {
public:
    // Build a complete ICMP Echo Request packet.
    // Returns the raw bytes ready to be sent over a socket.
    //
    // id:  A unique identifier for our traceroute session
    //      (so we can tell our packets apart from other programs' packets)
    // seq: The sequence number (we'll set this to the current hop's TTL)
    std::vector<uint8_t> build_echo_request(uint16_t id, uint16_t seq);

    // Compute the RFC 1071 Internet Checksum.
    // This is a STATIC method because it's a pure mathematical function —
    // it doesn't need any object state.
    //
    // data: pointer to the raw bytes
    // len:  how many bytes to checksum
    static uint16_t compute_checksum(const void* data, size_t len);
};

}  // namespace netscope
