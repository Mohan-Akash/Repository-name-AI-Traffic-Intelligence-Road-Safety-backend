from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VehicleEventCreate(BaseModel):
    vehicle_id: int
    vehicle_type: str
    direction: str
    speed_px_frame: float
    camera_id: str = "camera_1"


class VehicleEventResponse(VehicleEventCreate):
    id: int
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True
