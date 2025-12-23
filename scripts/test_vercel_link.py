#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.services.vercel_service import get_latest_deployment_url


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/test_vercel_link.py <branch>")
        return 1
    branch = sys.argv[1]
    settings = get_settings()
    project = settings.vercel_project_map.get("youdy-front", "")
    if not project:
        print("No Vercel project configured for youdy-front.")
        return 1
    url = get_latest_deployment_url(project, branch)
    if not url:
        print("No deployment URL found.")
        return 1
    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
