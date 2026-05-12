import argparse
import json
from pathlib import Path


def train_detector(data_yaml: str, project: str, name: str, epochs: int, imgsz: int, batch: int):
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Install ultralytics to train YOLOv5n: pip install ultralytics") from exc

    model = YOLO("yolov5n.pt")
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        workers=0,
        device="cpu",
        patience=15,
        project=project,
        name=name,
    )

    output_dir = Path(project) / name
    metrics = {
        "model": "yolov5n",
        "data": data_yaml,
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": batch,
        "device": "cpu",
        "results": str(results),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics_report.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Train FabriGuard YOLOv5n detector on CPU.")
    parser.add_argument("--data", default="ai_core/data/augmented/defect_dataset.yaml")
    parser.add_argument("--project", default="ai_core/models")
    parser.add_argument("--name", default="fabriguard_v1")
    parser.add_argument("--epochs", type=int, default=75)
    parser.add_argument("--imgsz", type=int, default=416)
    parser.add_argument("--batch", type=int, default=4)
    args = parser.parse_args()
    print(json.dumps(train_detector(args.data, args.project, args.name, args.epochs, args.imgsz, args.batch), indent=2))


if __name__ == "__main__":
    main()
