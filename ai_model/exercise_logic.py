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
    LEFT_SHOULDER, RIGHT_SHOULDER,
    LEFT_ELBOW,    RIGHT_ELBOW,
    LEFT_WRIST,    RIGHT_WRIST,
    LEFT_HIP,      RIGHT_HIP,
    LEFT_KNEE,     RIGHT_KNEE,
    LEFT_ANKLE,    RIGHT_ANKLE,
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

# ── Thresholds ────────────────────────────────────────────────────────────────
SQUAT_DOWN_TRIGGER  = max(SQUAT_DOWN_KNEE_ANGLE, 125)
SQUAT_UP_TRIGGER    = min(SQUAT_UP_KNEE_ANGLE, 155)
PUSHUP_DOWN_TRIGGER = max(PUSHUP_DOWN_ELBOW_ANGLE, 115)
PUSHUP_UP_TRIGGER   = min(PUSHUP_UP_ELBOW_ANGLE, 145)

REP_COOLDOWN_SECONDS = 0.35


# ── Helpers ───────────────────────────────────────────────────────────────────
def _count_rep_once(state):
    now = time.time()
    last_rep_time = getattr(state, "last_rep_time", 0.0)
    if now - last_rep_time >= REP_COOLDOWN_SECONDS:
        state.reps += 1
        state.last_rep_time = now
        return True
    return False


def _avg(values):
    clean = [v for v in values if v is not None]
    return average(clean) if clean else None


def _min(values):
    clean = [v for v in values if v is not None]
    return min(clean) if clean else None


# ── Squat ─────────────────────────────────────────────────────────────────────
def analyze_squat(landmarks, state):
    knee_angles, hip_angles = [], []

    for side in ["left", "right"]:
        if required_side_visible(landmarks, side, ["shoulder", "hip", "knee", "ankle"]):
            p = get_side_points(landmarks, side)
            knee_angles.append(calculate_angle(p["hip"], p["knee"], p["ankle"]))
            hip_angles.append(calculate_angle(p["shoulder"], p["hip"], p["knee"]))

    knee_angle = _min(knee_angles)
    avg_knee   = _avg(knee_angles)
    hip_angle  = _avg(hip_angles)

    if knee_angle is None:
        return set_no_landmarks_feedback(state, "Move back. Keep hips, knees, and ankles visible.")

    if knee_angle < state.best_depth_angle:
        state.best_depth_angle = knee_angle

    if knee_angle <= SQUAT_DOWN_TRIGGER:
        state.position = "DOWN"
    elif (avg_knee or knee_angle) >= SQUAT_UP_TRIGGER:
        if state.position == "DOWN":
            _count_rep_once(state)
            state.best_depth_angle = 999.0
        state.position = "UP"

    feedback, score = [], 100
    if state.position == "UNKNOWN": feedback.append("Start standing tall, then squat.")
    elif state.position == "UP":    feedback.append("Standing tall. Start next rep.")
    elif state.position == "DOWN":  feedback.append("Good depth. Push back up.")
    if state.position != "DOWN" and knee_angle > SQUAT_DOWN_TRIGGER:
        feedback.append("Go lower."); score -= 10
    if hip_angle is not None and hip_angle < 55:
        feedback.append("Keep chest up."); score -= 20
    if not feedback: feedback.append("Move with control.")

    state.feedback   = " ".join(feedback)
    state.form_score = max(0, min(100, score))
    return {"Knee angle": knee_angle, "Hip angle": hip_angle}, state


# ── Push-up ───────────────────────────────────────────────────────────────────
# Requires body to be HORIZONTAL (prone position) before counting reps.
# Prone check: shoulder Y and ankle Y must be within 0.35 vertically,
# and body angle must be > 140°. This blocks counting when standing/sitting.

PUSHUP_MIN_BODY_ANGLE = 140
PUSHUP_PRONE_Y_DIFF   = 0.35

