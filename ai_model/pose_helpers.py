import numpy as np

from config import MIN_VISIBILITY
from landmarks import (
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_ELBOW,
    RIGHT_ELBOW,
    LEFT_WRIST,
    RIGHT_WRIST,
    LEFT_HIP,
    RIGHT_HIP,
    LEFT_KNEE,
    RIGHT_KNEE,
    LEFT_ANKLE,
    RIGHT_ANKLE,
)


def calculate_angle(a, b, c):
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
