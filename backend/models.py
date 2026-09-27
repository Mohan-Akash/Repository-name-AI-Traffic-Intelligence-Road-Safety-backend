from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from .database import Base


class VehicleEvent(Base):
    __tablename__ = "vehicle_events"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, index=True)
    vehicle_type = Column(String, index=True)
    direction = Column(String)
    speed_px_frame = Column(Float)
    camera_id = Column(String, default="camera_1")
    timestamp = Column(DateTime, default=datetime.utcnow)
