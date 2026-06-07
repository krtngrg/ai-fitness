"""
workout_runner.py — programmatic wrapper around the MoveMate AI model.

Tracks:
- exercise reps
- sets
- calories
- posture score
- backend callback result

Used by:
    api_server.py -> run_ai_workout(...)
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
from drawing import (
    draw_info_panel,
    draw_pose,
    draw_set_complete_screen,
    draw_all_sets_done_screen,
)
from exercise_logic import analyze_exercise
from pose_landmarker import create_pose_landmarker
from state import reset_state


# Try to use the cleaner fullscreen window helper from drawing.py.
# If drawing.py does not have it yet, this fallback still works.
try:
    from drawing import setup_camera_window
except ImportError:
    def setup_camera_window(window_name, width=1280, height=720, fullscreen=False):
        flags = cv2.WINDOW_NORMAL | getattr(cv2, "WINDOW_GUI_NORMAL", 0)

        try:
            cv2.namedWindow(window_name, flags)
        except cv2.error:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        try:
            cv2.startWindowThread()
        except Exception:
            pass

        if fullscreen:
            cv2.setWindowProperty(
                window_name,
                cv2.WND_PROP_FULLSCREEN,
                cv2.WINDOW_FULLSCREEN,
            )
        else:
            cv2.resizeWindow(window_name, width, height)


CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
FULLSCREEN_CAMERA = True


SLUG_TO_EXERCISE = {
    "squat":            "Squat",
    "push_up":          "Push-up",
    "pushup":           "Push-up",
    "push-up":          "Push-up",
    "sit_up":           "Sit-up",
    "situp":            "Sit-up",
    "jumping_jack":     "Jumping Jack",
    "jumping-jack":     "Jumping Jack",
    "plank":            "Plank",
    "lunge":            "Lunge",
    "lunges":           "Lunge",
    "burpee":           "Burpee",
    "burpees":          "Burpee",
    "mountain_climber": "Mountain Climber",
}


def camera_window_closed(window_name: str) -> bool:
    """
    OpenCV does not automatically stop your Python loop when the X button is clicked.
    This checks whether the window was closed.
    """
    try:
        return cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def should_exit_camera(window_name: str, key: int) -> bool:
    """
    Exit when:
    - Q is pressed
    - ESC is pressed
    - the window close button is clicked
    """
    return key in (ord("q"), 27) or camera_window_closed(window_name)


def open_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Check CAMERA_INDEX in config.py.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    return cap


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
    reps_per_set = planned_reps

    cap = open_camera()

    setup_camera_window(
        WINDOW_NAME,
        width=CAMERA_WIDTH,
        height=CAMERA_HEIGHT,
        fullscreen=FULLSCREEN_CAMERA,
    )

    calorie_tracker = CalorieTracker()

    posture_events = []
    incorrect_reps_count = 0

    workout_start_time = time.time()
    calories_burned = 0.0

    current_set = 1
    completed_sets = 0
    total_actual_reps = 0

    original_cwd = os.getcwd()
    os.chdir(_here)

    try:
        try:
            landmarker = create_pose_landmarker()
        except Exception as error:
            raise RuntimeError(f"Could not load pose model: {error}")

        with landmarker:
            while current_set <= total_sets:
                state = reset_state(exercise_name)
                set_start_time = time.time()

                set_finished = False
                user_quit = False

                while True:
                    elapsed_total = time.time() - workout_start_time
                    elapsed_set = time.time() - set_start_time

                    if planned_duration_seconds and elapsed_total >= planned_duration_seconds:
                        total_actual_reps += state.reps
                        completed_sets += 1
                        current_set = total_sets + 1
                        break

                    success, frame = cap.read()

                    if not success:
                        total_actual_reps += state.reps
                        completed_sets += 1
                        user_quit = True
                        current_set = total_sets + 1
                        break

                    frame = cv2.flip(frame, 1)

                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    rgb_frame = np.ascontiguousarray(rgb_frame)

                    mp_image = mp.Image(
                        image_format=mp.ImageFormat.SRGB,
                        data=rgb_frame,
                    )

                    timestamp_ms = int(elapsed_total * 1000)
                    result = landmarker.detect_for_video(mp_image, timestamp_ms)

                    metrics = {}

                    if result.pose_landmarks:
                        landmarks = result.pose_landmarks[0]

                        old_reps = state.reps
                        metrics, state = analyze_exercise(landmarks, state)

                        if exercise_name == "Plank":
                            calories_burned = calorie_tracker.update_plank(
                                state.plank_seconds
                            )
                        else:
                            calories_burned = calorie_tracker.update_by_reps(
                                exercise_name=exercise_name,
                                reps=total_actual_reps + state.reps,
                            )

                        if state.reps > old_reps:
                            print(
                                f"Good {exercise_name}! "
                                f"Set={current_set}/{total_sets} | "
                                f"Set reps={state.reps} | "
                                f"Total reps={total_actual_reps + state.reps} | "
                                f"Calories={calories_burned:.2f}"
                            )

                            if state.form_score < 70:
                                incorrect_reps_count += 1

                                posture_events.append(
                                    {
                                        "timestamp_seconds": round(elapsed_total, 3),
                                        "issue_type": "poor_form",
                                        "feedback": state.feedback,
                                        "posture_score": state.form_score,
                                        "landmark_data": {
                                            key: round(float(value), 2)
                                            for key, value in metrics.items()
                                            if value is not None
                                        },
                                    }
                                )

                        draw_pose(frame, landmarks)

                    else:
                        state.feedback = "No person detected. Step into view."
                        state.form_score = 0

                        if exercise_name == "Plank":
                            state.plank_start_time = None
                            state.plank_seconds = 0.0

                    draw_info_panel(
                        frame,
                        state,
                        metrics,
                        calories_burned,
                        current_set=current_set,
                        total_sets=total_sets,
                        planned_reps=reps_per_set,
                        planned_duration=planned_duration_seconds,
                        elapsed=elapsed_set,
                    )

                    cv2.imshow(WINDOW_NAME, frame)

                    key = cv2.waitKey(1) & 0xFF

                    if should_exit_camera(WINDOW_NAME, key):
                        total_actual_reps += state.reps
                        completed_sets += 1
                        user_quit = True
                        current_set = total_sets + 1
                        break

                    if key == ord("r"):
                        state = reset_state(exercise_name)
                        print(f"{exercise_name} current set reset.")

                    elif key == ord("n"):
                        total_actual_reps += state.reps
                        completed_sets += 1
                        set_finished = True
                        break

                    elif reps_per_set and state.reps >= reps_per_set:
                        total_actual_reps += state.reps
                        completed_sets += 1
                        set_finished = True
                        break

                if user_quit:
                    break

                if not set_finished and current_set > total_sets:
                    break

                if current_set <= total_sets:
                    is_last_set = current_set == total_sets

                    if is_last_set:
                        _show_all_sets_done_screen(
                            cap=cap,
                            exercise_name=exercise_name,
                            total_sets=total_sets,
                            total_actual_reps=total_actual_reps,
                            calories_burned=calories_burned,
                        )
                    else:
                        should_continue = _show_set_complete_screen(
                            cap=cap,
                            current_set=current_set,
                            total_sets=total_sets,
                            reps_done=state.reps,
                            planned_reps=reps_per_set,
                            calories_burned=calories_burned,
                        )

                        if not should_continue:
                            break

                current_set += 1

    finally:
        cap.release()
        cv2.destroyAllWindows()
        os.chdir(original_cwd)

    total_duration = round(time.time() - workout_start_time)
    correct_reps = max(0, total_actual_reps - incorrect_reps_count)

    if total_actual_reps > 0:
        posture_score = max(0, 100 - incorrect_reps_count * 10)
    elif exercise_name == "Plank" and total_duration > 0:
        posture_score = 100
    else:
        posture_score = 0

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
            "session_id": session_id,
            "total_duration_seconds": total_duration,
            "total_calories_burned": round(calories_burned, 2),
            "average_posture_score": posture_score,
        },
        "exercises": [
            {
                "roadmap_day_exercise_id": roadmap_day_exercise_id,
                "exercise_slug": exercise_slug,
                "exercise_name": exercise_name,
                "actual_sets": completed_sets,
                "planned_sets": total_sets,
                "actual_reps": total_actual_reps,
                "planned_reps": planned_reps,
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
        _send_to_backend(
            backend_callback_url,
            result_payload,
            access_token,
        )

    return result_payload


def _show_set_complete_screen(
    cap,
    current_set,
    total_sets,
    reps_done,
    planned_reps,
    calories_burned,
):
    """
    Shows the set complete screen.
    Press N to continue.
    Press Q or ESC to quit.
    Clicking the close button also quits.
    """
    while True:
        success, frame = cap.read()

        if not success:
            return False

        frame = cv2.flip(frame, 1)

        draw_set_complete_screen(
            frame,
            current_set,
            total_sets,
            reps_done,
            planned_reps,
            calories_burned,
        )

        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF

        if should_exit_camera(WINDOW_NAME, key):
            return False

        if key == ord("n"):
            return True


def _show_all_sets_done_screen(
    cap,
    exercise_name,
    total_sets,
    total_actual_reps,
    calories_burned,
):
    """
    Shows workout complete screen for a short time.
    Press Q or ESC to close early.
    Clicking the close button also closes it.
    """
    end_time = time.time() + 3

    while time.time() < end_time:
        success, frame = cap.read()

        if not success:
            break

        frame = cv2.flip(frame, 1)

        draw_all_sets_done_screen(
            frame,
            exercise_name,
            total_sets,
            total_actual_reps,
            calories_burned,
        )

        cv2.imshow(WINDOW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF

        if should_exit_camera(WINDOW_NAME, key):
            break


def _send_to_backend(url: str, payload: dict, access_token: str = None):
    try:
        import requests

        headers = {
            "Content-Type": "application/json",
        }

        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=10,
        )

        response.raise_for_status()

        try:
            return response.json()
        except Exception:
            return {"status": "sent"}

    except Exception as error:
        print(f"[workout_runner] Failed to post to backend: {error}")
        return None