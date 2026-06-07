"""
MoveMate AI - MVP-1 Multi-Exercise Detector
MediaPipe Tasks API version

Exercises added:
- Squat
- Push-up
- Jumping Jack
- Plank
- Lunge

Run:
    python movemate_multi_exercise.py

Controls:
    1 = Squat
    2 = Push-up
    3 = Jumping Jack
    4 = Plank
    5 = Lunge
    r = reset current exercise
    q = quit
"""

import time
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np


# -----------------------------
# Config
# -----------------------------

CAMERA_INDEX = 0
MODEL_PATH = "pose_landmarker_lite.task"

MIN_VISIBILITY = 0.05

# Squat thresholds
SQUAT_DOWN_KNEE_ANGLE = 105
SQUAT_UP_KNEE_ANGLE = 160

# Push-up thresholds
PUSHUP_DOWN_ELBOW_ANGLE = 95
PUSHUP_UP_ELBOW_ANGLE = 155

# Jumping jack thresholds
JACK_OPEN_FOOT_MULTIPLIER = 1.25
JACK_CLOSED_FOOT_MULTIPLIER = 1.00

# Plank thresholds
PLANK_GOOD_BODY_ANGLE = 160

# Lunge thresholds
LUNGE_DOWN_KNEE_ANGLE = 115
LUNGE_UP_KNEE_ANGLE = 155

WINDOW_NAME = "MoveMate AI - Multi-Exercise Detector"


# -----------------------------
# MediaPipe landmark indexes
# -----------------------------

NOSE = 0

LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12

LEFT_ELBOW = 13
RIGHT_ELBOW = 14

LEFT_WRIST = 15
RIGHT_WRIST = 16

LEFT_HIP = 23
RIGHT_HIP = 24

LEFT_KNEE = 25
RIGHT_KNEE = 26

LEFT_ANKLE = 27
RIGHT_ANKLE = 28

LEFT_HEEL = 29
RIGHT_HEEL = 30

LEFT_FOOT_INDEX = 31
RIGHT_FOOT_INDEX = 32


POSE_CONNECTIONS = [
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_SHOULDER, LEFT_ELBOW),
    (LEFT_ELBOW, LEFT_WRIST),
    (RIGHT_SHOULDER, RIGHT_ELBOW),
    (RIGHT_ELBOW, RIGHT_WRIST),

    (LEFT_SHOULDER, LEFT_HIP),
    (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_HIP, RIGHT_HIP),

    (LEFT_HIP, LEFT_KNEE),
    (LEFT_KNEE, LEFT_ANKLE),
    (LEFT_ANKLE, LEFT_HEEL),
    (LEFT_HEEL, LEFT_FOOT_INDEX),

    (RIGHT_HIP, RIGHT_KNEE),
    (RIGHT_KNEE, RIGHT_ANKLE),
    (RIGHT_ANKLE, RIGHT_HEEL),
    (RIGHT_HEEL, RIGHT_FOOT_INDEX),
]


EXERCISE_KEYS = {
    ord("1"): "Squat",
    ord("2"): "Push-up",
    ord("3"): "Jumping Jack",
    ord("4"): "Plank",
    ord("5"): "Lunge",
}


# -----------------------------
# State
# -----------------------------

@dataclass
class MoveMateState:
    exercise: str = "Squat"
    position: str = "UNKNOWN"
    reps: int = 0
    best_depth_angle: float = 999.0
    plank_start_time: float = None
    plank_seconds: float = 0.0
    best_plank_seconds: float = 0.0
    feedback: str = "Stand where your full body is visible."
    form_score: int = 100


def reset_state(exercise):
    return MoveMateState(exercise=exercise)


# -----------------------------
# Helpers
# -----------------------------

def calculate_angle(a, b, c):
    """
    Calculates angle ABC in degrees.
    a, b, c are [x, y].
    """

    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(
        a[1] - b[1], a[0] - b[0]
    )

    angle = abs(radians * 180.0 / np.pi)

    if angle > 180:
        angle = 360 - angle

    return angle


def landmark_xy(landmarks, index):
    lm = landmarks[index]
    return [lm.x, lm.y]


def landmark_visible(landmarks, index):
    lm = landmarks[index]

    if lm.x < -0.2 or lm.x > 1.2:
        return False

    if lm.y < -0.2 or lm.y > 1.2:
        return False

    visibility = getattr(lm, "visibility", 1.0)
    presence = getattr(lm, "presence", 1.0)

    return visibility >= MIN_VISIBILITY and presence >= MIN_VISIBILITY


