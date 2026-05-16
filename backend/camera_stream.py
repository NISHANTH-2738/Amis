"""Low-resource webcam ingestion loop for FabriGuard.

The camera process is intentionally separate from the FastAPI server. It reads
frames with OpenCV, keeps only every Nth frame, JPEG-compresses that frame, and
posts it to the existing `/inspect/frame` endpoint. That endpoint runs the
normal pipeline:

camera -> roboflow_service.py -> hosted Roboflow inference -> hybrid_detector.py
-> inspection_pipeline.py -> FastAPI websocket broadcast -> frontend dashboard
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path

import cv2
import requests
from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger(__name__)

API_FRAME_URL = os.getenv("FABRIGUARD_FRAME_URL", "http://127.0.0.1:8000/inspect/frame")
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
CAMERA_POLL_INTERVAL_MS = int(os.getenv("CAMERA_POLL_INTERVAL_MS", "500"))
CAMERA_PROCESS_EVERY_NTH_FRAME = int(os.getenv("CAMERA_PROCESS_EVERY_NTH_FRAME", "5"))
CAMERA_FRAME_WIDTH = int(os.getenv("CAMERA_FRAME_WIDTH", "640"))
CAMERA_JPEG_QUALITY = int(os.getenv("CAMERA_JPEG_QUALITY", "70"))
CAMERA_REQUEST_TIMEOUT_SECONDS = float(os.getenv("CAMERA_REQUEST_TIMEOUT_SECONDS", "15"))


def _save_frame(frame) -> str:
    """Write a compressed temporary JPEG that the API can process cheaply."""
    height, width = frame.shape[:2]
    if width > CAMERA_FRAME_WIDTH:
        ratio = CAMERA_FRAME_WIDTH / float(width)
        frame = cv2.resize(frame, (CAMERA_FRAME_WIDTH, int(height * ratio)), interpolation=cv2.INTER_AREA)

    temp_file = tempfile.NamedTemporaryFile(prefix="fabriguard_frame_", suffix=".jpg", delete=False)
    temp_file.close()
    cv2.imwrite(temp_file.name, frame, [int(cv2.IMWRITE_JPEG_QUALITY), CAMERA_JPEG_QUALITY])
    return temp_file.name


def _submit_frame(frame_path: str) -> None:
    """Use the existing API so websocket event shape stays exactly the same."""
    with open(frame_path, "rb") as frame_file:
        response = requests.post(
            API_FRAME_URL,
            files={"file": (Path(frame_path).name, frame_file, "image/jpeg")},
            timeout=CAMERA_REQUEST_TIMEOUT_SECONDS,
        )
    response.raise_for_status()
    data = response.json()
    LOGGER.info(
        "Frame inspected: status=%s severity=%s defects=%s",
        data.get("status"),
        data.get("severity", {}).get("name"),
        len(data.get("defects", [])),
    )


def run_camera_stream() -> None:
    """Capture webcam frames and feed the existing realtime inspection system."""
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    capture = cv2.VideoCapture(CAMERA_INDEX)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open camera index {CAMERA_INDEX}")

    frame_number = 0
    LOGGER.info("Camera stream started: index=%s endpoint=%s", CAMERA_INDEX, API_FRAME_URL)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                LOGGER.warning("Camera read failed; retrying")
                time.sleep(CAMERA_POLL_INTERVAL_MS / 1000)
                continue

            frame_number += 1
            if frame_number % CAMERA_PROCESS_EVERY_NTH_FRAME != 0:
                time.sleep(CAMERA_POLL_INTERVAL_MS / 1000)
                continue

            frame_path = _save_frame(frame)
            try:
                _submit_frame(frame_path)
            except Exception as exc:
                LOGGER.warning("Frame submission failed: %s", exc)
            finally:
                try:
                    os.unlink(frame_path)
                except OSError:
                    pass

            time.sleep(CAMERA_POLL_INTERVAL_MS / 1000)
    except KeyboardInterrupt:
        LOGGER.info("Camera stream stopped")
    finally:
        capture.release()


if __name__ == "__main__":
    run_camera_stream()
