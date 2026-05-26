from __future__ import annotations

import hashlib
import logging
import os
import tempfile
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from PIL import Image

load_dotenv()

LOGGER = logging.getLogger(__name__)

ROBOFLOW_API_URL = os.getenv(
    "ROBOFLOW_API_URL",
    "https://serverless.roboflow.com",
)

ROBOFLOW_API_KEY = os.getenv(
    "ROBOFLOW_API_KEY"
)

ROBOFLOW_WORKSPACE_NAME = os.getenv(
    "ROBOFLOW_WORKSPACE_NAME"
)

ROBOFLOW_WORKFLOW_ID = os.getenv(
    "ROBOFLOW_WORKFLOW_ID"
)

ROBOFLOW_WORKFLOW_IMAGE_KEY = os.getenv(
    "ROBOFLOW_WORKFLOW_IMAGE_KEY",
    "image",
)

ROBOFLOW_TIMEOUT_SECONDS = float(
    os.getenv(
        "ROBOFLOW_TIMEOUT_SECONDS",
        "45",
    )
)

ROBOFLOW_RETRIES = int(
    os.getenv(
        "ROBOFLOW_RETRIES",
        "2",
    )
)

ROBOFLOW_CONFIDENCE_THRESHOLD = float(
    os.getenv(
        "ROBOFLOW_CONFIDENCE_THRESHOLD",
        "0.50",
    )
)

ROBOFLOW_MAX_IMAGE_SIZE = int(
    os.getenv(
        "ROBOFLOW_MAX_IMAGE_SIZE",
        "640",
    )
)

ROBOFLOW_JPEG_QUALITY = int(
    os.getenv(
        "ROBOFLOW_JPEG_QUALITY",
        "72",
    )
)

ROBOFLOW_CACHE_SIZE = int(
    os.getenv(
        "ROBOFLOW_CACHE_SIZE",
        "128",
    )
)

NON_DEFECT_CLASSES = {
    "normal",
    "pass",
    "ok",
    "good",
    "no_defect",
    "no defect",
    "background",
}

_client = None

_cache: OrderedDict[
    str,
    list[dict[str, Any]]
] = OrderedDict()

_executor: ThreadPoolExecutor | None = None


@dataclass(frozen=True)
class PreparedImage:
    path: str
    original_width: int
    original_height: int
    sent_width: int
    sent_height: int


def _get_client():
    global _client

    if _client is not None:
        return _client

    if (
        not ROBOFLOW_API_KEY
        or not ROBOFLOW_WORKSPACE_NAME
        or not ROBOFLOW_WORKFLOW_ID
    ):
        LOGGER.warning(
            "Roboflow configuration missing."
        )
        return None

    try:
        from inference_sdk import (
            InferenceHTTPClient,
        )
    except ImportError:
        LOGGER.warning(
            "Install inference-sdk"
        )
        return None

    _client = InferenceHTTPClient(
        api_url=ROBOFLOW_API_URL,
        api_key=ROBOFLOW_API_KEY,
    )

    return _client


def _get_executor():
    global _executor

    if _executor is None:
        _executor = ThreadPoolExecutor(
            max_workers=2,
        )

    return _executor


def _file_hash(path: str):
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _cache_key(image_path: str):
    return "|".join(
        [
            _file_hash(image_path),
            ROBOFLOW_WORKSPACE_NAME or "",
            ROBOFLOW_WORKFLOW_ID or "",
            str(ROBOFLOW_CONFIDENCE_THRESHOLD),
            str(ROBOFLOW_MAX_IMAGE_SIZE),
            str(ROBOFLOW_JPEG_QUALITY),
        ]
    )


def _cache_get(key):
    cached = _cache.get(key)

    if cached is None:
        return None

    _cache.move_to_end(key)

    return cached.copy()


def _cache_set(key, result):
    _cache[key] = result.copy()

    _cache.move_to_end(key)

    while len(_cache) > ROBOFLOW_CACHE_SIZE:
        _cache.popitem(last=False)