def analyze_pushup(landmarks, state):
    elbow_angles, body_angles = [], []
    shoulder_ys, ankle_ys     = [], []

    for side in ["left", "right"]:
        if required_side_visible(landmarks, side, ["shoulder", "elbow", "wrist", "hip", "ankle"]):
            p = get_side_points(landmarks, side)
            elbow_angles.append(calculate_angle(p["shoulder"], p["elbow"], p["wrist"]))
            body_angles.append(calculate_angle(p["shoulder"], p["hip"], p["ankle"]))
            shoulder_ys.append(p["shoulder"][1])
            ankle_ys.append(p["ankle"][1])

    elbow_angle = _avg(elbow_angles)
    body_angle  = _avg(body_angles)
    shoulder_y  = _avg(shoulder_ys)
    ankle_y     = _avg(ankle_ys)

    if elbow_angle is None:
        return set_no_landmarks_feedback(
            state, "Side view. Keep shoulder, elbow, wrist, hip and ankle visible."
        )

    # Gate: must be in prone (flat) position
    y_diff   = abs((ankle_y or 1.0) - (shoulder_y or 0.0))
    is_prone = y_diff < PUSHUP_PRONE_Y_DIFF and (body_angle is None or body_angle > PUSHUP_MIN_BODY_ANGLE)

    if not is_prone:
        state.position   = "UNKNOWN"
        state.feedback   = "Get into push-up position — lie flat, face down."
        state.form_score = 0
        return {"Elbow angle": elbow_angle, "Body angle": body_angle}, state

    if elbow_angle <= PUSHUP_DOWN_TRIGGER:
        state.position = "DOWN"
    elif elbow_angle >= PUSHUP_UP_TRIGGER:
        if state.position == "DOWN": _count_rep_once(state)
        state.position = "UP"

    feedback, score = [], 100
    if state.position == "UNKNOWN": feedback.append("Start in a high plank, then lower.")
    elif state.position == "UP":    feedback.append("Arms extended. Lower with control.")
    elif state.position == "DOWN":  feedback.append("Good depth. Push back up.")
    if body_angle is not None and body_angle < 150:
        feedback.append("Keep body straight — don't let hips sag."); score -= 25
    if state.position != "DOWN" and elbow_angle > PUSHUP_DOWN_TRIGGER:
        feedback.append("Lower your chest more."); score -= 10
    if not feedback: feedback.append("Good form. Keep going.")

    state.feedback   = " ".join(feedback)
    state.form_score = max(0, min(100, score))
    return {"Elbow angle": elbow_angle, "Body angle": body_angle}, state


# ── Sit-up ────────────────────────────────────────────────────────────────────
# Gates:
#   1. Knees bent (knee angle < 130) — blocks standing/sitting on chair
#   2. Lying flat: |shoulder.y - hip.y| < 0.20 — blocks sitting upright on floor
# Torso angle = shoulder→hip→knee
#   DOWN (flat):   90° – 140°  (horizontal body, knees bent up)
#   UP   (curled): < 55°       (shoulder close to knee)

SITUP_DOWN_MIN    = 90
SITUP_DOWN_MAX    = 140
SITUP_UP_MAX      = 55
SITUP_KNEE_MAX    = 130
SITUP_PRONE_YDIFF = 0.20

