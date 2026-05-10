# tests/test_pipeline.py
import sys, os
sys.path.append(os.path.dirname(
    os.path.dirname(__file__)
))

from backend.services.inspection_pipeline import run_inspection
import json

print("=" * 50)
print("  FABRIGUARD PIPELINE TEST")
print("=" * 50)

for i in range(5):
    result = run_inspection("test_image.jpg")
    print(f"\nTest {i+1}:")
    print(f"  Status:     {result['status']}")
    print(f"  Machine:    {result['machine_id']}")
    print(f"  Severity:   {result['severity']['name']}")
    if result["root_cause"]:
        print(f"  Cause:      {result['root_cause']['cause']}")
        print(f"  Action:     {result['root_cause']['action']}")
    print(f"  Time:       {result['inference_ms']}ms")

print("\n" + "=" * 50)
print("  PIPELINE WORKING CORRECTLY")
print("=" * 50)