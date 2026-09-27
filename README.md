# 🚦 AI Traffic Intelligence & Road Safety System

A production-style traffic monitoring project built around YOLOv8,
ByteTrack, FastAPI, SQLite, and a future React dashboard.

## Repository structure

```text
AI_Traffic_Intelligence_Road_Safety/
├── training/
│   ├── AI_Traffic_Intelligence_Road_Safety.ipynb
│   └── README.md
│
├── detection/
│   ├── __init__.py
│   └── analytics.py
│
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── requirements.txt
│   └── .gitignore
│
├── .gitignore
└── README.md
```

## Current status

1. YOLOv8 training completed.
2. ByteTrack tracking tested.
3. Vehicle counting completed.
4. Relative speed calculated in pixels/frame.
5. Traffic presence analysis completed.
6. Direction analysis completed.
7. Reliable-track filtering completed.
8. FastAPI + SQLite backend created and tested.
9. Next: connect local YOLO/ByteTrack processing to FastAPI.
10. After that: React dashboard.

## Important

The dataset, trained weights, and large video files are intentionally NOT
included in this repository.

Speed is currently measured in pixels/frame. Real-world km/h requires
camera calibration or homography.

SQLite is built into Python; no separate SQLite server is required.

## Backend setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```
