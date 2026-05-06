"""Fetch and cache current/historical/Mapbox imagery for a site (Phase 2)."""

import argparse
import json
from pathlib import Path

from apps.api.runtime import get_imagery_service, get_repository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-id", required=True, help="Registered site_id")
    parser.add_argument("--force-refresh", action="store_true", help="Bypass cache and fetch live/mock source")
    parser.add_argument("--out", default="", help="Optional output JSON path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo = get_repository()
    site = repo.get_site(args.site_id)
    if not site:
        raise SystemExit(f"site not found: {args.site_id}")

    assets, mode = get_imagery_service().fetch_site_bundle(site=site, force_refresh=args.force_refresh)
    for asset in assets.values():
        repo.save_image_asset(asset)

    payload = {
        "site_id": args.site_id,
        "mode": mode,
        "assets": {
            key: {
                "asset_id": value.asset_id,
                "source": value.source,
                "path": value.local_path,
                "cloud_cover": value.cloud_cover,
                "captured_at": value.timestamp_captured.isoformat(),
            }
            for key, value in assets.items()
        },
    }

    rendered = json.dumps(payload, indent=2)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