def analyze_situp(landmarks, state):
    torso_angles, knee_angles = [], []
    shoulder_ys, hip_ys       = [], []

    for side in ["left", "right"]:
        if required_side_visible(landmarks, side, ["shoulder", "hip", "knee"]):
            p = get_side_points(landmarks, side)
            torso_angles.append(calculate_angle(p["shoulder"], p["hip"], p["knee"]))
            shoulder_ys.append(p["shoulder"][1])
            hip_ys.append(p["hip"][1])
        if required_side_visible(landmarks, side, ["hip", "knee", "ankle"]):
            p = get_side_points(landmarks, side)
            knee_angles.append(calculate_angle(p["hip"], p["knee"], p["ankle"]))

    torso_angle = _avg(torso_angles)
    knee_angle  = _avg(knee_angles)
    shoulder_y  = _avg(shoulder_ys)
    hip_y       = _avg(hip_ys)

    if torso_angle is None:
        return set_no_landmarks_feedback(
            state, "Lie flat on back, sideways to camera. Shoulder, hip and knee must be visible."
        )

    # Gate 1: knees bent
    if knee_angle is not None and knee_angle > SITUP_KNEE_MAX:
        state.position   = "UNKNOWN"
        state.feedback   = "Bend your knees (feet flat on floor) and lie on your back."
        state.form_score = 0
        return {"Torso angle": torso_angle, "Knee angle": knee_angle}, state

    # Gate 2: lying flat
    if shoulder_y is not None and hip_y is not None:
        y_diff = abs(shoulder_y - hip_y)
        if y_diff > SITUP_PRONE_YDIFF:
            state.position   = "UNKNOWN"
            state.feedback   = "Lie flat on your back — sit-ups require you to be on the floor."
            state.form_score = 0
            return {"Torso angle": torso_angle, "Knee angle": knee_angle}, state

    if SITUP_DOWN_MIN <= torso_angle <= SITUP_DOWN_MAX:
        if state.position == "UP":
            _count_rep_once(state)
        state.position = "DOWN"
    elif torso_angle < SITUP_UP_MAX:
        state.position = "UP"

    feedback, score = [], 100
    if state.position == "UNKNOWN": feedback.append("Lie flat, knees bent — then curl up.")
    elif state.position == "DOWN":  feedback.append("Flat. Now curl your torso up to your knees.")
    elif state.position == "UP":    feedback.append("Good crunch! Lower back down slowly.")

    state.feedback   = " ".join(feedback)
    state.form_score = max(0, min(100, score))
    return {"Torso angle": torso_angle, "Knee angle": knee_angle}, state


# ── Jumping Jack ──────────────────────────────────────────────────────────────
def analyze_jumping_jack(landmarks, state):
    required = [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_WRIST, RIGHT_WRIST, LEFT_ANKLE, RIGHT_ANKLE]

    if not all_visible(landmarks, required):
        return set_no_landmarks_feedback(state, "Move back. Wrists, shoulders, and ankles must be visible.")

    ls = landmark_xy(landmarks, LEFT_SHOULDER)
    rs = landmark_xy(landmarks, RIGHT_SHOULDER)
    lw = landmark_xy(landmarks, LEFT_WRIST)
    rw = landmark_xy(landmarks, RIGHT_WRIST)
    la = landmark_xy(landmarks, LEFT_ANKLE)
    ra = landmark_xy(landmarks, RIGHT_ANKLE)

    shoulder_width = max(abs(rs[0] - ls[0]), 0.01)
    foot_ratio     = abs(ra[0] - la[0]) / shoulder_width
    avg_wrist_y    = (lw[1] + rw[1]) / 2.0
    avg_shoulder_y = (ls[1] + rs[1]) / 2.0

    wrists_above = avg_wrist_y < avg_shoulder_y
    wrists_below = avg_wrist_y > avg_shoulder_y + 0.10
    is_open   = wrists_above and foot_ratio > JACK_OPEN_FOOT_MULTIPLIER
    is_closed = wrists_below and foot_ratio < JACK_CLOSED_FOOT_MULTIPLIER

    if is_open:
        if state.position == "CLOSED": _count_rep_once(state)
        state.position = "OPEN"
    elif is_closed:
        state.position = "CLOSED"

    feedback, score = [], 100
    if state.position == "UNKNOWN": feedback.append("Start closed, then jump open.")
    elif state.position == "CLOSED": feedback.append("Closed position. Jump open.")
    elif state.position == "OPEN":   feedback.append("Open position. Return closed.")
    if not wrists_above and state.position == "OPEN":
        feedback.append("Raise arms overhead."); score -= 20
    if foot_ratio < JACK_OPEN_FOOT_MULTIPLIER and state.position == "OPEN":
        feedback.append("Jump feet wider."); score -= 20

    state.feedback   = " ".join(feedback)
    state.form_score = max(0, min(100, score))
    return {"Foot ratio": foot_ratio, "Wrist height": avg_shoulder_y - avg_wrist_y}, state


