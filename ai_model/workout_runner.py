"""
workout_runner.py — programmatic wrapper around the MoveMate AI model.
Called by api_server.py (FastAPI) and can also be used from main.py CLI.
"""

import os
import sys
import time

# Allow imports from ai_model directory when called from outside
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import cv2
import mediapipe as mp
import numpy as np

from calorie_tracker import CalorieTracker
from config import CAMERA_INDEX, MODEL_PATH, WINDOW_NAME
from drawing import draw_info_panel, draw_pose
from exercise_logic import analyze_exercise
from pose_landmarker import create_pose_landmarker
from state import MoveMateState, reset_state

# Slug → display name used by exercise_logic
SLUG_TO_EXERCISE = {
    "squat": "Squat",
    "push_up": "Push-up",
    "jumping_jack": "Jumping Jack",
    "plank": "Plank",
    "lunge": "Lunge",
    "lunges": "Lunge",  # DB uses 'lunges' slug
}

CALORIES_PER_REP_FALLBACK = {
    "squat": 0.32,
    "push_up": 0.29,
    "sit_up": 0.25,
    "jumping_jack": 0.20,
    "lunge": 0.30,
}


def run_ai_workout(
    session_id: str,
    exercise_slug: str,
    planned_reps: int = None,
    planned_sets: int = None,
    planned_duration_seconds: int = None,
    roadmap_day_exercise_id: str = None,
    backend_callback_url: str = None,
    access_token: str = None,
) -> dict:
    """
    Open webcam, run pose detection for the given exercise.
    Stops when:
      - user presses 'q'
      - planned_reps reached
      - planned_duration_seconds reached

    Returns a JSON-compatible dict matching Django SaveAIWorkoutResult API.
    If backend_callback_url is provided, POSTs result to Django.
    """
    exercise_name = SLUG_TO_EXERCISE.get(exercise_slug)
    if not exercise_name:
        raise ValueError(f"Unsupported exercise slug: {exercise_slug}")

    model_path = os.path.join(_here, MODEL_PATH)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Check CAMERA_INDEX in config.py.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    state = reset_state(exercise_name)
    calorie_tracker = CalorieTracker()

    posture_events = []
    incorrect_reps_count = 0
    last_reps = 0
    start_time = time.time()
    calories_burned = 0.0

    # pose_landmarker.py uses a relative MODEL_PATH — must run from ai_model dir
    _orig_cwd = os.getcwd()
    os.chdir(_here)
    try:
        landmarker = create_pose_landmarker()
    except Exception as e:
        os.chdir(_orig_cwd)
        cap.release()
        raise RuntimeError(f"Could not load pose model: {e}")

    with landmarker:
        while True:
            elapsed = time.time() - start_time

            # Stop conditions
            if planned_duration_seconds and elapsed >= planned_duration_seconds:
                break
            if planned_reps and state.reps >= planned_reps:
                break

            success, frame = cap.read()
            if not success:
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame = np.ascontiguousarray(rgb_frame)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            timestamp_ms = int(elapsed * 1000)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            metrics = {}
            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                old_reps = state.reps
                metrics, state = analyze_exercise(landmarks, state)

                if exercise_slug == "plank":
                    calories_burned = calorie_tracker.update_plank(state.plank_seconds)
                else:
                    calories_burned = calorie_tracker.update_by_reps(
                        exercise_name=exercise_name, reps=state.reps
                    )

                # Track bad reps (form_score < 70 on new rep)
                if state.reps > old_reps and state.form_score < 70:
                    incorrect_reps_count += 1
                    posture_events.append({
                        "timestamp_seconds": round(elapsed, 3),
                        "issue_type": "poor_form",
                        "feedback": state.feedback,
                        "posture_score": state.form_score,
                        "landmark_data": {k: round(float(v), 2) for k, v in metrics.items()},
                    })

                draw_pose(frame, landmarks)
            else:
                state.feedback = "No person detected. Step into view."
                state.form_score = 0

            draw_info_panel(frame, state, metrics, calories_burned)

            # Overlay planned info
            cv2.putText(
                frame,
                f"Session: {session_id[:8]}...  Target: {planned_reps or planned_duration_seconds}",
                (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1,
            )

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
    os.chdir(_orig_cwd)

    total_duration = round(time.time() - start_time)
    actual_reps = state.reps
    correct_reps = max(0, actual_reps - incorrect_reps_count)
    posture_score = state.form_score if actual_reps > 0 else 0
    if actual_reps > 0 and incorrect_reps_count > 0:
        posture_score = max(0, 100 - incorrect_reps_count * 10)

    result_payload = {
        "model": {
            "model_name": "MoveMate Pose AI",
            "model_version": "1.0",
            "detector_type": f"{exercise_slug}_detector",
            "metadata": {
                "camera_fps": 30,
                "model_file": MODEL_PATH,
                "device": "webcam",
                "source": "opencv_local",
            },
        },
        "session": {
            "total_duration_seconds": total_duration,
            "total_calories_burned": round(calories_burned, 2),
            "average_posture_score": posture_score,
        },
        "exercises": [
            {
                "roadmap_day_exercise_id": roadmap_day_exercise_id,
                "exercise_slug": exercise_slug,
                "actual_sets": planned_sets or 1,
                "actual_reps": actual_reps,
                "actual_duration_seconds": total_duration,
                "correct_reps": correct_reps,
                "incorrect_reps": incorrect_reps_count,
                "calories_burned": round(calories_burned, 2),
                "posture_score": posture_score,
                "posture_events": posture_events,
            }
        ],
    }

    # POST to Django backend if callback URL provided
    if backend_callback_url:
        _send_to_backend(backend_callback_url, result_payload, access_token)

    return result_payload


def _send_to_backend(url: str, payload: dict, access_token: str = None):
    try:
        import requests
        headers = {"Content-Type": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[workout_runner] Failed to post to backend: {e}")
        return None
