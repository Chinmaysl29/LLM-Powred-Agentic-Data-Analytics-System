"""One-Click Deployment Script for CLI & CI/CD Pipelines.

Usage:
    python scripts/deploy.py --version v1.0.1
"""

import argparse
import json
import sys
from backend.deployment.deployment_automator import deployment_automator


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy AI Data Analyst OS to production.")
    parser.add_argument("--version", default="v1.0.0", help="Target release version tag")
    args = parser.parse_args()

    print(f"[*] Initiating automated deployment for version: {args.version}")
    report = deployment_automator.execute_deployment(target_version=args.version)
    print(json.dumps(report, indent=2))

    if not report["system_online"]:
        print(f"[!] Deployment failed! System status: {report['status']}")
        sys.exit(1)

    print(f"[+] Deployment complete! System is ONLINE at version {report['active_version']}.")


if __name__ == "__main__":
    main()