def all_visible(landmarks, indexes):
    return all(landmark_visible(landmarks, index) for index in indexes)


def required_side_visible(landmarks, side, needed_parts):
    if side == "left":
        mapping = {
            "shoulder": LEFT_SHOULDER,
            "elbow": LEFT_ELBOW,
            "wrist": LEFT_WRIST,
            "hip": LEFT_HIP,
            "knee": LEFT_KNEE,
            "ankle": LEFT_ANKLE,
        }
    else:
        mapping = {
            "shoulder": RIGHT_SHOULDER,
            "elbow": RIGHT_ELBOW,
            "wrist": RIGHT_WRIST,
            "hip": RIGHT_HIP,
            "knee": RIGHT_KNEE,
            "ankle": RIGHT_ANKLE,
        }

    return all_visible(landmarks, [mapping[part] for part in needed_parts])


def get_side_points(landmarks, side):
    if side == "left":
        return {
            "shoulder": landmark_xy(landmarks, LEFT_SHOULDER),
            "elbow": landmark_xy(landmarks, LEFT_ELBOW),
            "wrist": landmark_xy(landmarks, LEFT_WRIST),
            "hip": landmark_xy(landmarks, LEFT_HIP),
            "knee": landmark_xy(landmarks, LEFT_KNEE),
            "ankle": landmark_xy(landmarks, LEFT_ANKLE),
        }

    return {
        "shoulder": landmark_xy(landmarks, RIGHT_SHOULDER),
        "elbow": landmark_xy(landmarks, RIGHT_ELBOW),
        "wrist": landmark_xy(landmarks, RIGHT_WRIST),
        "hip": landmark_xy(landmarks, RIGHT_HIP),
        "knee": landmark_xy(landmarks, RIGHT_KNEE),
        "ankle": landmark_xy(landmarks, RIGHT_ANKLE),
    }


def average(values):
    clean_values = [value for value in values if value is not None]

    if not clean_values:
        return None

    return float(np.mean(clean_values))


def set_no_landmarks_feedback(state, message="Move back. Full body must be visible."):
    state.feedback = message
    state.form_score = 0

    if state.exercise == "Plank":
        state.plank_start_time = None
        state.plank_seconds = 0.0

    return {}, state


# -----------------------------
# Exercise logic
# -----------------------------

def analyze_squat(landmarks, state):
    knee_angles = []
    hip_angles = []

    for side in ["left", "right"]:
        if required_side_visible(landmarks, side, ["shoulder", "hip", "knee", "ankle"]):
            points = get_side_points(landmarks, side)
            knee_angles.append(calculate_angle(points["hip"], points["knee"], points["ankle"]))
            hip_angles.append(calculate_angle(points["shoulder"], points["hip"], points["knee"]))

    knee_angle = average(knee_angles)
    hip_angle = average(hip_angles)

    if knee_angle is None:
        return set_no_landmarks_feedback(state)

    if knee_angle < state.best_depth_angle:
        state.best_depth_angle = knee_angle

    if knee_angle > SQUAT_UP_KNEE_ANGLE:
        if state.position == "DOWN":
            state.reps += 1
            state.best_depth_angle = 999.0

        state.position = "UP"

    elif knee_angle < SQUAT_DOWN_KNEE_ANGLE:
        state.position = "DOWN"

    feedback = []
    score = 100

    if state.position == "UNKNOWN":
        feedback.append("Start standing tall, then squat.")
    elif state.position == "UP":
        feedback.append("Standing tall. Start next rep.")
    elif state.position == "DOWN":
        feedback.append("Good depth. Push back up.")

    if knee_angle > 130 and state.position != "UP":
        feedback.append("Go lower.")
        score -= 20

    if hip_angle is not None and hip_angle < 55:
        feedback.append("Keep chest up.")
        score -= 25

    if not feedback:
        feedback.append("Move with control.")

    state.feedback = " ".join(feedback)
    state.form_score = max(0, min(100, score))

    metrics = {
        "Knee angle": knee_angle,
        "Hip angle": hip_angle,
    }

    return metrics, state


