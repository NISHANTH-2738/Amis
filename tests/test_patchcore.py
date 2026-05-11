# tests/test_patchcore.py
import sys, os
sys.path.append(os.path.dirname(
    os.path.dirname(__file__)
))

import numpy as np
from PIL import Image
from ai_core.inference.patchcore_detector import (
    PatchCoreDetector
)

print("=" * 55)
print("  FABRIGUARD — PATCHCORE FEW-SHOT TEST")
print("=" * 55)

detector = PatchCoreDetector()

# Generate synthetic test images
# (replaces real product photos for testing)
os.makedirs("uploads/test_reference", exist_ok=True)
os.makedirs("uploads/test_inspect",   exist_ok=True)

print("\n[1] Generating synthetic reference images...")
ref_paths = []
for i in range(10):
    # Simulate good product — uniform texture
    img_array = np.ones((224, 224, 3),
                        dtype=np.uint8) * 180
    noise = np.random.randint(
        0, 15, (224, 224, 3), dtype=np.uint8
    )
    img_array = np.clip(
        img_array.astype(int) + noise, 0, 255
    ).astype(np.uint8)
    path = f"uploads/test_reference/good_{i}.png"
    Image.fromarray(img_array).save(path)
    ref_paths.append(path)
print(f"  Created {len(ref_paths)} reference images")

print("\n[2] Setting up product profile...")
result = detector.setup_product(
    "Test Knitwear Product", ref_paths
)
print(f"  Memory bank: {result['memory_patches']} patches")
print(f"  Status: {result['status']}")

print("\n[3] Inspecting GOOD product (should PASS)...")
good_img = np.ones(
    (224, 224, 3), dtype=np.uint8
) * 180
noise = np.random.randint(
    0, 15, (224, 224, 3), dtype=np.uint8
)
good_img = np.clip(
    good_img.astype(int) + noise, 0, 255
).astype(np.uint8)
good_path = "uploads/test_inspect/good_test.png"
Image.fromarray(good_img).save(good_path)
r1 = detector.inspect(good_path)
print(f"  Result: {r1['status']}")
print(f"  Score:  {r1.get('anomaly_score', 0):.4f}")

print("\n[4] Inspecting DEFECTIVE product (should FAIL)...")
bad_img = np.ones(
    (224, 224, 3), dtype=np.uint8
) * 180
# Add obvious defect — dark square region
bad_img[80:140, 80:140] = [20, 20, 20]
bad_path = "uploads/test_inspect/defect_test.png"
Image.fromarray(bad_img).save(bad_path)
r2 = detector.inspect(bad_path)
print(f"  Result: {r2['status']}")
if r2["defects"]:
    d = r2["defects"][0]
    print(f"  Score:  {d['anomaly_score']:.4f}")
    print(f"  Conf:   {d['confidence']}")
    print(f"  Loc:    x={d['bbox']['x']} "
          f"y={d['bbox']['y']}")

print("\n" + "=" * 55)
print(f"  GOOD image  → {r1['status']}")
print(f"  DEFECT image → {r2['status']}")
if r1["status"] == "PASS" and r2["status"] == "FAIL":
    print("  ✅ PATCHCORE WORKING CORRECTLY")
else:
    print("  ⚠️  Threshold may need adjustment")
print("=" * 55)
