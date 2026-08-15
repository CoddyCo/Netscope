import pytest
from netscope.utils.validators import is_valid_domain, is_valid_ip, is_private_ip, sanitize_input

def test_is_valid_domain():
    assert is_valid_domain("google.com")
    assert is_valid_domain("www.google.com")
    assert not is_valid_domain("google")
    assert not is_valid_domain("http://google.com")

def test_is_valid_ip():
    assert is_valid_ip("8.8.8.8")
    assert is_valid_ip("192.168.1.1")
    assert not is_valid_ip("256.256.256.256")
    assert not is_valid_ip("google.com")

def test_is_private_ip():
    assert is_private_ip("192.168.1.1")
    assert is_private_ip("10.0.0.1")
    assert is_private_ip("172.16.0.1")
    assert not is_private_ip("8.8.8.8")

def test_sanitize_input():
    assert sanitize_input("http://google.com") == "google.com"
    assert sanitize_input("https://google.com/path") == "google.com"
    assert sanitize_input("google.com:443") == "google.com"
    assert sanitize_input("  google.com  ") == "google.com"
