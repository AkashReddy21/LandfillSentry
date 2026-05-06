import os
import shutil
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse
from pathlib import Path

from apps.api.config import load_settings
from apps.api.schemas import Site
from apps.api.services.cache_service import CacheService
from apps.api.services.imagery_service import ImageryError, ImageryService


class Phase2IntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ls_phase2_"))
        self.db_path = self.tmpdir / "landfillsentry.db"
        self.cache_root = self.tmpdir / "cache"
        self.old_env = os.environ.copy()

        os.environ["LS_DB_PATH"] = str(self.db_path)
        os.environ["LS_CACHE_ROOT"] = str(self.cache_root)
        os.environ["SIMSAT_MODE"] = "mock"
        os.environ["MAPBOX_MODE"] = "mock"
        os.environ["REQUIRE_LIVE_RESULTS"] = "false"

        settings = load_settings()
        self.imagery = ImageryService(settings=settings, cache=CacheService(settings.cache_root))

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.old_env)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _site(self, site_id: str, fixture_class: str) -> Site:
        return Site(
            site_id=site_id,
            name=site_id,
            lat=22.5726,
            lon=88.3639,
            country="IN",
            operator="Demo Operator",
            watchlist_enabled=True,
            polygon_geojson=None,
            metadata={"fixture_class": fixture_class},
        )

    def test_positive_and_negative_sites_fetch_cleanly(self) -> None:
        for site in (self._site("LF_POS_001", "positive"), self._site("LF_NEG_001", "negative")):
            assets, mode = self.imagery.fetch_site_bundle(site=site, force_refresh=False)
            self.assertEqual(mode, "live")
            self.assertTrue(Path(assets["current"].local_path).exists())
            self.assertTrue(Path(assets["historical"].local_path).exists())
            self.assertTrue(Path(assets["mapbox"].local_path).exists())

    def test_cached_replay_works_after_first_fetch(self) -> None:
        site = self._site("LF_CACHE_001", "positive")
        first_assets, first_mode = self.imagery.fetch_site_bundle(site=site, force_refresh=False)
        second_assets, second_mode = self.imagery.fetch_site_bundle(site=site, force_refresh=False)

        self.assertEqual(first_mode, "live")
        self.assertEqual(second_mode, "cached")
        self.assertEqual(first_assets["mapbox"].local_path, second_assets["mapbox"].local_path)

    def test_missing_data_fails_gracefully(self) -> None:
        site = self._site("LF_MISS_001", "missing_data")
        with self.assertRaises(ImageryError):
            self.imagery.fetch_site_bundle(site=site, force_refresh=False)

    def test_live_mode_requires_configured_live_backends(self) -> None:
        os.environ["SIMSAT_MODE"] = "live"
        os.environ["MAPBOX_MODE"] = "live"
        os.environ["SIMSAT_BASE_URL"] = ""
        os.environ["SIMSAT_USE_FOR_MAPBOX"] = "true"
        os.environ["MAPBOX_BASE_URL"] = ""
        os.environ["MAPBOX_TOKEN"] = ""
        settings = load_settings()
        imagery = ImageryService(settings=settings, cache=CacheService(settings.cache_root))

        site = self._site("LF_LIVE_001", "positive")
        with self.assertRaises(ImageryError):
            imagery.fetch_site_bundle(site=site, force_refresh=True)

    def test_live_endpoint_split_current_vs_historical(self) -> None:
        os.environ["SIMSAT_MODE"] = "live"
        os.environ["MAPBOX_MODE"] = "live"
        os.environ["SIMSAT_BASE_URL"] = "http://localhost:9005"
        os.environ["SIMSAT_USE_FOR_MAPBOX"] = "true"
        settings = load_settings()

        class _StubImageryService(ImageryService):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.urls = []

            def _http_get(self, url: str):
                self.urls.append(url)
                if "/sentinel" in url:
                    header = {
                        "sentinel_metadata": (
                            '{"image_available": true, "source": "sentinel-2a", '
                            '"spectral_bands": ["red","green","blue"], "cloud_cover": 12.0, '
                            '"datetime": "2026-03-16T13:53:37Z"}'
                        )
                    }
                else:
                    header = {"mapbox_metadata": '{"image_available": true, "target_visible": true}'}
                return b"stub", header

        imagery = _StubImageryService(settings=settings, cache=CacheService(settings.cache_root))
        site = self._site("LF_SPLIT_001", "positive")
        imagery.fetch_site_bundle(site=site, force_refresh=True)

        self.assertTrue(any("/data/current/image/sentinel" in u for u in imagery.urls))
        self.assertTrue(any("/data/image/sentinel" in u for u in imagery.urls))
        self.assertTrue(any("/data/current/image/mapbox" in u for u in imagery.urls))

        sentinel_urls = [u for u in imagery.urls if "/sentinel" in u]
        self.assertGreaterEqual(len(sentinel_urls), 2)
        for url in sentinel_urls:
            parsed = parse_qs(urlparse(url).query)
            self.assertEqual(parsed.get("spectral_bands"), ["red", "green", "blue"])


if __name__ == "__main__":
    unittest.main()
