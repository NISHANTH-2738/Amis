"""Compatibility shim for old imports.

The production detector now lives in backend.services.hybrid_detector so the
backend service layer owns the hosted Roboflow integration. Existing ai_core
imports continue to work through this shim.
"""

from backend.services.hybrid_detector import hybrid_detect
