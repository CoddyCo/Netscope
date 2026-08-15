#include <gtest/gtest.h>
#include "netscope/cidr_trie.hpp"

using namespace netscope;

TEST(CIDRTrieTest, InsertAndLookup) {
    CIDRTrie trie;
    trie.insert("104.16.0.0/12", "Cloudflare", "", "CDN");

    auto result = trie.lookup("104.20.34.165");
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->provider, "Cloudflare");
    EXPECT_EQ(result->service, "CDN");
}

TEST(CIDRTrieTest, NoMatch) {
    CIDRTrie trie;
    trie.insert("104.16.0.0/12", "Cloudflare");

    auto result = trie.lookup("8.8.8.8");
    EXPECT_FALSE(result.has_value());
}

TEST(CIDRTrieTest, LongestPrefixMatch) {
    CIDRTrie trie;
    // Broad AWS range
    trie.insert("13.0.0.0/8", "AWS", "global");
    // More specific AWS region
    trie.insert("13.232.0.0/14", "AWS", "ap-south-1", "EC2");

    // IP in the more specific range should match ap-south-1
    auto result = trie.lookup("13.232.100.50");
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->provider, "AWS");
    EXPECT_EQ(result->region, "ap-south-1");

    // IP outside the specific range but inside /8
    auto result2 = trie.lookup("13.100.0.1");
    ASSERT_TRUE(result2.has_value());
    EXPECT_EQ(result2->region, "global");
}

TEST(CIDRTrieTest, ExactMatch32) {
    CIDRTrie trie;
    trie.insert("8.8.8.8/32", "Google", "", "DNS");

    auto result = trie.lookup("8.8.8.8");
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->provider, "Google");

    // 8.8.8.9 should NOT match
    auto result2 = trie.lookup("8.8.8.9");
    EXPECT_FALSE(result2.has_value());
}

TEST(CIDRTrieTest, MultipleProviders) {
    CIDRTrie trie;
    trie.insert("104.16.0.0/12", "Cloudflare", "", "CDN");
    trie.insert("13.0.0.0/8", "AWS", "global");
    trie.insert("35.190.0.0/17", "Google Cloud", "us-central1");

    auto cf = trie.lookup("104.20.1.1");
    ASSERT_TRUE(cf.has_value());
    EXPECT_EQ(cf->provider, "Cloudflare");

    auto aws = trie.lookup("13.227.1.1");
    ASSERT_TRUE(aws.has_value());
    EXPECT_EQ(aws->provider, "AWS");

    auto gcp = trie.lookup("35.190.50.10");
    ASSERT_TRUE(gcp.has_value());
    EXPECT_EQ(gcp->provider, "Google Cloud");
}

TEST(CIDRTrieTest, Size) {
    CIDRTrie trie;
    EXPECT_EQ(trie.size(), 0u);

    trie.insert("10.0.0.0/8", "Private");
    EXPECT_EQ(trie.size(), 1u);

    trie.insert("172.16.0.0/12", "Private");
    EXPECT_EQ(trie.size(), 2u);
}

TEST(CIDRTrieTest, Clear) {
    CIDRTrie trie;
    trie.insert("10.0.0.0/8", "Private");
    trie.insert("172.16.0.0/12", "Private");
    EXPECT_EQ(trie.size(), 2u);

    trie.clear();
    EXPECT_EQ(trie.size(), 0u);
    EXPECT_FALSE(trie.lookup("10.0.0.1").has_value());
}

TEST(CIDRTrieTest, PrivateRanges) {
    CIDRTrie trie;
    trie.insert("10.0.0.0/8", "Private", "RFC1918");
    trie.insert("172.16.0.0/12", "Private", "RFC1918");
    trie.insert("192.168.0.0/16", "Private", "RFC1918");

    EXPECT_TRUE(trie.lookup("10.0.0.1").has_value());
    EXPECT_TRUE(trie.lookup("172.16.5.1").has_value());
    EXPECT_TRUE(trie.lookup("192.168.1.1").has_value());
    EXPECT_FALSE(trie.lookup("8.8.8.8").has_value());
}

TEST(CIDRTrieTest, InvalidIP) {
    CIDRTrie trie;
    trie.insert("10.0.0.0/8", "Private");

    auto result = trie.lookup("not-an-ip");
    EXPECT_FALSE(result.has_value());
}
