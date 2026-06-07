import cv2

from landmarks import POSE_CONNECTIONS
from pose_helpers import landmark_visible


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


def draw_info_panel(frame, state, metrics, calories_burned):
    height, width, _ = frame.shape

    cv2.rectangle(frame, (10, 10), (740, 315), (20, 20, 20), -1)

    rep_line = f"Reps: {state.reps}"

    if state.exercise == "Plank":
        rep_line = f"Hold: {state.plank_seconds:.1f}s | Best: {state.best_plank_seconds:.1f}s"

    lines = [
        "MoveMate AI MVP-1",
        f"Exercise: {state.exercise}",
        f"State: {state.position}",
        rep_line,
        f"Calories: {calories_burned:.2f} kcal",
    ]

    for label, value in list(metrics.items())[:3]:
        lines.append(f"{label}: {format_metric(value)}")

    lines.extend([
        f"Form score: {state.form_score}/100",
        f"Feedback: {state.feedback[:72]}",
        "Keys: 1 Squat | 2 Push-up | 3 Jumping Jack | 4 Plank | 5 Lunge | c Calories reset",
    ])

    y = 38

    for line in lines:
        color = (255, 255, 255)
        font_scale = 0.7

        if line.startswith("Feedback"):
            color = (0, 255, 255)
            font_scale = 0.55

        if line.startswith("Keys"):
            color = (200, 200, 200)
            font_scale = 0.48

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
        "Press q to quit | r to reset current exercise | c to reset calories",
        (10, height - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
