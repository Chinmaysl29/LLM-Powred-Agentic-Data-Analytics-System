"""Automated Rollback CLI Utility for Production Incidents.

Usage:
    python scripts/rollback.py --target v1.0.0 --reason "Health check latency regression"
"""

import argparse
import json
import sys
from backend.deployment.deployment_automator import deployment_automator


def main() -> None:
    parser = argparse.ArgumentParser(description="Rollback AI Data Analyst OS deployment.")
    parser.add_argument("--failed", default="v-current-unhealthy", help="Failed version to dismantle")
    parser.add_argument("--target", default="v1.0.0", help="Stable release version tag to restore")
    parser.add_argument("--reason", default="Manual emergency rollback triggered", help="Reason for rollback")
    args = parser.parse_args()

    print(f"[*] Rolling back from {args.failed} to {args.target}...")
    res = deployment_automator.rollback_deployment(
        failed_version=args.failed,
        previous_version=args.target,
        reason=args.reason,
    )
    print(json.dumps(res, indent=2))
    print("[+] Rollback completed. System state restored.")


if __name__ == "__main__":
    main()