def analyze_pushup(landmarks, state):
    elbow_angles = []
    body_angles = []

    for side in ["left", "right"]:
        if required_side_visible(landmarks, side, ["shoulder", "elbow", "wrist", "hip", "ankle"]):
            points = get_side_points(landmarks, side)
            elbow_angles.append(calculate_angle(points["shoulder"], points["elbow"], points["wrist"]))
            body_angles.append(calculate_angle(points["shoulder"], points["hip"], points["ankle"]))

    elbow_angle = average(elbow_angles)
    body_angle = average(body_angles)

    if elbow_angle is None:
        return set_no_landmarks_feedback(
            state,
            "Use a side view. Keep shoulders, elbows, wrists, hips, and ankles visible.",
        )

    if elbow_angle > PUSHUP_UP_ELBOW_ANGLE:
        if state.position == "DOWN":
            state.reps += 1

        state.position = "UP"

    elif elbow_angle < PUSHUP_DOWN_ELBOW_ANGLE:
        state.position = "DOWN"

    feedback = []
    score = 100

    if state.position == "UNKNOWN":
        feedback.append("Start in a high plank, then lower.")
    elif state.position == "UP":
        feedback.append("Arms extended. Lower with control.")
    elif state.position == "DOWN":
        feedback.append("Good depth. Push back up.")

    if body_angle is not None and body_angle < 160:
        feedback.append("Keep body straight.")
        score -= 25

    if elbow_angle > 115 and state.position not in ["UP", "UNKNOWN"]:
        feedback.append("Lower chest more.")
        score -= 20

    state.feedback = " ".join(feedback)
    state.form_score = max(0, min(100, score))

    metrics = {
        "Elbow angle": elbow_angle,
        "Body angle": body_angle,
    }

    return metrics, state


def analyze_jumping_jack(landmarks, state):
    required = [
        LEFT_SHOULDER,
        RIGHT_SHOULDER,
        LEFT_WRIST,
        RIGHT_WRIST,
        LEFT_ANKLE,
        RIGHT_ANKLE,
    ]

    if not all_visible(landmarks, required):
        return set_no_landmarks_feedback(
            state,
            "Move back. Wrists, shoulders, and ankles must be visible.",
        )

    left_shoulder = landmark_xy(landmarks, LEFT_SHOULDER)
    right_shoulder = landmark_xy(landmarks, RIGHT_SHOULDER)
    left_wrist = landmark_xy(landmarks, LEFT_WRIST)
    right_wrist = landmark_xy(landmarks, RIGHT_WRIST)
    left_ankle = landmark_xy(landmarks, LEFT_ANKLE)
    right_ankle = landmark_xy(landmarks, RIGHT_ANKLE)

    shoulder_width = abs(right_shoulder[0] - left_shoulder[0])
    foot_width = abs(right_ankle[0] - left_ankle[0])

    if shoulder_width < 0.01:
        shoulder_width = 0.01

    foot_ratio = foot_width / shoulder_width

    average_wrist_y = (left_wrist[1] + right_wrist[1]) / 2.0
    average_shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2.0

    wrists_above_shoulders = average_wrist_y < average_shoulder_y
    wrists_below_shoulders = average_wrist_y > average_shoulder_y + 0.10

    is_open = wrists_above_shoulders and foot_ratio > JACK_OPEN_FOOT_MULTIPLIER
    is_closed = wrists_below_shoulders and foot_ratio < JACK_CLOSED_FOOT_MULTIPLIER

    if is_open:
        if state.position == "CLOSED":
            state.reps += 1

        state.position = "OPEN"

    elif is_closed:
        state.position = "CLOSED"

    feedback = []
    score = 100

    if state.position == "UNKNOWN":
        feedback.append("Start closed, then jump open.")
    elif state.position == "CLOSED":
        feedback.append("Closed position. Jump open.")
    elif state.position == "OPEN":
        feedback.append("Open position. Return closed.")

    if not wrists_above_shoulders and state.position == "OPEN":
        feedback.append("Raise arms overhead.")
        score -= 20

    if foot_ratio < JACK_OPEN_FOOT_MULTIPLIER and state.position == "OPEN":
        feedback.append("Jump feet wider.")
        score -= 20

    state.feedback = " ".join(feedback)
    state.form_score = max(0, min(100, score))

    metrics = {
        "Foot ratio": foot_ratio,
        "Wrist height": average_shoulder_y - average_wrist_y,
    }

    return metrics, state


