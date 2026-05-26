from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Any


DEFAULT_MODEL_PATH = Path(
    os.getenv("YOLO_MODEL_PATH", "backend/models/best.pt")
)


class ModelUnavailableError(RuntimeError):
    """Raised when production inference cannot run because weights are absent."""


class YoloV8Engine:
    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH):
        self.model_path = Path(model_path)
        self._model: Any | None = None
        self._lock = Lock()

    def status(self) -> dict:
        return {
            "primary_model": "yolov8",
            "weights_path": str(self.model_path),
            "weights_available": self.model_path.exists(),
            "loaded": self._model is not None,
            "fallback": None,
        }

    def load(self, force: bool = False):
        with self._lock:
            if self._model is not None and not force:
                return self._model

            if not self.model_path.exists():
                raise ModelUnavailableError(
                    f"YOLOv8 weights not found at {self.model_path}. "
                    "Place best.pt there or set YOLO_MODEL_PATH."
                )

            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise ModelUnavailableError(
                    "ultralytics is not installed in this environment."
                ) from exc

            self._model = YOLO(str(self.model_path))
            return self._model

    def predict(self, image_path: str, confidence: float, image_size: int):
        model = self.load()
        return model(
            str(image_path),
            imgsz=image_size,
            conf=confidence,
            device=os.getenv("YOLO_DEVICE", "cpu"),
            verbose=False,
        )


engine = YoloV8Engine()
