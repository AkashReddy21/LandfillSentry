from functools import lru_cache

from .config import load_settings
from .db.repository import Repository
from .services.candidate_service import CandidateService
from .services.cache_service import CacheService
from .services.inference_service import InferenceService
from .services.imagery_service import ImageryService
from .services.output_validation_service import OutputValidationService
from .services.panel_service import PanelService
from .services.prompt_contract_service import PromptContractService


@lru_cache(maxsize=1)
def get_settings():
    return load_settings()


@lru_cache(maxsize=1)
def get_repository() -> Repository:
    settings = get_settings()
    repo = Repository(settings.db_path)
    repo.init_schema()
    return repo


@lru_cache(maxsize=1)
def get_cache_service() -> CacheService:
    settings = get_settings()
    return CacheService(settings.cache_root)


@lru_cache(maxsize=1)
def get_imagery_service() -> ImageryService:
    return ImageryService(settings=get_settings(), cache=get_cache_service())


@lru_cache(maxsize=1)
def get_candidate_service() -> CandidateService:
    return CandidateService()


@lru_cache(maxsize=1)
def get_panel_service() -> PanelService:
    return PanelService(cache=get_cache_service())


@lru_cache(maxsize=1)
def get_prompt_contract_service() -> PromptContractService:
    return PromptContractService()


@lru_cache(maxsize=1)
def get_output_validation_service() -> OutputValidationService:
    return OutputValidationService()


@lru_cache(maxsize=1)
def get_inference_service() -> InferenceService:
    return InferenceService(settings=get_settings())


def reset_runtime_caches() -> None:
    get_inference_service.cache_clear()
    get_output_validation_service.cache_clear()
    get_prompt_contract_service.cache_clear()
    get_panel_service.cache_clear()
    get_candidate_service.cache_clear()
    get_imagery_service.cache_clear()
    get_cache_service.cache_clear()
    get_repository.cache_clear()
    get_settings.cache_clear()
