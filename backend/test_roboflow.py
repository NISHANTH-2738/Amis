"""Manual Roboflow smoke test.

Usage:
    python backend/test_roboflow.py path/to/test-image.jpg

The script calls the same service used by the production detector and prints a
small, readable table. It never embeds credentials; configure `.env` instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.services.roboflow_service import detect_defects

load_dotenv()


def main() -> int:
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("test.jpg")
    if not image_path.exists():
        print(f"Test image not found: {image_path}")
        print("Pass a file path, for example: python backend/test_roboflow.py uploads/sample.jpg")
        return 1

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