def _prepare_image(image_path: str):
    source = Path(image_path)

    if not source.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    with Image.open(source) as image:
        image = image.convert("RGB")

        original_width, original_height = (
            image.size
        )

        image.thumbnail(
            (
                ROBOFLOW_MAX_IMAGE_SIZE,
                ROBOFLOW_MAX_IMAGE_SIZE,
            ),
            Image.Resampling.LANCZOS,
        )

        sent_width, sent_height = image.size

        temp_file = tempfile.NamedTemporaryFile(
            prefix="fabriguard_rf_",
            suffix=".jpg",
            delete=False,
        )

        temp_file.close()

        image.save(
            temp_file.name,
            format="JPEG",
            quality=ROBOFLOW_JPEG_QUALITY,
            optimize=True,
        )

    return PreparedImage(
        path=temp_file.name,
        original_width=original_width,
        original_height=original_height,
        sent_width=sent_width,
        sent_height=sent_height,
    )


def _scale_bbox(prediction, prepared):
    x = float(prediction.get("x", 0))
    y = float(prediction.get("y", 0))

    width = float(
        prediction.get("width", 0)
    )

    height = float(
        prediction.get("height", 0)
    )

    x1 = max(0, x - width / 2)
    y1 = max(0, y - height / 2)

    x2 = min(
        prepared.sent_width,
        x + width / 2,
    )

    y2 = min(
        prepared.sent_height,
        y + height / 2,
    )

    scale_x = (
        prepared.original_width
        / prepared.sent_width
    )

    scale_y = (
        prepared.original_height
        / prepared.sent_height
    )

    return [
        round(x1 * scale_x, 2),
        round(y1 * scale_y, 2),
        round(x2 * scale_x, 2),
        round(y2 * scale_y, 2),
    ]


def _scale_bbox_list(bbox, prepared):
    if not isinstance(bbox, list) or len(bbox) != 4:
        return bbox

    try:
        x1, y1, x2, y2 = [float(value) for value in bbox]
    except (TypeError, ValueError):
        return bbox

    scale_x = prepared.original_width / prepared.sent_width
    scale_y = prepared.original_height / prepared.sent_height

    return [
        round(max(0, x1) * scale_x, 2),
        round(max(0, y1) * scale_y, 2),
        round(min(prepared.sent_width, x2) * scale_x, 2),
        round(min(prepared.sent_height, y2) * scale_y, 2),
    ]


def _collect_predictions(result):
    if isinstance(result, list):
        predictions = []

        for item in result:
            predictions.extend(
                _collect_predictions(item)
            )

        return predictions

    if not isinstance(result, dict):
        return []

    direct = result.get("predictions")

    if isinstance(direct, list):
        return direct

    predictions = []

    for value in result.values():
        if isinstance(value, (dict, list)):
            predictions.extend(
                _collect_predictions(value)
            )

    return predictions


def _standardize_predictions(
    result,
    prepared,
):
    predictions = _collect_predictions(
        result
    )

    detections = []

    for prediction in predictions:
        defect_class = str(
            prediction.get(
                "class",
                prediction.get("class_name", "unknown"),
            )
        ).strip()

        if (
            defect_class.lower()
            in NON_DEFECT_CLASSES
        ):
            continue

        confidence = float(
            prediction.get(
                "confidence",
                prediction.get("score", 0),
            )
        )

        if (
            confidence
            < ROBOFLOW_CONFIDENCE_THRESHOLD
        ):
            continue

        width = float(
            prediction.get("width", 0)
        )

        height = float(
            prediction.get("height", 0)
        )

        if width <= 1 or height <= 1:
            continue

        detections.append(
            {
                "class": defect_class,
                "confidence": round(
                    confidence,
                    4,
                ),
                "bbox": _scale_bbox(
                    prediction,
                    prepared,
                ),
            }
        )

    return detections


