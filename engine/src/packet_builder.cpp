#include "netscope/packet_builder.hpp"
#include <arpa/inet.h>
#include <cstring>

namespace netscope {

std::vector<uint8_t> PacketBuilder::build_echo_request(uint16_t id, uint16_t seq) {
    // ICMP Echo Request: 8 bytes header + 56 bytes payload = 64 bytes total
    // This matches the standard ping packet size
    const size_t payload_size = 56;
    const size_t total_size = sizeof(ICMPHeader) + payload_size;

    std::vector<uint8_t> packet(total_size, 0);

    // Overlay the ICMP header struct onto the raw byte buffer
    auto* header = reinterpret_cast<ICMPHeader*>(packet.data());

    header->type     = 8;           // Echo Request
    header->code     = 0;           // No sub-type
    header->checksum = 0;           // Must be 0 before checksum computation
    header->id       = htons(id);   // Convert to network byte order (big-endian)
    header->sequence = htons(seq);  // Convert to network byte order

    // Fill payload with a recognizable pattern for debugging
    // If you capture this packet in Wireshark, you'll see 0x00, 0x01, 0x02, ...
    for (size_t i = 0; i < payload_size; i++) {
        packet[sizeof(ICMPHeader) + i] = static_cast<uint8_t>(i & 0xFF);
    }

    // Compute checksum over the entire packet (header + payload)
    header->checksum = compute_checksum(packet.data(), packet.size());

    return packet;
}

uint16_t PacketBuilder::compute_checksum(const void* data, size_t len) {
    // RFC 1071: Internet Checksum algorithm
    // 1. Sum all 16-bit words
    // 2. Fold any carry bits back into the 16-bit sum
    // 3. Take the one's complement (bitwise NOT)

    const auto* words = reinterpret_cast<const uint16_t*>(data);
    uint32_t sum = 0;

    // Sum 16-bit words
    while (len > 1) {
        sum += *words++;
        len -= 2;
    }

    // Handle odd byte at the end
    if (len == 1) {
        uint16_t last = 0;
        std::memcpy(&last, words, 1);
        sum += last;
    }

    // Fold 32-bit sum to 16 bits: add carry to lower 16
    while (sum >> 16) {
        sum = (sum & 0xFFFF) + (sum >> 16);
    }

    // One's complement
    return static_cast<uint16_t>(~sum);
}

}  // namespace netscope
