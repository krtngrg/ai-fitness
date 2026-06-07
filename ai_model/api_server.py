"""
api_server.py — FastAPI local AI service (port 9001).

Run with:
  cd movemate_mvp0_ai_engine
  uvicorn ai_model.api_server:app --host 127.0.0.1 --port 9001 --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="MoveMate AI Camera Service", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartWorkoutRequest(BaseModel):
    session_id: str
    exercise_slug: str
    planned_sets: Optional[int] = None
    planned_reps: Optional[int] = None
    planned_duration_seconds: Optional[int] = None
    roadmap_day_exercise_id: Optional[str] = None
    backend_callback_url: Optional[str] = None
    access_token: Optional[str] = None


SUPPORTED_SLUGS = {"squat", "push_up", "jumping_jack", "plank", "lunge", "lunges"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "MoveMate AI Camera Service"}


@app.post("/ai/start-workout")
def start_workout(req: StartWorkoutRequest):
    if req.exercise_slug not in SUPPORTED_SLUGS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported exercise_slug '{req.exercise_slug}'. Supported: {sorted(SUPPORTED_SLUGS)}",
        )

    # Import here so FastAPI starts even if cv2/mediapipe isn't loaded yet
    import sys, os
    _here = os.path.dirname(os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)

    from workout_runner import run_ai_workout

    try:
        result = run_ai_workout(
            session_id=req.session_id,
            exercise_slug=req.exercise_slug,
            planned_reps=req.planned_reps,
            planned_sets=req.planned_sets,
            planned_duration_seconds=req.planned_duration_seconds,
            roadmap_day_exercise_id=req.roadmap_day_exercise_id,
            backend_callback_url=req.backend_callback_url,
            access_token=req.access_token,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    saved = req.backend_callback_url is not None

    return {
        "message": "AI workout completed",
        "saved_to_backend": saved,
        "result": result,
    }