def analyze_plank(landmarks, state):
    body_angles = []

    for side in ["left", "right"]:
        if required_side_visible(landmarks, side, ["shoulder", "hip", "ankle"]):
            points = get_side_points(landmarks, side)
            body_angles.append(calculate_angle(points["shoulder"], points["hip"], points["ankle"]))

    body_angle = average(body_angles)

    if body_angle is None:
        return set_no_landmarks_feedback(
            state,
            "Use a side view. Keep shoulder, hip, and ankle visible.",
        )

    score = 100
    feedback = []

    if body_angle >= PLANK_GOOD_BODY_ANGLE:
        if state.plank_start_time is None:
            state.plank_start_time = time.time()

        state.position = "HOLD"
        state.plank_seconds = time.time() - state.plank_start_time
        state.best_plank_seconds = max(state.best_plank_seconds, state.plank_seconds)
        feedback.append("Good plank. Keep holding.")
    else:
        state.position = "RESET"
        state.plank_start_time = None
        state.plank_seconds = 0.0
        feedback.append("Straighten your body to start the hold.")
        score -= 35

    if body_angle < 170:
        feedback.append("Avoid hips sagging or lifting.")
        score -= 15

    state.feedback = " ".join(feedback)
    state.form_score = max(0, min(100, score))

    metrics = {
        "Body angle": body_angle,
        "Hold seconds": state.plank_seconds,
    }

    return metrics, state


def analyze_lunge(landmarks, state):
    left_knee_angle = None
    right_knee_angle = None
    torso_angles = []

    if required_side_visible(landmarks, "left", ["shoulder", "hip", "knee", "ankle"]):
        points = get_side_points(landmarks, "left")
        left_knee_angle = calculate_angle(points["hip"], points["knee"], points["ankle"])
        torso_angles.append(calculate_angle(points["shoulder"], points["hip"], points["knee"]))

    if required_side_visible(landmarks, "right", ["shoulder", "hip", "knee", "ankle"]):
        points = get_side_points(landmarks, "right")
        right_knee_angle = calculate_angle(points["hip"], points["knee"], points["ankle"])
        torso_angles.append(calculate_angle(points["shoulder"], points["hip"], points["knee"]))

    knee_angles = [angle for angle in [left_knee_angle, right_knee_angle] if angle is not None]
    torso_angle = average(torso_angles)

    if len(knee_angles) < 2:
        return set_no_landmarks_feedback(
            state,
            "Move back. Both legs must be visible for lunges.",
        )

    front_knee_angle = min(knee_angles)
    both_legs_straight = left_knee_angle > LUNGE_UP_KNEE_ANGLE and right_knee_angle > LUNGE_UP_KNEE_ANGLE

    if both_legs_straight:
        if state.position == "DOWN":
            state.reps += 1

        state.position = "UP"

    elif front_knee_angle < LUNGE_DOWN_KNEE_ANGLE:
        state.position = "DOWN"

    feedback = []
    score = 100

    if state.position == "UNKNOWN":
        feedback.append("Step into a lunge, then stand tall.")
    elif state.position == "UP":
        feedback.append("Standing tall. Start next lunge.")
    elif state.position == "DOWN":
        feedback.append("Good lunge depth. Push back up.")

    if state.position == "DOWN":
        if front_knee_angle < 75:
            feedback.append("Do not overbend the front knee.")
            score -= 15
        elif front_knee_angle > 105:
            feedback.append("Lower a little more.")
            score -= 15

    if torso_angle is not None and torso_angle < 55:
        feedback.append("Keep chest up.")
        score -= 20

    state.feedback = " ".join(feedback)
    state.form_score = max(0, min(100, score))

    metrics = {
        "Front knee": front_knee_angle,
        "Left knee": left_knee_angle,
        "Right knee": right_knee_angle,
    }

    return metrics, state


def analyze_exercise(landmarks, state):
    if state.exercise == "Squat":
        return analyze_squat(landmarks, state)

    if state.exercise == "Push-up":
        return analyze_pushup(landmarks, state)

    if state.exercise == "Jumping Jack":
        return analyze_jumping_jack(landmarks, state)

    if state.exercise == "Plank":
        return analyze_plank(landmarks, state)

    if state.exercise == "Lunge":
        return analyze_lunge(landmarks, state)

    state.feedback = "Unknown exercise selected."
    state.form_score = 0
    return {}, state


