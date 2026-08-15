#pragma once

// Platform detection macros for cross-platform raw socket support

#if defined(__linux__) || defined(__APPLE__)
    #define NETSCOPE_POSIX 1
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <netinet/ip_icmp.h>
    #include <arpa/inet.h>
    #include <netdb.h>
    #include <unistd.h>
    #include <poll.h>
    #include <cerrno>
    #include <cstring>
#elif defined(_WIN32)
    #define NETSCOPE_WINDOWS 1
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <iphlpapi.h>
    #include <icmpapi.h>
    #pragma comment(lib, "ws2_32.lib")
    #pragma comment(lib, "iphlpapi.lib")
#else
    #error "Unsupported platform"
#endif

#include <chrono>

namespace netscope {

// High-resolution clock alias for precise RTT measurement
using Clock = std::chrono::high_resolution_clock;
using TimePoint = Clock::time_point;

// Convert a duration to milliseconds as a double
inline double to_ms(const std::chrono::nanoseconds& ns) {
    return std::chrono::duration<double, std::milli>(ns).count();
}

}  // namespace netscope