# ── Plank ─────────────────────────────────────────────────────────────────────
def analyze_plank(landmarks, state):
    body_angles = []

    for side in ["left", "right"]:
        if required_side_visible(landmarks, side, ["shoulder", "hip", "ankle"]):
            p = get_side_points(landmarks, side)
            body_angles.append(calculate_angle(p["shoulder"], p["hip"], p["ankle"]))

    body_angle = average(body_angles) if body_angles else None

    if body_angle is None:
        return set_no_landmarks_feedback(state, "Side view. Keep shoulder, hip and ankle visible.")

    score, feedback = 100, []

    if body_angle >= PLANK_GOOD_BODY_ANGLE:
        if state.plank_start_time is None:
            state.plank_start_time = time.time()
        state.position      = "HOLD"
        state.plank_seconds = time.time() - state.plank_start_time
        state.best_plank_seconds = max(state.best_plank_seconds, state.plank_seconds)
        feedback.append("Good plank. Keep holding.")
        if body_angle < 170:
            feedback.append("Slight hip issue — keep body flat."); score -= 10
    else:
        state.position         = "RESET"
        state.plank_start_time = None
        state.plank_seconds    = 0.0
        if body_angle < 140:
            feedback.append("Hips too high or low. Straighten your body."); score -= 40
        else:
            feedback.append("Straighten your body to start."); score -= 20

    state.feedback   = " ".join(feedback)
    state.form_score = max(0, min(100, score))
    return {"Body angle": body_angle, "Hold seconds": state.plank_seconds}, state


# ── Lunge ─────────────────────────────────────────────────────────────────────
def analyze_lunge(landmarks, state):
    left_knee = right_knee = None
    torso_angles = []

    if required_side_visible(landmarks, "left", ["shoulder", "hip", "knee", "ankle"]):
        p = get_side_points(landmarks, "left")
        left_knee = calculate_angle(p["hip"], p["knee"], p["ankle"])
        torso_angles.append(calculate_angle(p["shoulder"], p["hip"], p["knee"]))

    if required_side_visible(landmarks, "right", ["shoulder", "hip", "knee", "ankle"]):
        p = get_side_points(landmarks, "right")
        right_knee = calculate_angle(p["hip"], p["knee"], p["ankle"])
        torso_angles.append(calculate_angle(p["shoulder"], p["hip"], p["knee"]))

    knee_angles  = [a for a in [left_knee, right_knee] if a is not None]
    torso_angle  = average(torso_angles) if torso_angles else None

    if len(knee_angles) < 2:
        return set_no_landmarks_feedback(state, "Move back. Both legs must be visible for lunges.")

    front_knee    = min(knee_angles)
    both_straight = left_knee > LUNGE_UP_KNEE_ANGLE and right_knee > LUNGE_UP_KNEE_ANGLE

    if both_straight:
        if state.position == "DOWN": _count_rep_once(state)
        state.position = "UP"
    elif front_knee < LUNGE_DOWN_KNEE_ANGLE:
        state.position = "DOWN"

    feedback, score = [], 100
    if state.position == "UNKNOWN": feedback.append("Step into a lunge, then stand tall.")
    elif state.position == "UP":    feedback.append("Standing tall. Start next lunge.")
    elif state.position == "DOWN":  feedback.append("Good lunge depth. Push back up.")
    if state.position == "DOWN":
        if front_knee < 75:    feedback.append("Don't overbend the front knee."); score -= 15
        elif front_knee > 105: feedback.append("Lower a little more."); score -= 15
    if torso_angle is not None and torso_angle < 55:
        feedback.append("Keep chest up."); score -= 20

    state.feedback   = " ".join(feedback)
    state.form_score = max(0, min(100, score))
    return {"Front knee": front_knee, "Left knee": left_knee, "Right knee": right_knee}, state


