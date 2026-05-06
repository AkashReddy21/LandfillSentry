import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.api.config import load_settings
from apps.api.services.inference_service import InferenceService


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LFM2.5-VL-450M examples (image QA, bbox grounding, tool-use).")
    parser.add_argument(
        "--env-file",
        default=str(Path(__file__).resolve().parents[1] / ".env.local"),
        help="Environment file to load before running.",
    )
    parser.add_argument(
        "--image",
        default="https://cdn.britannica.com/61/93061-050-99147DCE/Statue-of-Liberty-Island-New-York-Bay.jpg",
        help="Image URL or local path.",
    )
    parser.add_argument("--question", default="What is in this image?", help="Question for image QA.")
    parser.add_argument("--query", default="statue", help="Entity query for visual grounding.")
    parser.add_argument("--max-new-tokens", type=int, default=96, help="Generation length.")
    args = parser.parse_args()

    _load_env_file(Path(args.env_file))
    os.environ["INFERENCE_MODE"] = "live"

    settings = load_settings()
    service = InferenceService(settings=settings)

    print("=== Image QA ===")
    qa = service.answer_from_image(
        image_path=args.image,
        text_prompt=args.question,
        max_new_tokens=args.max_new_tokens,
    )
    print(qa)

    print("\n=== Visual Grounding (bbox JSON expected) ===")
    bbox = service.detect_bounding_boxes(
        image_path=args.image,
        query=args.query,
        max_new_tokens=args.max_new_tokens,
    )
    print(bbox)

    print("\n=== Tool Use (text-only) ===")
    tools = [
        {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        }
    ]
    messages = [{"role": "user", "content": "What's the weather in Paris?"}]
    tool_out = service.tool_use_response(messages=messages, tools=tools, max_new_tokens=128)
    print(tool_out)


if __name__ == "__main__":
    main()
