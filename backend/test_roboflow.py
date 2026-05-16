"""Manual Roboflow smoke/diagnostic test.

Usage:
    python backend/test_roboflow.py path/to/test-image.jpg
    python backend/test_roboflow.py path/to/test-image.jpg --diagnose

The script calls the same service used by the production detector and prints a
small, readable table. It never embeds credentials; configure `.env` instead.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.services.roboflow_service import detect_defects

load_dotenv()


def _compact(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "..."
    if isinstance(value, dict):
        compacted = {}
        for key, child in value.items():
            if isinstance(child, str) and len(child) > 120:
                compacted[key] = f"<str len={len(child)}>"
            else:
                compacted[key] = _compact(child, depth + 1)
        return compacted
    if isinstance(value, list):
        head = [_compact(item, depth + 1) for item in value[:3]]
        if len(value) > 3:
            head.append(f"<list more={len(value) - 3}>")
        return head
    return value


def _diagnose_workflow(image_path: Path) -> int:
    from inference_sdk import InferenceHTTPClient

    api_key = os.getenv("ROBOFLOW_API_KEY")
    workspace = os.getenv("ROBOFLOW_WORKSPACE_NAME")
    workflow = os.getenv("ROBOFLOW_WORKFLOW_ID")
    image_key = os.getenv("ROBOFLOW_WORKFLOW_IMAGE_KEY", "image")
    api_url = os.getenv("ROBOFLOW_API_URL", "https://serverless.roboflow.com")

    print("Roboflow diagnostic")
    print("-" * 72)
    print(f"api_url: {api_url}")
    print(f"api_key: {'set' if api_key else 'missing'}")
    print(f"workspace: {workspace or 'missing'}")
    print(f"workflow: {workflow or 'missing'}")
    print(f"configured image key: {image_key}")
    print(f"image: {image_path}")

    if not api_key or not workspace or not workflow:
        print("Missing required Roboflow environment values.")
        return 2

    client = InferenceHTTPClient(api_url=api_url, api_key=api_key)
    keys = []
    for candidate in [image_key, "image", "input_image", "image_input", "file"]:
        if candidate and candidate not in keys:
            keys.append(candidate)

    for candidate in keys:
        try:
            result = client.run_workflow(
                workspace_name=workspace,
                workflow_id=workflow,
                images={candidate: str(image_path)},
                use_cache=False,
            )
            print(f"workflow input key accepted: {candidate}")
            print("raw output summary:")
            print(json.dumps(_compact(result), indent=2, default=str))
            return 0
        except Exception as exc:
            print(f"workflow input key failed: {candidate} -> {str(exc)[:500]}")

    print("No tested workflow image input key was accepted.")
    return 3


def main() -> int:
    diagnose = "--diagnose" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != "--diagnose"]
    image_path = Path(args[0]) if args else Path("test.jpg")
    if not image_path.exists():
        print(f"Test image not found: {image_path}")
        print("Pass a file path, for example: python backend/test_roboflow.py uploads/sample.jpg")
        return 1

    if diagnose:
        status = _diagnose_workflow(image_path)
        print()
        if status != 0:
            return status

    try:
        detections = detect_defects(str(image_path))
    except Exception as exc:
        print(f"Roboflow test failed: {exc}")
        return 1

    print(f"Roboflow detections for: {image_path}")
    print("-" * 72)
    if not detections:
        print("No detections returned.")
        return 0

    for index, detection in enumerate(detections, start=1):
        bbox = detection["bbox"]
        print(
            f"{index:02d}. class={detection['class']:<24} "
            f"confidence={detection['confidence']:.2f} "
            f"bbox=[{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
