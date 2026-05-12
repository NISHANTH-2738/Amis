import argparse
import shutil
from pathlib import Path

import cv2


def _image_files(root: Path):
    return sorted(p for p in root.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})


def _augment_image(image, index: int):
    if index == 0:
        return image
    if index == 1:
        return cv2.flip(image, 1)
    if index == 2:
        return cv2.flip(image, 0)
    if index == 3:
        return cv2.convertScaleAbs(image, alpha=1.12, beta=12)
    blurred = cv2.GaussianBlur(image, (3, 3), 0)
    return cv2.convertScaleAbs(blurred, alpha=0.95, beta=-5)


def augment_dataset(processed_root: Path, augmented_root: Path, factor: int = 5):
    train_images = processed_root / "images" / "train"
    train_labels = processed_root / "labels" / "train"
    val_images = processed_root / "images" / "val"
    val_labels = processed_root / "labels" / "val"

    for split in ["train", "val"]:
        (augmented_root / "images" / split).mkdir(parents=True, exist_ok=True)
        (augmented_root / "labels" / split).mkdir(parents=True, exist_ok=True)

    count = 0
    for image_path in _image_files(train_images):
        image = cv2.imread(str(image_path))
        if image is None:
            continue
        label_path = train_labels / f"{image_path.stem}.txt"
        label_text = label_path.read_text(encoding="utf-8") if label_path.exists() else ""
        for idx in range(factor):
            suffix = f"_aug{idx}"
            out_image = augmented_root / "images" / "train" / f"{image_path.stem}{suffix}.jpg"
            out_label = augmented_root / "labels" / "train" / f"{image_path.stem}{suffix}.txt"
            cv2.imwrite(str(out_image), _augment_image(image, idx))
            out_label.write_text(label_text, encoding="utf-8")
            count += 1

    val_count = 0
    for image_path in _image_files(val_images):
        shutil.copy2(image_path, augmented_root / "images" / "val" / image_path.name)
        label_path = val_labels / f"{image_path.stem}.txt"
        if label_path.exists():
            shutil.copy2(label_path, augmented_root / "labels" / "val" / label_path.name)
        val_count += 1

    yaml_src = processed_root / "defect_dataset.yaml"
    yaml_dest = augmented_root / "defect_dataset.yaml"
    if yaml_src.exists():
        text = yaml_src.read_text(encoding="utf-8")
        text = text.replace(str(processed_root).replace("\\", "/"), str(augmented_root).replace("\\", "/"))
        yaml_dest.write_text(text, encoding="utf-8")
    return {"augmented_train_images": count, "validation_images": val_count}


def main():
    parser = argparse.ArgumentParser(description="Create FabriGuard training-only augmentations.")
    parser.add_argument("--processed-root", default="ai_core/data/processed")
    parser.add_argument("--augmented-root", default="ai_core/data/augmented")
    parser.add_argument("--factor", type=int, default=5)
    args = parser.parse_args()
    print(augment_dataset(Path(args.processed_root), Path(args.augmented_root), args.factor))


if __name__ == "__main__":
    main()
