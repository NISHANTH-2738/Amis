import argparse
import json
from pathlib import Path


def export_model(weights: str):
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Install ultralytics to export YOLO weights: pip install ultralytics") from exc

    model = YOLO(weights)
    onnx_path = model.export(format="onnx")
    torchscript_path = model.export(format="torchscript")
    return {
        "weights": weights,
        "onnx": str(onnx_path),
        "torchscript": str(torchscript_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Export FabriGuard detector for edge inference.")
    parser.add_argument("--weights", default="ai_core/models/fabriguard_v1/weights/best.pt")
    args = parser.parse_args()
    if not Path(args.weights).exists():
        raise FileNotFoundError(f"Missing trained weights: {args.weights}")
    print(json.dumps(export_model(args.weights), indent=2))


if __name__ == "__main__":
    main()
