# backend/database/models.py
# backend/database/models.py

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    JSON,
    Text,
)

from datetime import datetime

# IMPORTANT:
# Use SAME Base from connection.py
from backend.database.connection import Base


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)

    inspection_id = Column(
        String,
        unique=True,
        index=True,
    )

    timestamp = Column(
        DateTime,
        default=datetime.now,
    )

    machine_id = Column(
        String,
        index=True,
    )

    status = Column(String)

    defect_class = Column(
        String,
        nullable=True,
    )

    confidence = Column(
        Float,
        nullable=True,
    )

    severity_level = Column(
        Integer,
        nullable=True,
    )

    severity_name = Column(
        String,
        nullable=True,
    )

    root_cause = Column(
        Text,
        nullable=True,
    )

    action = Column(
        Text,
        nullable=True,
    )

    bbox = Column(
        JSON,
        nullable=True,
    )

    inference_ms = Column(
        Float,
        nullable=True,
    )

    model_source = Column(
        String,
        nullable=True,
    )

    overridden = Column(
        Boolean,
        default=False,
    )

    override_note = Column(
        Text,
        nullable=True,
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)

    inspection_id = Column(
        String,
        index=True,
    )

    timestamp = Column(
        DateTime,
        default=datetime.now,
    )

    machine_id = Column(
        String,
        index=True,
    )

    alert_level = Column(Integer)

    alert_name = Column(String)

    defect_class = Column(
        String,
        nullable=True,
    )

    message = Column(Text)

    acknowledged = Column(
        Boolean,
        default=False,
    )


class MachineState(Base):
    __tablename__ = "machine_states"

    id = Column(Integer, primary_key=True, index=True)

    machine_id = Column(
        String,
        unique=True,
        index=True,
    )

    timestamp = Column(
        DateTime,
        default=datetime.now,
    )

    vibration = Column(
        Float,
        nullable=True,
    )

    tension_kn = Column(
        Float,
        nullable=True,
    )

    temperature_c = Column(
        Float,
        nullable=True,
    )

    tool_age_days = Column(
        Integer,
        nullable=True,
    )
