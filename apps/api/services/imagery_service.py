import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple
from uuid import uuid4

from ..config import Settings
from ..schemas import ImageAsset, Site
from .cache_service import CacheService


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


class ImageryError(Exception):
    pass


@dataclass
class FetchResult:
    asset: ImageAsset
    mode: str


class ImageryService:
    def __init__(self, settings: Settings, cache: CacheService) -> None:
        self.settings = settings
        self.cache = cache

    def fetch_site_bundle(self, site: Site, force_refresh: bool = False) -> Tuple[Dict[str, ImageAsset], str]:
        current = self._fetch_asset(
            site=site,
            source="dphi-simsat",
            kind="current",
            mode=self.settings.simsat_mode,
            force_refresh=force_refresh,
        )
        historical = self._fetch_asset(
            site=site,
            source="dphi-simsat",
            kind="historical",
            mode=self.settings.simsat_mode,
            force_refresh=force_refresh,
        )
        mapbox = self._fetch_asset(
            site=site,
            source="mapbox",
            kind="context",
            mode=self.settings.mapbox_mode,
            force_refresh=force_refresh,
        )

        modes = {current.mode, historical.mode, mapbox.mode}
        overall_mode = "cached" if modes == {"cached"} else "live"
        if "cached_fallback" in modes:
            overall_mode = "cached_fallback"

        assets = {"current": current.asset, "historical": historical.asset, "mapbox": mapbox.asset}
        return assets, overall_mode

    def _fetch_asset(
        self,
        site: Site,
        source: str,
        kind: str,
        mode: str,
        force_refresh: bool,
    ) -> FetchResult:
        cache_key = self.cache.make_cache_key(
            namespace=f"{source}:{kind}",
            payload={"site_id": site.site_id, "lat": site.lat, "lon": site.lon},
        )

        cached = self.cache.read(cache_key)
        if cached and not force_refresh:
            return FetchResult(asset=self._meta_to_asset(site, source, cache_key, cached), mode="cached")

        try:
            blob, metadata = self._fetch_live_or_mock(site, source=source, kind=kind, mode=mode)
        except ImageryError:
            if cached:
                return FetchResult(asset=self._meta_to_asset(site, source, cache_key, cached), mode="cached_fallback")
            raise

        written = self.cache.write(cache_key=cache_key, blob=blob, metadata=metadata, ext=".img")
        return FetchResult(asset=self._meta_to_asset(site, source, cache_key, written), mode="live")

    def _meta_to_asset(self, site: Site, source: str, cache_key: str, meta: Dict) -> ImageAsset:
        return ImageAsset(
            asset_id=f"asset_{uuid4().hex[:12]}",
            site_id=site.site_id,
            source=source,
            timestamp_requested=meta["timestamp_requested"],
            timestamp_captured=meta["timestamp_captured"],
            cloud_cover=float(meta["cloud_cover"]),
            bands=list(meta["bands"]),
            local_path=meta["path"],
            cache_key=cache_key,
        )

    def _fetch_live_or_mock(self, site: Site, source: str, kind: str, mode: str) -> Tuple[bytes, Dict]:
        fixture_class = str(site.metadata.get("fixture_class", "")).lower()
        if fixture_class == "missing_data":
            raise ImageryError(f"{source}:{kind} unavailable for missing_data fixture")

        if mode == "mock":
            return self._mock_payload(site, source, kind, fixture_class)
        if mode != "live":
            raise ImageryError(f"unsupported mode: {mode}")

        if source in {"simsat", "dphi-simsat"}:
            try:
                return self._fetch_simsat_live(site=site, kind=kind)
            except ImageryError:
                if self.settings.require_live_results:
                    raise
                return self._fetch_direct_sentinel_live(site=site, kind=kind)

        if source == "mapbox":
            if self.settings.simsat_use_for_mapbox:
                try:
                    return self._fetch_simsat_mapbox_live(site=site)
                except ImageryError:
                    if self.settings.require_live_results:
                        raise
                    # SimSat Mapbox can report image-unavailable for some coordinates.
                    # Fall back to direct Mapbox when token config is present.
                    if self.settings.mapbox_token or self.settings.mapbox_base_url:
                        return self._fetch_direct_mapbox_live(site=site)
                    raise
            return self._fetch_direct_mapbox_live(site=site)

        raise ImageryError(f"unknown source: {source}")

    def _fetch_direct_sentinel_live(self, site: Site, kind: str) -> Tuple[bytes, Dict]:
        query_dt = datetime.now(timezone.utc) if kind == "current" else datetime.now(timezone.utc) - timedelta(days=7)
        return self.fetch_direct_sentinel_at(site=site, query_dt=query_dt)

    def fetch_direct_sentinel_at(self, site: Site, query_dt: datetime) -> Tuple[bytes, Dict]:
        try:
            from pystac_client import Client
        except Exception as exc:  # pragma: no cover - dependency import
            raise ImageryError(f"direct sentinel dependency unavailable: {exc}") from exc

        request_dt = datetime.now(timezone.utc)
        window_start = query_dt - timedelta(seconds=float(self.settings.simsat_window_seconds))
        datetime_window = f"{self._iso_utc(window_start)}/{self._iso_utc(query_dt)}"
        bbox = self._bbox_around_lon_lat(site.lon, site.lat, image_size_km=self.settings.simsat_size_km)

        try:
            client = Client.open("https://earth-search.aws.element84.com/v1")
            search = client.search(
                collections=["sentinel-2-l2a"],
                bbox=bbox,
                datetime=datetime_window,
                query={"eo:cloud_cover": {"lt": 100}},
                max_items=10,
            )
            items = list(search.items())
        except Exception as exc:
            raise ImageryError(f"direct sentinel search failed: {exc}") from exc

        if not items:
            raise ImageryError(f"direct sentinel image unavailable for site {site.site_id}")
        item = max(items, key=lambda i: i.datetime or datetime.fromtimestamp(0, tz=timezone.utc))
        asset = item.assets.get("thumbnail") or item.assets.get("rendered_preview") or item.assets.get("visual")
        if not asset:
            raise ImageryError(f"direct sentinel preview asset unavailable for site {site.site_id}")

        try:
            blob, headers = self._http_get(asset.href)
        except ImageryError as exc:
            raise ImageryError(f"direct sentinel asset fetch failed: {exc}") from exc

        content_type = str(headers.get("content-type", "")).lower()
        if "tiff" in content_type:
            raise ImageryError("direct sentinel visual GeoTIFF preview requires thumbnail asset")

        cloud_cover = self._normalize_cloud_cover(item.properties.get("eo:cloud_cover", 0.0))
        capture_dt = item.datetime or query_dt
        platform = str(item.properties.get("platform", "sentinel-2"))
        return blob, {
            "timestamp_requested": self._iso_utc(request_dt),
            "timestamp_captured": self._iso_utc(capture_dt),
            "cloud_cover": cloud_cover,
            "bands": ["RGB"],
            "source": f"direct-{platform}",
            "footprint": list(bbox),
        }

    def fetch_direct_mapbox_for_site(self, site: Site) -> Tuple[bytes, Dict]:
        return self._fetch_direct_mapbox_live(site)

    def _mock_payload(self, site: Site, source: str, kind: str, fixture_class: str) -> Tuple[bytes, Dict]:
        now = datetime.now(timezone.utc)
        cloud_cover = 0.85 if fixture_class == "cloudy" and source in {"simsat", "dphi-simsat"} else 0.10
        captured = now - timedelta(days=7) if kind == "historical" else now
        bands = ["RGB"] if source == "mapbox" else self._spectral_bands_default()

        payload = {
            "site_id": site.site_id,
            "source": source,
            "kind": kind,
            "fixture_class": fixture_class or "default",
            "generated_at": now.isoformat(),
        }
        blob = json.dumps(payload, indent=2).encode("utf-8")
        metadata = {
            "timestamp_requested": now.isoformat(),
            "timestamp_captured": captured.isoformat(),
            "cloud_cover": cloud_cover,
            "bands": bands,
        }
        return blob, metadata

    def _fetch_simsat_live(self, site: Site, kind: str) -> Tuple[bytes, Dict]:
        if not self.settings.simsat_base_url:
            raise ImageryError("SIMSAT_BASE_URL is required in live mode")

        request_time = self._iso_utc(datetime.now(timezone.utc))
        query_time = datetime.now(timezone.utc) if kind == "current" else datetime.now(timezone.utc) - timedelta(days=7)
        query_timestamp = self._iso_utc(query_time)
        spectral_bands = self._spectral_bands_default()
        endpoint = "/data/current/image/sentinel" if kind == "current" else "/data/image/sentinel"
        params = {
            "lon": f"{site.lon}",
            "lat": f"{site.lat}",
            "timestamp": query_timestamp,
            "size_km": f"{self.settings.simsat_size_km}",
            "window_seconds": f"{self.settings.simsat_window_seconds}",
            "return_type": "png",
            "spectral_bands": spectral_bands,
        }
        url = (
            f"{self.settings.simsat_base_url}{endpoint}?"
            f"{urllib.parse.urlencode(params, doseq=True)}"
        )

        body, headers = self._http_get(url)
        metadata = self._parse_json_header(headers.get("sentinel_metadata"))

        image_available = bool(metadata.get("image_available", True))
        if not image_available:
            raise ImageryError(f"DPhi SimSat sentinel image unavailable for site {site.site_id}")

        capture_time = self._safe_timestamp(metadata.get("datetime"), fallback=query_timestamp)
        cloud_cover = self._normalize_cloud_cover(metadata.get("cloud_cover", 0.0))
        bands = self._as_str_list(metadata.get("spectral_bands")) or self._spectral_bands_default()

        return body, {
            "timestamp_requested": request_time,
            "timestamp_captured": capture_time,
            "cloud_cover": cloud_cover,
            "bands": bands,
            "source": metadata.get("source", "dphi-simsat-sentinel"),
        }

    def _fetch_simsat_mapbox_live(self, site: Site) -> Tuple[bytes, Dict]:
        if not self.settings.simsat_base_url:
            raise ImageryError("SIMSAT_BASE_URL is required in live mode")

        params = {
            "lon": f"{site.lon}",
            "lat": f"{site.lat}",
        }
        url = f"{self.settings.simsat_base_url}/data/current/image/mapbox?{urllib.parse.urlencode(params)}"
        body, headers = self._http_get(url)
        metadata = self._parse_json_header(headers.get("mapbox_metadata"))

        if not bool(metadata.get("image_available", True)):
            raise ImageryError(f"DPhi SimSat mapbox image unavailable for site {site.site_id}")

        now = self._iso_utc(datetime.now(timezone.utc))
        return body, {
            "timestamp_requested": now,
            "timestamp_captured": now,
            "cloud_cover": 0.0,
            "bands": ["RGB"],
            "source": "dphi-simsat-mapbox",
        }

    def _fetch_direct_mapbox_live(self, site: Site) -> Tuple[bytes, Dict]:
        base_url = self.settings.mapbox_base_url.strip()
        if not base_url:
            base_url = (
                f"https://api.mapbox.com/styles/v1/{self.settings.mapbox_username}/"
                f"{self.settings.mapbox_style_id}/static"
            )
        if not self.settings.mapbox_token:
            raise ImageryError("MAPBOX_TOKEN is required in live mode")

        location = (
            f"/{site.lon},{site.lat},{self.settings.mapbox_zoom},0,0/"
            f"{self.settings.mapbox_width}x{self.settings.mapbox_height}"
        )
        url = f"{base_url}{location}?access_token={urllib.parse.quote(self.settings.mapbox_token)}"

        body, _headers = self._http_get(url)
        now = self._iso_utc(datetime.now(timezone.utc))
        return body, {
            "timestamp_requested": now,
            "timestamp_captured": now,
            "cloud_cover": 0.0,
            "bands": ["RGB"],
            "source": "mapbox-direct",
        }

    def _bbox_around_lon_lat(self, lon: float, lat: float, image_size_km: float) -> Tuple[float, float, float, float]:
        import math

        earth_radius_km = 6371.0
        half_side = image_size_km / 2.0
        d_lat = math.degrees(half_side / earth_radius_km)
        cos_lat = max(0.01, abs(math.cos(math.radians(lat))))
        d_lon = math.degrees(half_side / (earth_radius_km * cos_lat))
        return (lon - d_lon, lat - d_lat, lon + d_lon, lat + d_lat)

    def _http_get(self, url: str) -> Tuple[bytes, Dict[str, str]]:
        req = urllib.request.Request(url)
        if self.settings.simsat_api_key:
            req.add_header("Authorization", f"Bearer {self.settings.simsat_api_key}")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return body, headers
        except Exception as exc:  # pragma: no cover - network path
            raise ImageryError(f"http fetch failed ({url}): {exc}") from exc

    def _parse_json_header(self, raw_header: str | None) -> Dict:
        if not raw_header:
            return {}
        try:
            return json.loads(raw_header)
        except Exception:
            return {}

    def _spectral_bands_default(self) -> List[str]:
        bands = [p.strip() for p in self.settings.simsat_spectral_bands.split(",") if p.strip()]
        return bands or ["red", "green", "blue"]

    def _as_str_list(self, value) -> List[str]:
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            return [p.strip() for p in value.split(",") if p.strip()]
        return []

    def _iso_utc(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _safe_timestamp(self, value, fallback: str) -> str:
        if not value:
            return fallback
        try:
            if isinstance(value, str):
                if value.endswith("Z"):
                    base = value[:-1]
                    dt = datetime.fromisoformat(base).replace(tzinfo=timezone.utc)
                else:
                    dt = datetime.fromisoformat(value)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                return self._iso_utc(dt)
        except Exception:
            pass
        return fallback

    def _normalize_cloud_cover(self, value) -> float:
        try:
            cloud = float(value)
        except Exception:
            return 0.0
        if cloud > 1.0:
            cloud = cloud / 100.0
        return _clamp(cloud)
