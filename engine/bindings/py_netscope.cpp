#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include "netscope/types.hpp"
#include "netscope/packet_builder.hpp"
#include "netscope/cidr_trie.hpp"
#include "netscope/traceroute.hpp"

namespace py = pybind11;

PYBIND11_MODULE(netscope_core, m) {
    m.doc() = "NetScope C++ core engine — raw socket traceroute and CIDR trie";

    // ── TraceConfig ─────────────────────────────────────────
    py::class_<netscope::TraceConfig>(m, "TraceConfig")
        .def(py::init<>())
        .def_readwrite("max_hops", &netscope::TraceConfig::max_hops)
        .def_readwrite("timeout_ms", &netscope::TraceConfig::timeout_ms)
        .def_readwrite("probes_per_hop", &netscope::TraceConfig::probes_per_hop)
        .def_readwrite("resolve_hostnames", &netscope::TraceConfig::resolve_hostnames);

    // ── HopResult ───────────────────────────────────────────
    py::class_<netscope::HopResult>(m, "HopResult")
        .def(py::init<>())
        .def_readonly("hop_number", &netscope::HopResult::hop_number)
        .def_readonly("ip", &netscope::HopResult::ip)
        .def_readonly("hostname", &netscope::HopResult::hostname)
        .def_readonly("rtts", &netscope::HopResult::rtts)
        .def_readonly("avg_rtt", &netscope::HopResult::avg_rtt)
        .def_readonly("min_rtt", &netscope::HopResult::min_rtt)
        .def_readonly("max_rtt", &netscope::HopResult::max_rtt)
        .def_readonly("is_timeout", &netscope::HopResult::is_timeout)
        .def_readonly("is_destination", &netscope::HopResult::is_destination)
        .def("__repr__", [](const netscope::HopResult& h) {
            return "<HopResult hop=" + std::to_string(h.hop_number) +
                   " ip='" + h.ip + "' avg_rtt=" +
                   std::to_string(h.avg_rtt) + "ms>";
        });

    // ── CloudInfo ───────────────────────────────────────────
    py::class_<netscope::CloudInfo>(m, "CloudInfo")
        .def(py::init<>())
        .def_readonly("provider", &netscope::CloudInfo::provider)
        .def_readonly("region", &netscope::CloudInfo::region)
        .def_readonly("service", &netscope::CloudInfo::service)
        .def("__repr__", [](const netscope::CloudInfo& c) {
            return "<CloudInfo provider='" + c.provider +
                   "' region='" + c.region + "'>";
        });

    // ── PacketBuilder ───────────────────────────────────────
    py::class_<netscope::PacketBuilder>(m, "PacketBuilder")
        .def(py::init<>())
        .def("build_echo_request", &netscope::PacketBuilder::build_echo_request,
             py::arg("id"), py::arg("seq"),
             "Build an ICMP Echo Request packet")
        .def_static("compute_checksum",
            [](py::bytes data) {
                std::string s = data;
                return netscope::PacketBuilder::compute_checksum(s.data(), s.size());
            },
            py::arg("data"),
            "Compute RFC 1071 Internet Checksum");

    // ── CIDRTrie ────────────────────────────────────────────
    py::class_<netscope::CIDRTrie>(m, "CIDRTrie")
        .def(py::init<>())
        .def("insert", &netscope::CIDRTrie::insert,
             py::arg("cidr"), py::arg("provider"),
             py::arg("region") = "", py::arg("service") = "",
             "Insert a CIDR block with provider info")
        .def("lookup", &netscope::CIDRTrie::lookup,
             py::arg("ip"),
             "Lookup an IP — returns CloudInfo or None")
        .def("load_from_json", &netscope::CIDRTrie::load_from_json,
             py::arg("filepath"), py::arg("provider"),
             "Load cloud IP ranges from a JSON file")
        .def("size", &netscope::CIDRTrie::size,
             "Number of prefixes stored")
        .def("clear", &netscope::CIDRTrie::clear);

    // ── TracerouteEngine ────────────────────────────────────
    py::class_<netscope::TracerouteEngine>(m, "TracerouteEngine")
        .def(py::init<const netscope::TraceConfig&>(),
             py::arg("config") = netscope::TraceConfig{})
        .def("trace",
            [](netscope::TracerouteEngine& self,
               const std::string& target_ip,
               py::function on_hop) {
                // Release the GIL while the C++ engine is running
                // so the Python GUI thread stays responsive.
                // Re-acquire GIL only when calling the Python callback.
                py::gil_scoped_release release;
                self.trace(target_ip, [&on_hop](const netscope::HopResult& hop) {
                    py::gil_scoped_acquire acquire;
                    on_hop(hop);
                });
            },
            py::arg("target_ip"), py::arg("on_hop"),
            "Run traceroute — calls on_hop(HopResult) for each hop")
        .def("cancel", &netscope::TracerouteEngine::cancel,
             "Cancel a running trace")
        .def("is_cancelled", &netscope::TracerouteEngine::is_cancelled)
        .def("reset", &netscope::TracerouteEngine::reset);
}
