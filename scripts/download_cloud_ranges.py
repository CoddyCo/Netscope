#!/usr/bin/env python3
"""
Download Cloud IP Ranges

Fetches public IP range data from major cloud providers
and saves them to the data/cloud-ranges directory.
"""

import json
import os
import urllib.request
from pathlib import Path

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data" / "cloud-ranges"

# Sources
SOURCES = {
    "aws.json": "https://ip-ranges.amazonaws.com/ip-ranges.json",
    "gcp.json": "https://www.gstatic.com/ipranges/cloud.json",
    "cloudflare.json": "https://api.cloudflare.com/client/v4/ips",
    "azure.json": "https://download.microsoft.com/download/7/1/D/71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public_20231016.json", # Azure is trickier, link changes often
}

def main():
    print(f"Ensuring directory exists: {DATA_DIR}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for filename, url in SOURCES.items():
        out_path = DATA_DIR / filename
        print(f"Downloading {filename}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NetScope/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                
                # Cloudflare has a specific nested format, we unpack it
                if filename == "cloudflare.json":
                    cf_data = json.loads(data.decode("utf-8"))
                    if cf_data.get("success"):
                        # Extract ipv4 and ipv6 prefixes
                        ipv4 = cf_data["result"]["ipv4_cidrs"]
                        
                        # Create a unified format that our CloudDetector Python fallback understands easily
                        standardized = {
                            "prefixes": [{"ip_prefix": ip, "region": "global"} for ip in ipv4]
                        }
                        with open(out_path, "w") as f:
                            json.dump(standardized, f)
                        print(f"  Saved Cloudflare ranges to {out_path}")
                        continue
                
                with open(out_path, "wb") as f:
                    f.write(data)
                print(f"  Saved to {out_path}")
        except Exception as e:
            print(f"  Failed to download {filename}: {e}")

if __name__ == "__main__":
    main()
