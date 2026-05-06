from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SIMSAT_SIM_DIR = PROJECT_ROOT / "external" / "SimSat" / "src" / "sim"


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)).strip())
    except Exception:
        return float(default)


def _ensure_mapbox_token() -> None:
    token = os.getenv("MAPBOX_ACCESS_TOKEN", "").strip()
    if not token:
        fallback = os.getenv("MAPBOX_TOKEN", "").strip()
        if fallback:
            os.environ["MAPBOX_ACCESS_TOKEN"] = fallback
            token = fallback
    if not token:
        raise RuntimeError("Missing MAPBOX_ACCESS_TOKEN (or MAPBOX_TOKEN) for SimSat Mapbox endpoint.")


def _tick_timestamp(shared_data: dict, interval_seconds: float) -> None:
    while True:
        shared_data["last_updated"] = _iso_now()
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SimSat API (source mode) on localhost.")
    parser.add_argument("--host", default=os.getenv("SIMSAT_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("SIMSAT_PORT", "9005")))
    parser.add_argument("--env-file", default=str(PROJECT_ROOT / ".env.local"))
    parser.add_argument("--lon", type=float, default=_env_float("SIMSAT_BOOT_LON", 6.6322734))
    parser.add_argument("--lat", type=float, default=_env_float("SIMSAT_BOOT_LAT", 46.5218266))
    parser.add_argument("--alt-km", type=float, default=_env_float("SIMSAT_BOOT_ALT_KM", 800.0))
    parser.add_argument("--tick-seconds", type=float, default=_env_float("SIMSAT_BOOT_TICK_SECONDS", 1.0))
    args = parser.parse_args()

    _load_env_file(Path(args.env_file))
    _ensure_mapbox_token()

    if not SIMSAT_SIM_DIR.exists():
        raise RuntimeError(f"SimSat source path not found: {SIMSAT_SIM_DIR}")

    sys.path.insert(0, str(SIMSAT_SIM_DIR))
    from api import api as simsat_api  # type: ignore

    shared_data = {
        "satellite_position": (args.lon, args.lat, args.alt_km),
        "last_updated": _iso_now(),
    }
    simsat_api.state.shared_data = shared_data

    ticker = threading.Thread(
        target=_tick_timestamp,
        args=(shared_data, max(0.2, args.tick_seconds)),
        daemon=True,
    )
    ticker.start()

    print(
        f"SimSat API bootstrap started on {args.host}:{args.port} "
        f"with static satellite_position=({args.lon}, {args.lat}, {args.alt_km})."
    )
    uvicorn.run(simsat_api, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
