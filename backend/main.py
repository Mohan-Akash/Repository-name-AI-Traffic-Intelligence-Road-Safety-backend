from fastapi import Depends, FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from pathlib import Path
from threading import Thread
import shutil
import uuid

from .database import Base, engine, get_db
from .models import VehicleEvent
from .schemas import VehicleEventCreate, VehicleEventResponse

from detection.detction import process_video

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Traffic Intelligence API",
    description="Backend API for traffic monitoring and vehicle analytics",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# UPLOAD_DIR = PROJECT_ROOT / "uploads"
# UPLOAD_DIR.mkdir(exist_ok=True)

UPLOAD_DIR = PROJECT_ROOT / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
video_jobs = {}

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm"
}

def process_uploaded_video(
    job_id: str,
    video_path: Path,
    output_path: Path
):
    try:

        video_jobs[job_id] = {
            "status": "processing",
            "progress": 0,
            "current_frame": 0,
            "total_frames": 0
        }

        print(
            f"Starting processing: {video_path}"
        )

        # ---------------------------------------------
        # REAL-TIME PROGRESS CALLBACK
        # ---------------------------------------------

        def update_progress(
            progress,
            current_frame,
            total_frames
        ):
            video_jobs[job_id] = {
                "status": "processing",
                "progress": progress,
                "current_frame": current_frame,
                "total_frames": total_frames
            }

        # ---------------------------------------------
        # PROCESS VIDEO
        # ---------------------------------------------

        result = process_video(
            video_path=video_path,
            output_video=output_path,
            progress_callback=update_progress
        )

        # ---------------------------------------------
        # COMPLETED
        # ---------------------------------------------

        video_jobs[job_id] = {
            "status": "completed",
            "progress": 100,
            "current_frame": result.get(
                "frame_count",
                0
            ),
            "total_frames": result.get(
                "frame_count",
                0
            ),
            "result": result
        }

        print(
            f"Processing completed: {video_path}"
        )

    except Exception as e:

        video_jobs[job_id] = {
            "status": "failed",
            "progress": 0,
            "error": str(e)
        }

        print(
            f"Video processing error: {e}"
        )

@app.get("/")
def root():
    return {"message": "AI Traffic Intelligence API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/vehicles", response_model=VehicleEventResponse)
def create_vehicle_event(
    event: VehicleEventCreate,
    db: Session = Depends(get_db),
):
    vehicle = VehicleEvent(**event.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@app.get("/vehicles")
def get_vehicle_events(db: Session = Depends(get_db)):
    return (
        db.query(VehicleEvent)
        .order_by(VehicleEvent.timestamp.desc())
        .all()
    )


@app.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)):
    total_vehicles = db.query(VehicleEvent).count()

    total_cars = (
        db.query(VehicleEvent)
        .filter(VehicleEvent.vehicle_type == "car")
        .count()
    )

    total_buses = (
        db.query(VehicleEvent)
        .filter(VehicleEvent.vehicle_type == "bus")
        .count()
    )

    total_vans = (
        db.query(VehicleEvent)
        .filter(VehicleEvent.vehicle_type == "van")
        .count()
    )

    average_speed = (
        db.query(func.avg(VehicleEvent.speed_px_frame))
        .scalar()
    )

    return {
        "total_vehicles": total_vehicles,
        "vehicle_types": {
            "cars": total_cars,
            "buses": total_buses,
            "vans": total_vans
        },
        "average_speed_px_frame": round(average_speed or 0, 2)
    }

@app.get("/analytics/vehicle-types")
def vehicle_type_analytics(db: Session = Depends(get_db)):
    vehicle_types = (
        db.query(
            VehicleEvent.vehicle_type,
            func.count(VehicleEvent.id)
        )
        .group_by(VehicleEvent.vehicle_type)
        .all()
    )

    return {
        vehicle_type: count
        for vehicle_type, count in vehicle_types
    }

@app.get("/analytics/directions")
def direction_analytics(db: Session = Depends(get_db)):
    directions = (
        db.query(
            VehicleEvent.direction,
            func.count(VehicleEvent.id)
        )
        .group_by(VehicleEvent.direction)
        .all()
    )

    return {
        direction: count
        for direction, count in directions
    }

@app.get("/analytics/speed")
def speed_analytics(db: Session = Depends(get_db)):
    average_speed = (
        db.query(func.avg(VehicleEvent.speed_px_frame))
        .scalar()
    )

    maximum_speed = (
        db.query(func.max(VehicleEvent.speed_px_frame))
        .scalar()
    )

    minimum_speed = (
        db.query(func.min(VehicleEvent.speed_px_frame))
        .scalar()
    )

    return {
        "average_speed_px_frame": round(average_speed or 0, 2),
        "maximum_speed_px_frame": round(maximum_speed or 0, 2),
        "minimum_speed_px_frame": round(minimum_speed or 0, 2)
    }

@app.get("/analytics/timeline")
def traffic_timeline(db: Session = Depends(get_db)):
    events = (
        db.query(VehicleEvent)
        .order_by(VehicleEvent.timestamp)
        .all()
    )

    timeline = {}

    for event in events:
        time_key = event.timestamp.strftime("%H:%M")

        if time_key not in timeline:
            timeline[time_key] = 0

        timeline[time_key] += 1

    return [
        {
            "time": time,
            "vehicle_count": count
        }
        for time, count in sorted(timeline.items())
    ]

@app.post("/videos/upload")
async def upload_video(
    file: UploadFile = File(...)
):

    allowed_extensions = {
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".webm"
    }

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported video format"
        )

    job_id = str(uuid.uuid4())

    input_path = (
        UPLOAD_DIR /
        f"{job_id}{extension}"
    )

    output_path = (
        OUTPUT_DIR /
        f"{job_id}_processed.mp4"
    )

    # Save uploaded video
    with open(input_path, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    # Run processing in background
    # Create initial job status
    video_jobs[job_id] = {
        "status": "queued",
        "progress": 0
    }

    # Run processing in background
    thread = Thread(
        target=process_uploaded_video,
        args=(
            job_id,
            input_path,
            output_path
        ),
        daemon=True
    )

    thread.start()

    return {
        "job_id": job_id,
        "filename": file.filename,
        "status": "processing",
        "message": "Video uploaded and processing started"
    }

@app.get("/videos/{job_id}/status")
def video_status(job_id: str):

    job = video_jobs.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    response = {
        "job_id": job_id,
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "current_frame": job.get("current_frame", 0),
        "total_frames": job.get("total_frames", 0)
    }

    if job.get("status") == "completed":

        response["result"] = job.get(
            "result",
            {}
        )

        response["video_url"] = (
            f"/videos/{job_id}/processed"
        )

    if job.get("status") == "failed":

        response["error"] = job.get(
            "error",
            "Unknown processing error"
        )

    return response

@app.get("/videos/{job_id}/processed")
def get_processed_video(job_id: str):
    output_path = OUTPUT_DIR / f"{job_id}_processed.mp4"

    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Processed video not found"
        )

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=output_path.name
    )