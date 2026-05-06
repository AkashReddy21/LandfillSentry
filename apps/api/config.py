import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_defaults() -> None:
    root = Path(__file__).resolve().parents[2]
    for env_name in (".env.local", ".env"):
        env_path = root / env_name
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip().strip('"').strip("'")


_load_env_defaults()


def _as_bool(value: str, default: bool) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class Settings:
    db_path: Path
    cache_root: Path
    simsat_mode: str
    mapbox_mode: str
    simsat_base_url: str
    simsat_api_key: str
    simsat_window_seconds: int
    simsat_size_km: float
    simsat_spectral_bands: str
    simsat_satellite_alt_km: float
    simsat_use_for_mapbox: bool
    mapbox_base_url: str
    mapbox_token: str
    mapbox_username: str
    mapbox_style_id: str
    mapbox_zoom: int
    mapbox_width: int
    mapbox_height: int
    inference_mode: str
    hf_token: str
    hf_model_id: str
    hf_model_revision: str
    hf_adapter_id: str
    hf_adapter_revision: str
    hf_device_map: str
    hf_dtype: str
    hf_max_new_tokens: int
    hf_trust_remote_code: bool
    hf_local_files_only: bool
    inference_allow_fallback: bool
    modal_token: str
    modal_token_id: str
    modal_token_secret: str
    modal_environment: str
    modal_gpu: str
    modal_app_name: str
    require_live_results: bool


def load_settings() -> Settings:
    return Settings(
        db_path=Path(os.getenv("LS_DB_PATH", "data/processed/landfillsentry.db")),
        cache_root=Path(os.getenv("LS_CACHE_ROOT", "data/cache/assets")),
        simsat_mode=os.getenv("SIMSAT_MODE", "live").lower(),
        mapbox_mode=os.getenv("MAPBOX_MODE", "live").lower(),
        simsat_base_url=os.getenv("SIMSAT_BASE_URL", "http://localhost:9005").strip().rstrip("/"),
        simsat_api_key=os.getenv("SIMSAT_API_KEY", "").strip(),
        simsat_window_seconds=int(os.getenv("SIMSAT_WINDOW_SECONDS", "864000").strip()),
        simsat_size_km=float(os.getenv("SIMSAT_SIZE_KM", "5.0").strip()),
        simsat_spectral_bands=os.getenv("SIMSAT_SPECTRAL_BANDS", "red,green,blue").strip(),
        simsat_satellite_alt_km=float(os.getenv("SIMSAT_SATELLITE_ALT_KM", "800.0").strip()),
        simsat_use_for_mapbox=_as_bool(
            os.getenv("SIMSAT_USE_FOR_MAPBOX", "true"),
            default=True,
        ),
        mapbox_base_url=os.getenv("MAPBOX_BASE_URL", "").strip(),
        mapbox_token=os.getenv("MAPBOX_TOKEN", "").strip(),
        mapbox_username=os.getenv("MAPBOX_USERNAME", "mapbox").strip(),
        mapbox_style_id=os.getenv("MAPBOX_STYLE_ID", "satellite-v9").strip(),
        mapbox_zoom=int(os.getenv("MAPBOX_ZOOM", "14").strip()),
        mapbox_width=int(os.getenv("MAPBOX_WIDTH", "512").strip()),
        mapbox_height=int(os.getenv("MAPBOX_HEIGHT", "512").strip()),
        inference_mode=os.getenv("INFERENCE_MODE", "live").strip().lower(),
        hf_token=(os.getenv("HF_TOKEN", "").strip() or os.getenv("HUGGINGFACE_TOKEN", "").strip()),
        hf_model_id=os.getenv("HF_MODEL_ID", "LiquidAI/LFM2.5-VL-450M").strip(),
        hf_model_revision=os.getenv("HF_MODEL_REVISION", "main").strip(),
        hf_adapter_id=os.getenv("HF_ADAPTER_ID", "").strip(),
        hf_adapter_revision=os.getenv("HF_ADAPTER_REVISION", "main").strip(),
        hf_device_map=os.getenv("HF_DEVICE_MAP", "auto").strip(),
        hf_dtype=os.getenv("HF_DTYPE", "bfloat16").strip().lower(),
        hf_max_new_tokens=int(os.getenv("HF_MAX_NEW_TOKENS", "320").strip()),
        hf_trust_remote_code=_as_bool(os.getenv("HF_TRUST_REMOTE_CODE", "false"), default=False),
        hf_local_files_only=_as_bool(os.getenv("HF_LOCAL_FILES_ONLY", "true"), default=True),
        inference_allow_fallback=_as_bool(os.getenv("INFERENCE_ALLOW_FALLBACK", "false"), default=False),
        modal_token=os.getenv("MODAL_TOKEN", "").strip(),
        modal_token_id=os.getenv("MODAL_TOKEN_ID", "").strip(),
        modal_token_secret=os.getenv("MODAL_TOKEN_SECRET", "").strip(),
        modal_environment=os.getenv("MODAL_ENVIRONMENT", "main").strip(),
        modal_gpu=os.getenv("MODAL_GPU", "T4").strip().upper(),
        modal_app_name=os.getenv("MODAL_APP_NAME", "landfillsentry-lora-train").strip(),
        require_live_results=_as_bool(os.getenv("REQUIRE_LIVE_RESULTS", "false"), default=False),
    )
