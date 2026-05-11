# ai_core/inference/patchcore_detector.py

class PatchCoreDetector:
    def __init__(self):
        self.product_name = None
        self.status = "not_setup"
    
    def setup_product(self, product_name, image_paths):
        self.product_name = product_name
        self.status = "ready"
        return {
            "status": "ready",
            "images_used": len(image_paths),
            "product_name": product_name
        }
    
    def get_status(self):
        return {
            "product_name": self.product_name,
            "status": self.status
        }
    
    def inspect(self, image_path):
        # Mock inspection
        import random
        if random.random() < 0.7:
            return {
                "status": "PASS",
                "defects": [],
                "inference_ms": 150
            }
        else:
            return {
                "status": "FAIL",
                "defects": [{"confidence": round(random.uniform(0.6, 0.95), 2)}],
                "inference_ms": 150
            }

patchcore = PatchCoreDetector()