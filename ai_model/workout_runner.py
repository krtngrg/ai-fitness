"""
workout_runner.py — programmatic wrapper around the MoveMate AI model.
Tracks sets, reps progress, shows completion screen between sets.
"""

import os
import sys
import time

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import cv2
import mediapipe as mp
import numpy as np

from calorie_tracker import CalorieTracker
from config import CAMERA_INDEX, MODEL_PATH, WINDOW_NAME
from drawing import draw_info_panel, draw_pose, draw_set_complete_screen, draw_all_sets_done_screen
from exercise_logic import analyze_exercise
from pose_landmarker import create_pose_landmarker
from state import MoveMateState, reset_state

SLUG_TO_EXERCISE = {
    "squat": "Squat",
    "push_up": "Push-up",
    "jumping_jack": "Jumping Jack",
    "plank": "Plank",
    "lunge": "Lunge",
    "lunges": "Lunge",
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
    exercise_name = SLUG_TO_EXERCISE.get(exercise_slug)
    if not exercise_name:
        raise ValueError(f"Unsupported exercise slug: {exercise_slug}")

    total_sets = planned_sets or 1
    reps_per_set = planned_reps  # None = free mode

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Check CAMERA_INDEX in config.py.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    calorie_tracker = CalorieTracker()
    posture_events = []
    incorrect_reps_count = 0
    start_time = time.time()
    calories_burned = 0.0

    # Per-set tracking
    current_set = 1
    total_actual_reps = 0

    _orig_cwd = os.getcwd()
    os.chdir(_here)
    try:
        landmarker = create_pose_landmarker()
    except Exception as e:
        os.chdir(_orig_cwd)
        cap.release()
        raise RuntimeError(f"Could not load pose model: {e}")

    with landmarker:
        while current_set <= total_sets:
            state = reset_state(exercise_name)
            set_start = time.time()

            # ── Per-set loop ───────────────────────────────────────────────
            while True:
                elapsed = time.time() - start_time
                set_elapsed = time.time() - set_start

                # Duration-based stop
                if planned_duration_seconds and elapsed >= planned_duration_seconds:
                    total_actual_reps += state.reps
                    current_set = total_sets + 1  # exit outer loop too
                    break

                # Reps target reached for this set
                set_done = reps_per_set and state.reps >= reps_per_set

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

                draw_info_panel(
                    frame, state, metrics, calories_burned,
                    current_set=current_set,
                    total_sets=total_sets,
                    planned_reps=reps_per_set,
                    planned_duration=planned_duration_seconds,
                    elapsed=set_elapsed,
                )

                cv2.imshow(WINDOW_NAME, frame)
                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):
                    total_actual_reps += state.reps
                    current_set = total_sets + 1
                    break

                if set_done or key == ord("n"):
                    total_actual_reps += state.reps
                    break

            else:
                # cap.read() failed
                break

            # ── Set complete screen ────────────────────────────────────────
            if current_set <= total_sets:
                is_last = current_set == total_sets
                # Show completion / next screen until user presses N or Q
                deadline = time.time() + (5 if is_last else 60)
                while time.time() < deadline:
                    success, frame = cap.read()
                    if not success:
                        break
                    frame = cv2.flip(frame, 1)

                    if is_last:
                        draw_all_sets_done_screen(
                            frame, exercise_name, total_sets,
                            total_actual_reps, calories_burned,
                        )
                    else:
                        draw_set_complete_screen(
                            frame, current_set, total_sets,
                            state.reps, reps_per_set, calories_burned,
                        )

                    cv2.imshow(WINDOW_NAME, frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        current_set = total_sets + 1
                        break
                    if key == ord("n") or is_last:
                        if is_last:
                            time.sleep(0.4)
                        break

                current_set += 1

    cap.release()
    cv2.destroyAllWindows()
    os.chdir(_orig_cwd)

    total_duration = round(time.time() - start_time)
    correct_reps = max(0, total_actual_reps - incorrect_reps_count)
    posture_score = max(0, 100 - incorrect_reps_count * 10) if total_actual_reps > 0 else 0

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
                "actual_sets": total_sets,
                "actual_reps": total_actual_reps,
                "actual_duration_seconds": total_duration,
                "correct_reps": correct_reps,
                "incorrect_reps": incorrect_reps_count,
                "calories_burned": round(calories_burned, 2),
                "posture_score": posture_score,
                "posture_events": posture_events,
            }
        ],
    }

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
