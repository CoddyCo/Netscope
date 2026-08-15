"""
NetScope CLI Entry Point
"""

import argparse
import sys

from netscope.app import NetScopeApp


def main():
    parser = argparse.ArgumentParser(description="NetScope — Network Intelligence")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode with recorded traces")
    args = parser.parse_args()

    app = NetScopeApp(demo_mode=args.demo)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
