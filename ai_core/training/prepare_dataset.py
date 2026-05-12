import argparse
import json
import random
import shutil
from pathlib import Path

import cv2


DEFAULT_CLASSES = [
    "hole",
    "stain",
    "drop_stitch",
    "needle_line",
    "run_ladder",
    "pilling",
    "tuck_fault",
    "fly_yarn",
]


def _image_files(root: Path):
    suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    return sorted(p for p in root.rglob("*") if p.suffix.lower() in suffixes)


def _read_image(path: Path):
    image = cv2.imread(str(path))
    if image is None or image.size == 0:
        raise ValueError(f"Unreadable image: {path}")
    return image


def _mask_to_yolo(mask_path: Path, class_id: int, image_width: int, image_height: int):
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if mask is None or mask.size == 0:
        return []

    _, binary = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    labels = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w <= 1 or h <= 1:
            continue
        x_center = (x + w / 2) / image_width
        y_center = (y + h / 2) / image_height
        labels.append(
            f"{class_id} {x_center:.6f} {y_center:.6f} "
            f"{w / image_width:.6f} {h / image_height:.6f}"
        )
    return labels


def _find_mask(mask_root: Path, image_path: Path):
    candidates = [
        mask_root / image_path.name,
        mask_root / f"{image_path.stem}.png",
        mask_root / f"{image_path.stem}_mask.png",
        mask_root / f"{image_path.stem}.bmp",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _write_yaml(path: Path, train_path: Path, val_path: Path, classes: list[str]):
    names = "\n".join(f"  {idx}: {name}" for idx, name in enumerate(classes))
    path.write_text(
        "path: .\n"
        f"train: {train_path.as_posix()}\n"
        f"val: {val_path.as_posix()}\n"
        f"nc: {len(classes)}\n"
        f"names:\n{names}\n",
        encoding="utf-8",
    )


def prepare_dataset(
    raw_root: Path,
    processed_root: Path,
    classes: list[str],
    image_size: int,
    val_ratio: float,
    seed: int,
):
    defect_root = raw_root / "Defect_images"
    clean_root = raw_root / "NODefect_images"
    mask_root = raw_root / "Mask_images"
    if not defect_root.exists() or not clean_root.exists() or not mask_root.exists():
        raise FileNotFoundError(
            "Expected AITEX layout with Defect_images, NODefect_images, and Mask_images"
        )

    class_map = {name: idx for idx, name in enumerate(classes)}
    class_id = class_map.get("hole", 0)
    samples = []
    rejected = []

    for image_path in _image_files(defect_root):
        try:
            image = _read_image(image_path)
            mask_path = _find_mask(mask_root, image_path)
            labels = []
            if mask_path:
                labels = _mask_to_yolo(mask_path, class_id, image.shape[1], image.shape[0])
            if not labels:
                rejected.append({"path": str(image_path), "reason": "missing_or_empty_mask"})
                continue
            samples.append((image_path, labels))
        except ValueError as exc:
            rejected.append({"path": str(image_path), "reason": str(exc)})

    for image_path in _image_files(clean_root):
        try:
            _read_image(image_path)
            samples.append((image_path, []))
        except ValueError as exc:
            rejected.append({"path": str(image_path), "reason": str(exc)})

    random.Random(seed).shuffle(samples)
    split_at = int(len(samples) * (1 - val_ratio))
    splits = {"train": samples[:split_at], "val": samples[split_at:]}

    for split_name, split_samples in splits.items():
        image_dir = processed_root / "images" / split_name
        label_dir = processed_root / "labels" / split_name
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)

        for source_path, labels in split_samples:
            image = _read_image(source_path)
            resized = cv2.resize(image, (image_size, image_size), interpolation=cv2.INTER_AREA)
            output_image = image_dir / f"{source_path.stem}.jpg"
            output_label = label_dir / f"{source_path.stem}.txt"
            cv2.imwrite(str(output_image), resized)
            output_label.write_text("\n".join(labels) + ("\n" if labels else ""), encoding="utf-8")

    label_map = {idx: name for idx, name in enumerate(classes)}
    processed_root.mkdir(parents=True, exist_ok=True)
    (processed_root / "label_map.json").write_text(
        json.dumps(label_map, indent=2),
        encoding="utf-8",
    )
    (processed_root / "preprocessing.json").write_text(
        json.dumps({"image_size": image_size, "normalize": "yolov5_default"}, indent=2),
        encoding="utf-8",
    )
    (processed_root / "rejected_files.json").write_text(
        json.dumps(rejected, indent=2),
        encoding="utf-8",
    )
    _write_yaml(
        processed_root / "defect_dataset.yaml",
        processed_root / "images" / "train",
        processed_root / "images" / "val",
        classes,
    )
    shutil.copyfile(processed_root / "defect_dataset.yaml", processed_root / "dataset.yaml")
    return {
        "samples": len(samples),
        "train": len(splits["train"]),
        "val": len(splits["val"]),
        "rejected": len(rejected),
        "label_map": label_map,
    }


def main():
    parser = argparse.ArgumentParser(description="Prepare AITEX data for FabriGuard YOLOv5n.")
    parser.add_argument("--raw-root", default="ai_core/data/raw/aitex")
    parser.add_argument("--processed-root", default="ai_core/data/processed")
    parser.add_argument("--imgsz", type=int, default=416)
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--classes", nargs="*", default=DEFAULT_CLASSES)
    args = parser.parse_args()

    summary = prepare_dataset(
        Path(args.raw_root),
        Path(args.processed_root),
        args.classes,
        args.imgsz,
        args.val_ratio,
        args.seed,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