# -----------------------------
# Drawing
# -----------------------------

def normalized_to_pixel(landmark, width, height):
    x = int(landmark.x * width)
    y = int(landmark.y * height)
    return x, y


def draw_pose(frame, landmarks):
    height, width, _ = frame.shape

    for start_index, end_index in POSE_CONNECTIONS:
        if start_index >= len(landmarks) or end_index >= len(landmarks):
            continue

        start = landmarks[start_index]
        end = landmarks[end_index]

        if not landmark_visible(landmarks, start_index):
            continue

        if not landmark_visible(landmarks, end_index):
            continue

        x1, y1 = normalized_to_pixel(start, width, height)
        x2, y2 = normalized_to_pixel(end, width, height)

        cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)

    for index, landmark in enumerate(landmarks):
        if not landmark_visible(landmarks, index):
            continue

        x, y = normalized_to_pixel(landmark, width, height)
        cv2.circle(frame, (x, y), 5, (0, 255, 255), -1)


def format_metric(value):
    if value is None:
        return "--"

    return f"{value:.1f}"


def draw_info_panel(frame, state, metrics):
    height, width, _ = frame.shape

    cv2.rectangle(frame, (10, 10), (700, 285), (20, 20, 20), -1)

    rep_line = f"Reps: {state.reps}"

    if state.exercise == "Plank":
        rep_line = f"Hold: {state.plank_seconds:.1f}s | Best: {state.best_plank_seconds:.1f}s"

    lines = [
        "MoveMate AI MVP-1",
        f"Exercise: {state.exercise}",
        f"State: {state.position}",
        rep_line,
    ]

    for label, value in list(metrics.items())[:3]:
        lines.append(f"{label}: {format_metric(value)}")

    lines.extend([
        f"Form score: {state.form_score}/100",
        f"Feedback: {state.feedback[:72]}",
        "Keys: 1 Squat | 2 Push-up | 3 Jumping Jack | 4 Plank | 5 Lunge",
    ])

    y = 38

    for index, line in enumerate(lines):
        color = (255, 255, 255)
        font_scale = 0.7

        if line.startswith("Feedback"):
            color = (0, 255, 255)
            font_scale = 0.55

        if line.startswith("Keys"):
            color = (200, 200, 200)
            font_scale = 0.52

        if line.startswith("Form score"):
            if state.form_score >= 80:
                color = (0, 255, 0)
            elif state.form_score >= 50:
                color = (0, 255, 255)
            else:
                color = (0, 0, 255)

        cv2.putText(
            frame,
            line,
            (25, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            2,
            cv2.LINE_AA,
        )

        y += 27

    cv2.putText(
        frame,
        "Press q to quit | r to reset current exercise",
        (10, height - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


# -----------------------------
# Main
# -----------------------------

def create_pose_landmarker():
    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    return PoseLandmarker.create_from_options(options)


def print_exercise_menu():
    print("Exercise controls:")
    print("  1 = Squat")
    print("  2 = Push-up")
    print("  3 = Jumping Jack")
    print("  4 = Plank")
    print("  5 = Lunge")
    print("  r = reset current exercise")
    print("  q = quit")


def main():
    print("Starting MoveMate AI MVP-1...")
    print("Using MediaPipe Tasks Pose Landmarker.")
    print("Checking model:", MODEL_PATH)
    print_exercise_menu()

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("ERROR: Could not open webcam.")
        print("Try changing CAMERA_INDEX = 0 to CAMERA_INDEX = 1")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    state = MoveMateState()
    frame_count = 0
    start_time = time.time()

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
                data=rgb_frame
            )

            timestamp_ms = int((time.time() - start_time) * 1000)

            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            metrics = {}

            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]

                metrics, state = analyze_exercise(landmarks, state)

                draw_pose(frame, landmarks)
            else:
                state.feedback = "No person detected. Step into view."
                state.form_score = 0

                if state.exercise == "Plank":
                    state.plank_start_time = None
                    state.plank_seconds = 0.0

            draw_info_panel(frame, state, metrics)

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

            if key in EXERCISE_KEYS:
                selected_exercise = EXERCISE_KEYS[key]
                state = reset_state(selected_exercise)
                print(f"Switched to {selected_exercise}.")

    cap.release()
    cv2.destroyAllWindows()
    print("MoveMate AI stopped.")


if __name__ == "__main__":
    main()