def parse_workflow_result(raw_output: dict) -> dict:
    """
    Parse the new industrial QC workflow outputs.
    Workflow now returns 5 structured outputs.
    """
    quality_status = raw_output.get(
        "quality_status", "PASS"
    ).upper().strip()

    filtered = raw_output.get(
        "filtered_predictions", []
    ) or raw_output.get("predictions", [])

    defect_count = int(
        raw_output.get("defect_count", 0) or 0
    )

    csv_log = raw_output.get("csv_log", "")

    detections = []
    predictions = (
        filtered
        if isinstance(filtered, list)
        else filtered.get("predictions", [])
    )

    for pred in predictions:
        if not isinstance(pred, dict):
            continue

        label = str(
            pred.get("class", pred.get("label", ""))
        ).lower().strip()

        if label in NON_DEFECT_CLASSES:
            continue

        confidence = float(
            pred.get("confidence", pred.get("score", 0))
        )

        if "bbox" in pred:
            bbox = pred["bbox"]
        else:
            x = float(pred.get("x", 0))
            y = float(pred.get("y", 0))
            w = float(pred.get("width", 0))
            h = float(pred.get("height", 0))
            bbox = [x - w / 2, y - h / 2, x + w / 2, y + h / 2]

        detections.append(
            {
                "class": label,
                "confidence": round(confidence, 3),
                "bbox": bbox,
            }
        )

    return {
        "status": quality_status,
        "defects": detections,
        "defect_count": defect_count,
        "csv_log": csv_log,
        "source": "roboflow_workflow",
    }


def _scale_workflow_result(parsed: dict, prepared: PreparedImage) -> dict:
    scaled = parsed.copy()
    scaled["defects"] = [
        {
            **defect,
            "bbox": _scale_bbox_list(defect.get("bbox"), prepared),
        }
        for defect in parsed.get("defects", [])
    ]
    return scaled


def _run_workflow(
    client,
    prepared_path,
):
    return client.run_workflow(
        workspace_name=ROBOFLOW_WORKSPACE_NAME,
        workflow_id=ROBOFLOW_WORKFLOW_ID,
        images={
            ROBOFLOW_WORKFLOW_IMAGE_KEY:
            prepared_path
        },
        use_cache=True,
    )


def detect_defects(image_path: str):
    started = time.perf_counter()

    client = _get_client()

    if client is None:
        return []

    try:
        key = _cache_key(image_path)

        cached = _cache_get(key)

        if cached is not None:
            return cached

        prepared = _prepare_image(
            image_path
        )

        try:
            last_error = None

            for attempt in range(
                ROBOFLOW_RETRIES + 1
            ):
                try:
                    future = (
                        _get_executor().submit(
                            _run_workflow,
                            client,
                            prepared.path,
                        )
                    )

                    result = future.result(
                        timeout=ROBOFLOW_TIMEOUT_SECONDS
                    )

                    LOGGER.debug(
                        "Roboflow raw result: %s",
                        result,
                    )

                    if isinstance(result, dict):
                        parsed = _scale_workflow_result(
                            parse_workflow_result(result),
                            prepared,
                        )
                    else:
                        detections = _standardize_predictions(
                            result,
                            prepared,
                        )
                        parsed = {
                            "status": "FAIL" if detections else "PASS",
                            "defects": detections,
                            "defect_count": len(detections),
                            "csv_log": "",
                            "source": "roboflow_legacy",
                        }

                    if not parsed.get("defects"):
                        detections = _standardize_predictions(
                            result,
                            prepared,
                        )
                        parsed["defects"] = detections
                        parsed["defect_count"] = (
                            parsed.get("defect_count")
                            or len(detections)
                        )

                    _cache_set(
                        key,
                        parsed,
                    )

                    LOGGER.info(
                        "Inference completed in %.0fms",
                        (
                            time.perf_counter()
                            - started
                        )
                        * 1000,
                    )

                    return parsed

                except Exception as exc:
                    last_error = exc

                    LOGGER.warning(
                        "Retry %s failed: %s",
                        attempt + 1,
                        exc,
                    )

                    time.sleep(
                        0.5 * (attempt + 1)
                    )

            raise (
                last_error
                or RuntimeError(
                    "Inference failed"
                )
            )

        finally:
            try:
                os.unlink(prepared.path)
            except OSError:
                pass

    except TimeoutError:
        LOGGER.warning(
            "Inference timeout"
        )

    except Exception as exc:
        LOGGER.warning(
            "Roboflow inference failed: %s",
            exc,
        )

    return {
        "status": "PASS",
        "defects": [],
        "defect_count": 0,
        "csv_log": "",
        "source": "roboflow_unavailable",
    }
