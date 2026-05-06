import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


class CacheService:
    def __init__(self, cache_root: Path) -> None:
        self.cache_root = cache_root
        self.cache_root.mkdir(parents=True, exist_ok=True)

    def make_cache_key(self, namespace: str, payload: Dict) -> str:
        raw = json.dumps({"namespace": namespace, "payload": payload}, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _asset_path(self, cache_key: str, ext: str = ".bin") -> Path:
        shard = cache_key[:2]
        folder = self.cache_root / shard
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{cache_key}{ext}"

    def _meta_path(self, cache_key: str) -> Path:
        shard = cache_key[:2]
        folder = self.cache_root / shard
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{cache_key}.meta.json"

    def has(self, cache_key: str) -> bool:
        meta = self._meta_path(cache_key)
        if not meta.exists():
            return False
        payload = json.loads(meta.read_text(encoding="utf-8"))
        return Path(payload["path"]).exists()

    def read(self, cache_key: str) -> Optional[Dict]:
        meta = self._meta_path(cache_key)
        if not meta.exists():
            return None
        payload = json.loads(meta.read_text(encoding="utf-8"))
        if not Path(payload["path"]).exists():
            return None
        return payload

    def write(self, cache_key: str, blob: bytes, metadata: Dict, ext: str = ".bin") -> Dict:
        asset_path = self._asset_path(cache_key, ext=ext)
        asset_path.write_bytes(blob)

        meta = dict(metadata)
        meta["path"] = str(asset_path.as_posix())
        meta["cached_at"] = datetime.now(timezone.utc).isoformat()

        meta_path = self._meta_path(cache_key)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta
