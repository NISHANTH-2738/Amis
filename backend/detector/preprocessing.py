from __future__ import annotations

from pathlib import Path

from backend.utils.image import image_metadata, validate_image_path


def prepare_image(image_path: str | Path) -> dict:
    path = validate_image_path(image_path)
    metadata = image_metadata(path)
    metadata["path"] = str(path)
    return metadata