# ── Burpee ────────────────────────────────────────────────────────────────────
# DOWN = squat/floor (knee angle ≤ 115), UP = standing with wrists above shoulders
def analyze_burpee(landmarks, state):
    knee_angles = []
    for side in ["left", "right"]:
        if required_side_visible(landmarks, side, ["hip", "knee", "ankle"]):
            p = get_side_points(landmarks, side)
            knee_angles.append(calculate_angle(p["hip"], p["knee"], p["ankle"]))

    knee_angle = _avg(knee_angles)

    wrists_up = False
    try:
        lw = landmark_xy(landmarks, LEFT_WRIST)
        rw = landmark_xy(landmarks, RIGHT_WRIST)
        ls = landmark_xy(landmarks, LEFT_SHOULDER)
        rs = landmark_xy(landmarks, RIGHT_SHOULDER)
        avg_wrist_y    = (lw[1] + rw[1]) / 2.0
        avg_shoulder_y = (ls[1] + rs[1]) / 2.0
        wrists_up = avg_wrist_y < avg_shoulder_y - 0.05
    except Exception:
        pass

    if knee_angle is None and not wrists_up:
        return set_no_landmarks_feedback(state, "Move back so your full body is visible for burpees.")

    is_down = knee_angle is not None and knee_angle <= 115
    is_up   = wrists_up and (knee_angle is None or knee_angle > 140)

    if is_down:
        state.position = "DOWN"
    elif is_up:
        if state.position == "DOWN": _count_rep_once(state)
        state.position = "UP"

    feedback = []
    if state.position == "UNKNOWN": feedback.append("Stand, drop to floor, then jump up.")
    elif state.position == "DOWN":  feedback.append("Floor position. Push up and jump!")
    elif state.position == "UP":    feedback.append("Great jump! Drop back down.")

    state.feedback   = " ".join(feedback)
    state.form_score = 100
    return {"Knee angle": knee_angle}, state


# ── Mountain Climber ──────────────────────────────────────────────────────────
# Each knee drive counts as a half-rep; L + R = 1 full rep
def analyze_mountain_climber(landmarks, state):
    left_hip = right_hip = None

    if required_side_visible(landmarks, "left", ["shoulder", "hip", "knee"]):
        p = get_side_points(landmarks, "left")
        left_hip = calculate_angle(p["shoulder"], p["hip"], p["knee"])

    if required_side_visible(landmarks, "right", ["shoulder", "hip", "knee"]):
        p = get_side_points(landmarks, "right")
        right_hip = calculate_angle(p["shoulder"], p["hip"], p["knee"])

    if left_hip is None and right_hip is None:
        return set_no_landmarks_feedback(state, "Side view. Keep shoulder, hip and knee visible.")

    if not hasattr(state, "mc_last_driven"):  state.mc_last_driven = None
    if not hasattr(state, "mc_half_reps"):    state.mc_half_reps   = 0

    left_drive  = left_hip  is not None and left_hip  < 80
    right_drive = right_hip is not None and right_hip < 80

    if left_drive and state.mc_last_driven != "left":
        state.mc_last_driven = "left"
        state.mc_half_reps  += 1
    elif right_drive and state.mc_last_driven != "right":
        state.mc_last_driven = "right"
        state.mc_half_reps  += 1

    full_reps = state.mc_half_reps // 2
    if full_reps > state.reps:
        state.reps += full_reps - state.reps
        import time as _t; state.last_rep_time = _t.time()

    state.position = "LEFT" if left_drive else ("RIGHT" if right_drive else "HOLD")

    feedback = []
    if state.position == "HOLD":   feedback.append("Drive knees to chest alternately.")
    elif state.position == "LEFT": feedback.append("Left knee in. Switch!")
    elif state.position == "RIGHT":feedback.append("Right knee in. Switch!")

    state.feedback   = " ".join(feedback)
    state.form_score = 100
    return {"Left hip": left_hip, "Right hip": right_hip}, state


# ── Dispatcher ────────────────────────────────────────────────────────────────
def analyze_exercise(landmarks, state):
    if state.exercise == "Squat":            return analyze_squat(landmarks, state)
    if state.exercise == "Push-up":          return analyze_pushup(landmarks, state)
    if state.exercise == "Sit-up":           return analyze_situp(landmarks, state)
    if state.exercise == "Jumping Jack":     return analyze_jumping_jack(landmarks, state)
    if state.exercise == "Plank":            return analyze_plank(landmarks, state)
    if state.exercise == "Lunge":            return analyze_lunge(landmarks, state)
    if state.exercise == "Burpee":           return analyze_burpee(landmarks, state)
    if state.exercise == "Mountain Climber": return analyze_mountain_climber(landmarks, state)

    state.feedback   = f"Unknown exercise: {state.exercise}"
    state.form_score = 0
    return {}, state
