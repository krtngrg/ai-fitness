import time

from config import (
    SQUAT_DOWN_KNEE_ANGLE,
    SQUAT_UP_KNEE_ANGLE,
    PUSHUP_DOWN_ELBOW_ANGLE,
    PUSHUP_UP_ELBOW_ANGLE,
    JACK_OPEN_FOOT_MULTIPLIER,
    JACK_CLOSED_FOOT_MULTIPLIER,
    PLANK_GOOD_BODY_ANGLE,
    LUNGE_DOWN_KNEE_ANGLE,
    LUNGE_UP_KNEE_ANGLE,
)

from landmarks import (
    LEFT_SHOULDER,
    RIGHT_SHOULDER,
    LEFT_WRIST,
    RIGHT_WRIST,
    LEFT_ANKLE,
    RIGHT_ANKLE,
)

from pose_helpers import (
    calculate_angle,
    landmark_xy,
    all_visible,
    required_side_visible,
    get_side_points,
    average,
    set_no_landmarks_feedback,
)


# More forgiving thresholds for real webcam movement.
# Your old values were too strict, so many squats/pushups were not counted.
SQUAT_DOWN_TRIGGER = max(SQUAT_DOWN_KNEE_ANGLE, 125)
SQUAT_UP_TRIGGER = min(SQUAT_UP_KNEE_ANGLE, 155)

PUSHUP_DOWN_TRIGGER = max(PUSHUP_DOWN_ELBOW_ANGLE, 115)
PUSHUP_UP_TRIGGER = min(PUSHUP_UP_ELBOW_ANGLE, 145)

REP_COOLDOWN_SECONDS = 0.35


def _count_rep_once(state):
    """
    Count one rep, but prevent double-counting caused by camera jitter.
    """
    now = time.time()
    last_rep_time = getattr(state, "last_rep_time", 0.0)

    if now - last_rep_time >= REP_COOLDOWN_SECONDS:
        state.reps += 1
        state.last_rep_time = now
        return True

    return False


def _avg(values):
    clean_values = [value for value in values if value is not None]

    if not clean_values:
        return None

    return average(clean_values)


def _min(values):
    clean_values = [value for value in values if value is not None]

    if not clean_values:
        return None

    return min(clean_values)


def analyze_squat(landmarks, state):
    knee_angles = []
    hip_angles = []

    for side in ["left", "right"]:
        if required_side_visible(
            landmarks,
            side,
            ["shoulder", "hip", "knee", "ankle"],
        ):
            points = get_side_points(landmarks, side)

            knee_angles.append(
                calculate_angle(
                    points["hip"],
                    points["knee"],
                    points["ankle"],
                )
            )

            hip_angles.append(
                calculate_angle(
                    points["shoulder"],
                    points["hip"],
                    points["knee"],
                )
            )

    # Use the deepest visible knee angle.
    # Averaging both knees can hide a valid squat if one side is noisy.
    knee_angle = _min(knee_angles)
    average_knee_angle = _avg(knee_angles)
    hip_angle = _avg(hip_angles)

    if knee_angle is None:
        return set_no_landmarks_feedback(
            state,
            "Move back. Keep hips, knees, and ankles visible.",
        )

    if knee_angle < state.best_depth_angle:
        state.best_depth_angle = knee_angle

    is_down = knee_angle <= SQUAT_DOWN_TRIGGER
    is_up = (average_knee_angle or knee_angle) >= SQUAT_UP_TRIGGER

    if is_down:
        state.position = "DOWN"

    elif is_up:
        if state.position == "DOWN":
            _count_rep_once(state)
            state.best_depth_angle = 999.0

        state.position = "UP"

    feedback = []
    score = 100

    if state.position == "UNKNOWN":
        feedback.append("Start standing tall, then squat.")

    elif state.position == "UP":
        feedback.append("Standing tall. Start next rep.")

    elif state.position == "DOWN":
        feedback.append("Good depth. Push back up.")

    if state.position != "DOWN" and knee_angle > SQUAT_DOWN_TRIGGER:
        feedback.append("Go lower until knees bend more.")
        score -= 10

    if hip_angle is not None and hip_angle < 55:
        feedback.append("Keep chest up.")
        score -= 20

    if not feedback:
        feedback.append("Move with control.")

    state.feedback = " ".join(feedback)
    state.form_score = max(0, min(100, score))

    metrics = {
        "Knee angle": knee_angle,
        "Avg knee angle": average_knee_angle,
        "Hip angle": hip_angle,
    }

    return metrics, state


