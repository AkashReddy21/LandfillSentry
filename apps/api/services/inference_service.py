import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List

from ..config import Settings
from ..schemas import Candidate, EvidencePanel, Site


class InferenceError(Exception):
    pass


@dataclass
class InferenceResult:
    raw_outputs: List[Any]
    mode: str
    model_id: str
    model_revision: str
    model_ref: str
    auth_configured: bool
    error_message: str | None = None


class InferenceService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model = None
        self._processor = None

    def generate_incident_outputs(
        self,
        site: Site,
        panel: EvidencePanel,
        prompt_bundle: Dict,
        candidate: Candidate,
        incident_id: str,
        scan_id: str,
    ) -> InferenceResult:
        seed_output = self._seed_incident_output(
            site=site,
            candidate=candidate,
            incident_id=incident_id,
            scan_id=scan_id,
        )
        if self.settings.inference_mode != "live":
            return InferenceResult(
                raw_outputs=[seed_output],
                mode="mock",
                model_id=self.settings.hf_model_id,
                model_revision=self.settings.hf_model_revision or "main",
                model_ref=self._model_ref(),
                auth_configured=bool(self.settings.hf_token),
                error_message=None,
            )

        try:
            answer = self.answer_from_image(
                image_path=panel.current_rgb_path,
                text_prompt=prompt_bundle["user_prompt"],
                max_new_tokens=self.settings.hf_max_new_tokens,
                system_prompt=prompt_bundle.get("system_prompt"),
            )
            extracted = self._extract_json_payload(answer)
            if extracted is None:
                retry_prompt = (
                    prompt_bundle["user_prompt"]
                    + " IMPORTANT: Return exactly one valid JSON object only. No markdown, no code fences, no prose."
                )
                retry_answer = self.answer_from_image(
                    image_path=panel.current_rgb_path,
                    text_prompt=retry_prompt,
                    max_new_tokens=max(self.settings.hf_max_new_tokens, 512),
                    system_prompt=prompt_bundle.get("system_prompt"),
                )
                extracted = self._extract_json_payload(retry_answer)
            if extracted is None and not self.settings.inference_allow_fallback:
                raise InferenceError(
                    "live model output was not valid JSON object; "
                    "increase HF_MAX_NEW_TOKENS or adjust prompt contract"
                )
            outputs: List[Any] = [extracted if extracted is not None else answer]
            if self.settings.inference_allow_fallback:
                outputs.append(seed_output)
            return InferenceResult(
                raw_outputs=outputs,
                mode="live",
                model_id=self.settings.hf_model_id,
                model_revision=self.settings.hf_model_revision or "main",
                model_ref=self._model_ref(),
                auth_configured=bool(self.settings.hf_token),
                error_message=None,
            )
        except Exception as exc:
            if not self.settings.inference_allow_fallback:
                raise InferenceError(str(exc)) from exc
            # Optional fallback mode for offline/demo-only paths.
            fallback_note = {
                "error": "inference_runtime_failed",
                "message": str(exc),
                "model_id": self.settings.hf_model_id,
            }
            return InferenceResult(
                raw_outputs=[fallback_note, seed_output],
                mode="fallback",
                model_id=self.settings.hf_model_id,
                model_revision=self.settings.hf_model_revision or "main",
                model_ref=self._model_ref(),
                auth_configured=bool(self.settings.hf_token),
                error_message=str(exc),
            )

    def answer_from_image(
        self,
        image_path: str,
        text_prompt: str,
        max_new_tokens: int = 64,
        system_prompt: str | None = None,
    ) -> str:
        model, processor = self._load_model_stack()
        image = self._load_image(image_path)
        conversation = []
        if system_prompt:
            conversation.append({"role": "system", "content": [{"type": "text", "text": system_prompt}]})
        conversation.append(
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": text_prompt},
                ],
            }
        )
        inputs = processor.apply_chat_template(
            conversation,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
            tokenize=True,
        )
        inputs = self._move_inputs_to_model_device(inputs, model)
        outputs = model.generate(**inputs, max_new_tokens=max_new_tokens)
        if "input_ids" in inputs:
            prompt_len = inputs["input_ids"].shape[1]
            return processor.batch_decode(outputs[:, prompt_len:], skip_special_tokens=True)[0]
        return processor.batch_decode(outputs, skip_special_tokens=True)[0]

    def detect_bounding_boxes(
        self,
        image_path: str,
        query: str,
        max_new_tokens: int = 128,
    ) -> str:
        prompt = (
            f'Detect all instances of: {query}. Response must be a JSON array: '
            f'[{{"label": ..., "bbox": [x1, y1, x2, y2]}}, ...]. '
            "Coordinates are normalized to [0,1]."
        )
        return self.answer_from_image(image_path=image_path, text_prompt=prompt, max_new_tokens=max_new_tokens)

    def tool_use_response(self, messages: List[Dict], tools: List[Dict], max_new_tokens: int = 256) -> str:
        model, processor = self._load_model_stack()
        inputs = processor.tokenizer.apply_chat_template(
            messages,
            tools=tools,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        )
        input_ids = inputs["input_ids"].to(self._model_device(model))
        outputs = model.generate(input_ids=input_ids, max_new_tokens=max_new_tokens)
        return processor.tokenizer.decode(outputs[0, input_ids.shape[1] :], skip_special_tokens=False)

    def _seed_incident_output(
        self,
        site: Site,
        candidate: Candidate,
        incident_id: str,
        scan_id: str,
    ) -> Dict:
        return {
            "incident_id": incident_id,
            "site_id": site.site_id,
            "job_id": scan_id,
            "confidence": candidate.candidate_score,
            "bbox_norm": list(candidate.bbox_norm),
            "likely_source_zone_prior": candidate.likely_source_zone_prior.value,
            "temporal_recurrence": candidate.temporal_recurrence,
            "evidence_summary": (
                f"Fallback candidate output: score {candidate.candidate_score:.2f}, "
                f"zone {candidate.likely_source_zone_prior.value}."
            ),
            "model_version": f"{self.settings.hf_model_id}@{self.settings.hf_model_revision}",
        }

    def _extract_json_payload(self, text: str) -> Dict | List | None:
        if not isinstance(text, str):
            return None
        candidates = []
        arr_start = text.find("[")
        arr_end = text.rfind("]")
        if arr_start != -1 and arr_end > arr_start:
            candidates.append(text[arr_start : arr_end + 1])
        obj_start = text.find("{")
        obj_end = text.rfind("}")
        if obj_start != -1 and obj_end > obj_start:
            candidates.append(text[obj_start : obj_end + 1])
        for raw in candidates:
            try:
                return json.loads(raw)
            except Exception:
                continue
        return None

    def _load_model_stack(self):
        if self._model is not None and self._processor is not None:
            return self._model, self._processor
        try:
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor
            from transformers.utils import logging as transformers_logging
        except Exception as exc:  # pragma: no cover - import path
            raise InferenceError(f"transformers stack unavailable: {exc}") from exc

        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        try:
            transformers_logging.disable_progress_bar()
        except Exception:
            pass
        try:
            from huggingface_hub.utils import disable_progress_bars

            disable_progress_bars()
        except Exception:
            pass

        if not self.settings.hf_model_id:
            raise InferenceError("HF_MODEL_ID is required for live inference mode")

        base_model_kwargs = {
            "revision": self.settings.hf_model_revision or "main",
        }
        if self.settings.hf_token:
            base_model_kwargs["token"] = self.settings.hf_token

        dtype = self._resolve_dtype(torch)
        if dtype is not None:
            base_model_kwargs["dtype"] = dtype

        if torch.cuda.is_available():
            base_model_kwargs["device_map"] = self.settings.hf_device_map or "auto"
        else:
            # Stable CPU path: avoid accelerate auto-sharding/meta tensors.
            base_model_kwargs["low_cpu_mem_usage"] = False

        # Attempt 1 honors env setting. Attempt 2 enforces local cached files and built-in classes.
        load_attempts = [
            {
                "trust_remote_code": bool(self.settings.hf_trust_remote_code),
                "local_files_only": bool(self.settings.hf_local_files_only),
            },
            {
                "trust_remote_code": False,
                "local_files_only": True,
            },
        ]
        last_exc: Exception | None = None
        for attempt in load_attempts:
            model_kwargs = dict(base_model_kwargs)
            model_kwargs.update(attempt)
            processor_kwargs = {
                "revision": self.settings.hf_model_revision or "main",
                "trust_remote_code": attempt["trust_remote_code"],
                "local_files_only": attempt["local_files_only"],
                "token": self.settings.hf_token or None,
            }
            try:
                self._model = AutoModelForImageTextToText.from_pretrained(self.settings.hf_model_id, **model_kwargs)
                self._processor = AutoProcessor.from_pretrained(self.settings.hf_model_id, **processor_kwargs)
                break
            except Exception as exc:
                last_exc = exc
                self._model = None
                self._processor = None
                continue
        if self._model is None or self._processor is None:
            raise InferenceError(f"failed to load model/processor stack: {last_exc}")

        if self.settings.hf_adapter_id:
            try:
                from peft import PeftModel

                adapter_kwargs: Dict[str, Any] = {}
                if self.settings.hf_token:
                    adapter_kwargs["token"] = self.settings.hf_token
                if self.settings.hf_adapter_revision:
                    adapter_kwargs["revision"] = self.settings.hf_adapter_revision
                self._model = PeftModel.from_pretrained(self._model, self.settings.hf_adapter_id, **adapter_kwargs)
            except Exception as exc:
                raise InferenceError(f"failed to load adapter {self.settings.hf_adapter_id}: {exc}") from exc
        if not torch.cuda.is_available():
            self._model.to("cpu")
        return self._model, self._processor

    def _resolve_dtype(self, torch_module):
        selected = (self.settings.hf_dtype or "").lower()
        if selected == "bfloat16" and torch_module.cuda.is_available():
            return torch_module.bfloat16
        if selected in {"float16", "fp16"} and torch_module.cuda.is_available():
            return torch_module.float16
        if selected in {"float32", "fp32"}:
            return torch_module.float32
        if selected == "bfloat16":
            # CPU fallback for stability.
            return torch_module.float32
        return None

    def _load_image(self, image_path: str):
        try:
            from transformers.image_utils import load_image
        except Exception as exc:  # pragma: no cover - import path
            raise InferenceError(f"load_image unavailable: {exc}") from exc
        try:
            return load_image(image_path)
        except Exception as exc:
            raise InferenceError(f"failed to load image for inference ({image_path}): {exc}") from exc

    def _move_inputs_to_model_device(self, inputs: Dict, model):
        target = self._model_device(model)
        out = {}
        for key, value in inputs.items():
            if hasattr(value, "to"):
                out[key] = value.to(target)
            else:
                out[key] = value
        return out

    def _model_device(self, model):
        if hasattr(model, "device"):
            return model.device
        return "cpu"

    def _model_ref(self) -> str:
        base_ref = f"{self.settings.hf_model_id}@{self.settings.hf_model_revision or 'main'}"
        if not self.settings.hf_adapter_id:
            return base_ref
        return f"{base_ref}+adapter={self.settings.hf_adapter_id}@{self.settings.hf_adapter_revision or 'main'}"
