# ai-core/inference/mock_detector.py

import random
import time
from datetime import datetime

KNITWEAR_DEFECTS = [
    {"class": "drop_stitch",  "severity_weight": 0.7},
    {"class": "hole",         "severity_weight": 0.9},
    {"class": "needle_line",  "severity_weight": 0.6},
    {"class": "run_ladder",   "severity_weight": 0.8},
    {"class": "stain",        "severity_weight": 0.5},
    {"class": "pilling",      "severity_weight": 0.3},
    {"class": "tuck_fault",   "severity_weight": 0.4},
    {"class": "fly_yarn",     "severity_weight": 0.2},
]

def mock_detect(image_path: str = None) -> dict:
    """
    Pretends to be YOLOv8.
    Returns identical data structure to real model.
    Swap this function later — nothing else changes.
    """
    time.sleep(0.1)  # simulate inference time

    # 70% chance product is normal
    if random.random() < 0.70:
        return {
            "status":     "PASS",
            "defects":    [],
            "inference_ms": 110,
            "timestamp":  datetime.now().isoformat(),
            "image_path": image_path,
            "source":     "mock"
        }

    # 30% chance — pick a defect
    defect = random.choice(KNITWEAR_DEFECTS)
    confidence = round(random.uniform(0.60, 0.97), 2)

    return {
        "status": "FAIL",
        "defects": [{
            "class":      defect["class"],
            "confidence": confidence,
            "bbox": {
                "x":      round(random.uniform(0.1, 0.8), 3),
                "y":      round(random.uniform(0.1, 0.8), 3),
                "width":  round(random.uniform(0.05, 0.3), 3),
                "height": round(random.uniform(0.05, 0.3), 3),
            },
            "severity_weight": defect["severity_weight"]
        }],
        "inference_ms": 110,
        "timestamp":    datetime.now().isoformat(),
        "image_path":   image_path,
        "source":       "mock"
    }