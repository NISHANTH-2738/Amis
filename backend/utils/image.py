from __future__ import annotations

from pathlib import Path

from PIL import Image


SUPPORTED_IMAGE_TYPES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}


def validate_image_path(image_path: str | Path) -> Path:
    path = Path(image_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")
    if path.suffix.lower() not in SUPPORTED_IMAGE_TYPES:
        raise ValueError(f"Unsupported image type: {path.suffix}")
    with Image.open(path) as image:
        image.verify()
    return path


def image_metadata(image_path: str | Path) -> dict:
    path = Path(image_path)
    with Image.open(path) as image:
        return {
            "width": image.width,
            "height": image.height,
            "saved_path": str(path),
        }
