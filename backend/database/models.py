# backend/database/models.py
from sqlalchemy import (
    Column, String, Float, Integer,
    Boolean, DateTime, JSON, Text
)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Inspection(Base):
    __tablename__ = "inspections"

    id            = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(String, unique=True, index=True)
    timestamp     = Column(DateTime, default=datetime.now)
    machine_id    = Column(String, index=True)
    status        = Column(String)        # PASS / FAIL
    defect_class  = Column(String, nullable=True)
    confidence    = Column(Float,  nullable=True)
    severity_level= Column(Integer, nullable=True)
    severity_name = Column(String, nullable=True)
    root_cause    = Column(Text,   nullable=True)
    action        = Column(String, nullable=True)
    bbox          = Column(JSON,   nullable=True)
    inference_ms  = Column(Integer)
    model_source  = Column(String, default="mock")
    overridden    = Column(Boolean, default=False)
    override_note = Column(String, nullable=True)

class Alert(Base):
    __tablename__ = "alerts"

    id            = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(String, index=True)
    timestamp     = Column(DateTime, default=datetime.now)
    machine_id    = Column(String)
    alert_level   = Column(Integer)
    alert_name    = Column(String)
    defect_class  = Column(String)
    message       = Column(Text)
    acknowledged  = Column(Boolean, default=False)

class MachineState(Base):
    __tablename__ = "machine_states"

    id             = Column(Integer, primary_key=True)
    machine_id     = Column(String, unique=True, index=True)
    tool_age_days  = Column(Float)
    vibration      = Column(Float)
    tension_kn     = Column(Float)
    temperature_c  = Column(Float)
    last_updated   = Column(DateTime, default=datetime.now)