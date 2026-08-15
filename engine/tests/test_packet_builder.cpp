#include <gtest/gtest.h>
#include "netscope/packet_builder.hpp"
#include <arpa/inet.h>

using namespace netscope;

TEST(PacketBuilderTest, PacketSize) {
    PacketBuilder builder;
    auto packet = builder.build_echo_request(1234, 1);
    // 8 bytes header + 56 bytes payload = 64 bytes
    EXPECT_EQ(packet.size(), 64u);
}

TEST(PacketBuilderTest, ICMPType) {
    PacketBuilder builder;
    auto packet = builder.build_echo_request(1234, 1);
    auto* header = reinterpret_cast<const ICMPHeader*>(packet.data());
    EXPECT_EQ(header->type, 8);  // Echo Request
    EXPECT_EQ(header->code, 0);
}

TEST(PacketBuilderTest, IDAndSequence) {
    PacketBuilder builder;
    auto packet = builder.build_echo_request(0xABCD, 42);
    auto* header = reinterpret_cast<const ICMPHeader*>(packet.data());
    EXPECT_EQ(ntohs(header->id), 0xABCD);
    EXPECT_EQ(ntohs(header->sequence), 42);
}

TEST(PacketBuilderTest, ChecksumNonZero) {
    PacketBuilder builder;
    auto packet = builder.build_echo_request(1234, 1);
    auto* header = reinterpret_cast<const ICMPHeader*>(packet.data());
    EXPECT_NE(header->checksum, 0);
}

TEST(PacketBuilderTest, ChecksumVerification) {
    // If we compute the checksum over the entire packet (including the
    // stored checksum), the result should be 0 (or 0xFFFF in one's complement)
    PacketBuilder builder;
    auto packet = builder.build_echo_request(1234, 1);
    uint16_t verify = PacketBuilder::compute_checksum(packet.data(), packet.size());
    // After checksumming a packet that already has a valid checksum,
    // the result should be 0 (all bits cancel out)
    EXPECT_EQ(verify, 0);
}

TEST(PacketBuilderTest, DifferentSequencesProduceDifferentChecksums) {
    PacketBuilder builder;
    auto pkt1 = builder.build_echo_request(1234, 1);
    auto pkt2 = builder.build_echo_request(1234, 2);
    auto* h1 = reinterpret_cast<const ICMPHeader*>(pkt1.data());
    auto* h2 = reinterpret_cast<const ICMPHeader*>(pkt2.data());
    EXPECT_NE(h1->checksum, h2->checksum);
}

TEST(PacketBuilderTest, PayloadPattern) {
    PacketBuilder builder;
    auto packet = builder.build_echo_request(1234, 1);
    // Payload starts at offset 8 (after header)
    // Should be 0, 1, 2, 3, ... pattern
    for (size_t i = 0; i < 56; i++) {
        EXPECT_EQ(packet[8 + i], static_cast<uint8_t>(i & 0xFF));
    }
}
