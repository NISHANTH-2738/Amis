from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


InspectionStatus = Literal["PASS", "FAIL"]


class DefectBox(BaseModel):
    class_: str = Field(alias="class")
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[float] = Field(min_length=4, max_length=4)

    model_config = {
        "populate_by_name": True,
    }


class Severity(BaseModel):
    name: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    score: float = Field(ge=0.0, le=1.0)
    level: int = Field(ge=1, le=4)
    action: str


class DetectionResponse(BaseModel):
    status: InspectionStatus
    timestamp: str
    defect_count: int = Field(ge=0)
    inference_ms: int = Field(ge=0)
    severity: Severity
    defects: list[DefectBox]


class InspectionEvent(BaseModel):
    type: Literal["inspection"] = "inspection"
    payload: DetectionResponse


class AlertEvent(BaseModel):
    type: Literal["alert"] = "alert"
    payload: dict