def analyze_pushup(landmarks, state):
    elbow_angles = []
    body_angles = []

    for side in ["left", "right"]:
        if required_side_visible(
            landmarks,
            side,
            ["shoulder", "elbow", "wrist", "hip", "ankle"],
        ):
            points = get_side_points(landmarks, side)

            elbow_angles.append(
                calculate_angle(
                    points["shoulder"],
                    points["elbow"],
                    points["wrist"],
                )
            )

            body_angles.append(
                calculate_angle(
                    points["shoulder"],
                    points["hip"],
                    points["ankle"],
                )
            )

    elbow_angle = _avg(elbow_angles)
    body_angle = _avg(body_angles)

    if elbow_angle is None:
        return set_no_landmarks_feedback(
            state,
            "Use side view. Keep shoulder, elbow, wrist, hip, and ankle visible.",
        )

    is_down = elbow_angle <= PUSHUP_DOWN_TRIGGER
    is_up = elbow_angle >= PUSHUP_UP_TRIGGER

    if is_down:
        state.position = "DOWN"

    elif is_up:
        if state.position == "DOWN":
            _count_rep_once(state)

        state.position = "UP"

    feedback = []
    score = 100

    if state.position == "UNKNOWN":
        feedback.append("Start in a high plank, then lower.")

    elif state.position == "UP":
        feedback.append("Arms extended. Lower with control.")

    elif state.position == "DOWN":
        feedback.append("Good depth. Push back up.")

    if body_angle is not None and body_angle < 150:
        feedback.append("Keep body straight.")
        score -= 25

    if state.position != "DOWN" and elbow_angle > PUSHUP_DOWN_TRIGGER:
        feedback.append("Lower chest more.")
        score -= 10

    if not feedback:
        feedback.append("Move with control.")

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
            _count_rep_once(state)

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
        if required_side_visible(
            landmarks,
            side,
            ["shoulder", "hip", "ankle"],
        ):
            points = get_side_points(landmarks, side)

            body_angles.append(
                calculate_angle(
                    points["shoulder"],
                    points["hip"],
                    points["ankle"],
                )
            )

    body_angle = average(body_angles)

    if body_angle is None:
        return set_no_landmarks_feedback(
            state,
            "Use side view. Keep shoulder, hip, and ankle visible.",
        )

    score = 100
    feedback = []

    if body_angle >= PLANK_GOOD_BODY_ANGLE:
        if state.plank_start_time is None:
            state.plank_start_time = time.time()

        state.position = "HOLD"
        state.plank_seconds = time.time() - state.plank_start_time
        state.best_plank_seconds = max(
            state.best_plank_seconds,
            state.plank_seconds,
        )
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

    if required_side_visible(
        landmarks,
        "left",
        ["shoulder", "hip", "knee", "ankle"],
    ):
        points = get_side_points(landmarks, "left")

        left_knee_angle = calculate_angle(
            points["hip"],
            points["knee"],
            points["ankle"],
        )

        torso_angles.append(
            calculate_angle(
                points["shoulder"],
                points["hip"],
                points["knee"],
            )
        )

    if required_side_visible(
        landmarks,
        "right",
        ["shoulder", "hip", "knee", "ankle"],
    ):
        points = get_side_points(landmarks, "right")

        right_knee_angle = calculate_angle(
            points["hip"],
            points["knee"],
            points["ankle"],
        )

        torso_angles.append(
            calculate_angle(
                points["shoulder"],
                points["hip"],
                points["knee"],
            )
        )

    knee_angles = [
        angle
        for angle in [left_knee_angle, right_knee_angle]
        if angle is not None
    ]

    torso_angle = average(torso_angles)

    if len(knee_angles) < 2:
        return set_no_landmarks_feedback(
            state,
            "Move back. Both legs must be visible for lunges.",
        )

    front_knee_angle = min(knee_angles)

    both_legs_straight = (
        left_knee_angle > LUNGE_UP_KNEE_ANGLE
        and right_knee_angle > LUNGE_UP_KNEE_ANGLE
    )

    if both_legs_straight:
        if state.position == "DOWN":
            _count_rep_once(state)

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