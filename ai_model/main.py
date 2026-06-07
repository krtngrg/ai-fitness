import time

import cv2
import mediapipe as mp
import numpy as np

from calorie_tracker import CalorieTracker
from config import CAMERA_INDEX, EXERCISE_KEYS, MODEL_PATH, WINDOW_NAME
from drawing import draw_info_panel, draw_pose, format_metric
from exercise_logic import analyze_exercise
from pose_landmarker import create_pose_landmarker
from state import MoveMateState, reset_state


def print_exercise_menu():
    print("Exercise controls:")
    print("  1 = Squat")
    print("  2 = Push-up")
    print("  3 = Jumping Jack")
    print("  4 = Plank")
    print("  5 = Lunge")
    print("  r = reset current exercise")
    print("  c = reset calories")
    print("  q = quit")


def main():
    print("Starting MoveMate AI MVP-1...")
    print("Using MediaPipe Tasks Pose Landmarker.")
    print("Checking model:", MODEL_PATH)
    print_exercise_menu()

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        print("Try changing CAMERA_INDEX = 0 to CAMERA_INDEX = 1 in config.py")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    state = MoveMateState()
    calorie_tracker = CalorieTracker()

    frame_count = 0
    start_time = time.time()
    calories_burned = 0.0

    try:
        landmarker = create_pose_landmarker()
    except Exception as error:
        print("ERROR: Could not create Pose Landmarker.")
        print("Make sure pose_landmarker_lite.task is in this folder.")
        print("Original error:")
        print(error)
        cap.release()
        return

    with landmarker:
        while True:
            success, frame = cap.read()

            if not success:
                print("ERROR: Could not read frame.")
                break

            frame_count += 1
            frame = cv2.flip(frame, 1)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame = np.ascontiguousarray(rgb_frame)

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )

            timestamp_ms = int((time.time() - start_time) * 1000)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            metrics = {}

            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]

                old_reps = state.reps
                metrics, state = analyze_exercise(landmarks, state)

                if state.exercise == "Plank":
                    calories_burned = calorie_tracker.update_plank(
                        state.plank_seconds
                    )
                else:
                    calories_burned = calorie_tracker.update_by_reps(
                        exercise_name=state.exercise,
                        reps=state.reps,
                    )

                if state.reps > old_reps:
                    print(
                        f"Good {state.exercise}! "
                        f"Reps={state.reps} | "
                        f"Calories={calories_burned:.2f}"
                    )

                draw_pose(frame, landmarks)

            else:
                state.feedback = "No person detected. Step into view."
                state.form_score = 0
                calories_burned = calorie_tracker.total_calories

                if state.exercise == "Plank":
                    state.plank_start_time = None
                    state.plank_seconds = 0.0

            draw_info_panel(frame, state, metrics, calories_burned)

            if frame_count % 15 == 0:
                metric_text = " | ".join(
                    f"{label}={format_metric(value)}"
                    for label, value in list(metrics.items())[:3]
                )

                if metric_text:
                    print(
                        f"Exercise={state.exercise} | "
                        f"State={state.position} | "
                        f"Reps={state.reps} | "
                        f"Calories={calories_burned:.2f} | "
                        f"{metric_text} | "
                        f"Score={state.form_score}"
                    )
                else:
                    print(f"Exercise={state.exercise} | Waiting for landmarks...")

            cv2.imshow(WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            if key == ord("r"):
                state = reset_state(state.exercise)
                print(f"{state.exercise} counter reset.")

            if key == ord("c"):
                calorie_tracker.reset()
                calories_burned = 0.0
                print("Calories reset.")

            if key in EXERCISE_KEYS:
                selected_exercise = EXERCISE_KEYS[key]
                state = reset_state(selected_exercise)
                print(f"Switched to {selected_exercise}.")

    cap.release()
    cv2.destroyAllWindows()
    print("MoveMate AI stopped.")


if __name__ == "__main__":
    main()