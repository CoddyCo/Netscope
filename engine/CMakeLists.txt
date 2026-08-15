# ── NetScope C++ Core Engine ──────────────────────────────────
# Builds the netscope_core Python extension module via pybind11
cmake_minimum_required(VERSION 3.20)
project(netscope_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)


# Find pybind11 — installed via pip install pybind11
find_package(pybind11 QUIET)
if(NOT pybind11_FOUND)
    # Fallback: use pybind11 from pip
    execute_process(
        COMMAND python3 -m pybind11 --cmakedir
        OUTPUT_VARIABLE pybind11_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    find_package(pybind11 REQUIRED)
endif()

# Find nlohmann/json for parsing cloud IP ranges
# We'll use a header-only approach — download it if not found
include(FetchContent)
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)
FetchContent_MakeAvailable(json)

# ── Core library sources ─────────────────────────────────────
set(ENGINE_SOURCES
    src/packet_builder.cpp
    src/cidr_trie.cpp
    src/traceroute.cpp
)

# ── pybind11 Python module ───────────────────────────────────
pybind11_add_module(netscope_core
    ${ENGINE_SOURCES}
    bindings/py_netscope.cpp
)

target_include_directories(netscope_core PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(netscope_core PRIVATE
    nlohmann_json::nlohmann_json
)

# ── GoogleTest for C++ unit tests ────────────────────────────
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)
FetchContent_MakeAvailable(googletest)

enable_testing()

add_executable(test_packet_builder tests/test_packet_builder.cpp src/packet_builder.cpp)
target_include_directories(test_packet_builder PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(test_packet_builder GTest::gtest_main)

add_executable(test_cidr_trie tests/test_cidr_trie.cpp src/cidr_trie.cpp)
target_include_directories(test_cidr_trie PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(test_cidr_trie GTest::gtest_main nlohmann_json::nlohmann_json)

include(GoogleTest)
gtest_discover_tests(test_packet_builder)
gtest_discover_tests(test_cidr_trie)
