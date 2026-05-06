"""Launch Phase 6 Modal GPU LoRA training scaffold."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    prep_cmd = [sys.executable, "scripts/build_phase6_dataset.py"]
    prep = subprocess.run(prep_cmd, cwd=PROJECT_ROOT)
    if prep.returncode != 0:
        raise SystemExit(prep.returncode)

    train_cmd = [sys.executable, "scripts/modal_gpu_check.py"]
    train = subprocess.run(train_cmd, cwd=PROJECT_ROOT)
    if train.returncode != 0:
        raise SystemExit(train.returncode)


if __name__ == "__main__":
    main()
