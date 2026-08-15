import pytest
from netscope.core.models import GeoInfo, NetworkInfo, CloudInfo, Hop

def test_hop_dataclass():
    geo = GeoInfo(country="United States", country_code="US", city="Seattle", latitude=47.6, longitude=-122.3)
    net = NetworkInfo(asn=15169, isp="Google LLC", org="Google LLC")
    cloud = CloudInfo(provider="GCP", region="us-west1", service="")
    
    hop = Hop(
        hop_number=5,
        ip="8.8.8.8",
        hostname="dns.google",
        rtts=[10.0, 10.1, 9.9],
        avg_rtt=10.0,
        min_rtt=9.9,
        max_rtt=10.1,
        is_timeout=False,
        is_destination=True,
        packet_loss=0.0,
        geo=geo,
        network=net,
        cloud=cloud
    )
    
    assert hop.ip == "8.8.8.8"
    assert hop.geo.country_code == "US"
    assert hop.network.asn == 15169
    assert hop.cloud.provider == "GCP"
    
def test_hop_serialization():
    hop = Hop(
        hop_number=1,
        ip="1.1.1.1",
        hostname="one.one.one.one",
        rtts=[1.0, 1.2, 1.1],
        avg_rtt=1.1,
        min_rtt=1.0,
        max_rtt=1.2,
        is_timeout=False,
        is_destination=False,
        geo=GeoInfo(country_code="US"),
    )
    
    hop_dict = hop.to_dict()
    assert hop_dict["ip"] == "1.1.1.1"
    assert hop_dict["geo"]["country_code"] == "US"
    
    restored = Hop.from_dict(hop_dict)
    assert restored.ip == "1.1.1.1"
    assert restored.geo.country_code == "US"
