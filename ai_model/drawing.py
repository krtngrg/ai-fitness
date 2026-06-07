import cv2
import numpy as np

from landmarks import POSE_CONNECTIONS
from pose_helpers import landmark_visible

# BGR colors
C_BG = (12, 14, 20)
C_PANEL = (20, 22, 30)
C_ACCENT = (99, 202, 183)
C_WHITE = (238, 238, 245)
C_MUTED = (145, 145, 160)
C_GREEN = (80, 220, 110)
C_YELLOW = (40, 210, 240)
C_RED = (80, 80, 230)
C_DARK = (8, 9, 12)

C_SKEL_LINE = (80, 220, 120)
C_SKEL_DOT = (40, 230, 240)


def setup_camera_window(window_name, width=1280, height=720, fullscreen=False):
    flags = cv2.WINDOW_NORMAL | getattr(cv2, "WINDOW_GUI_NORMAL", 0)

    try:
        cv2.namedWindow(window_name, flags)
    except cv2.error:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    if fullscreen:
        cv2.setWindowProperty(
            window_name,
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN,
        )
    else:
        cv2.resizeWindow(window_name, width, height)


def _alpha_rect(frame, x1, y1, x2, y2, color, alpha=0.72):
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w - 1, x2), min(h - 1, y2)

    if x2 <= x1 or y2 <= y1:
        return

    ov = frame.copy()
    cv2.rectangle(ov, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, frame)


def _rrect(frame, x1, y1, x2, y2, color, alpha=0.78, r=12):
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w - 1, x2), min(h - 1, y2)

    if x2 <= x1 or y2 <= y1:
        return

    r = max(1, min(r, (x2 - x1) // 2, (y2 - y1) // 2))

    ov = frame.copy()
    cv2.rectangle(ov, (x1 + r, y1), (x2 - r, y2), color, -1)
    cv2.rectangle(ov, (x1, y1 + r), (x2, y2 - r), color, -1)

    for cx, cy in [
        (x1 + r, y1 + r),
        (x2 - r, y1 + r),
        (x1 + r, y2 - r),
        (x2 - r, y2 - r),
    ]:
        cv2.circle(ov, (cx, cy), r, color, -1)

    cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, frame)


def _bar(frame, x, y, w, h, pct, fg, bg=(45, 46, 56)):
    pct = 0.0 if pct is None else max(0.0, min(float(pct), 1.0))
    cv2.rectangle(frame, (x, y), (x + w, y + h), bg, -1)

    fill_w = int(w * pct)
    if fill_w > 0:
        cv2.rectangle(frame, (x, y), (x + fill_w, y + h), fg, -1)


def _t(frame, text, x, y, scale=0.55, color=C_WHITE, bold=False):
    text = str(text)
    cv2.putText(
        frame,
        text,
        (int(x), int(y)),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        2 if bold else 1,
        cv2.LINE_AA,
    )


def _ellipsis(text, max_chars):
    text = str(text).replace("\n", " ").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _text_size(text, scale=0.55, bold=False):
    return cv2.getTextSize(
        str(text),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        2 if bold else 1,
    )[0]


def normalized_to_pixel(lm, w, h):
    return int(lm.x * w), int(lm.y * h)


def draw_pose(frame, landmarks):
    h, w, _ = frame.shape

    for s, e in POSE_CONNECTIONS:
        if s >= len(landmarks) or e >= len(landmarks):
            continue
        if not landmark_visible(landmarks, s) or not landmark_visible(landmarks, e):
            continue

        x1, y1 = normalized_to_pixel(landmarks[s], w, h)
        x2, y2 = normalized_to_pixel(landmarks[e], w, h)

        cv2.line(frame, (x1, y1), (x2, y2), C_SKEL_LINE, 2, cv2.LINE_AA)

    for i, lm in enumerate(landmarks):
        if not landmark_visible(landmarks, i):
            continue

        x, y = normalized_to_pixel(lm, w, h)
        cv2.circle(frame, (x, y), 4, C_SKEL_DOT, -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 4, C_WHITE, 1, cv2.LINE_AA)


def format_metric(v):
    return "--" if v is None else f"{v:.1f}"


def _stat_card(frame, x, y, w, h, label, value, accent=C_ACCENT, progress=None):
    _rrect(frame, x, y, x + w, y + h, C_PANEL, alpha=0.84, r=14)

    _t(frame, label.upper(), x + 14, y + 22, scale=0.42, color=C_MUTED, bold=True)
    _t(frame, value, x + 14, y + 55, scale=0.82, color=C_WHITE, bold=True)

    if progress is not None:
        _bar(frame, x + 14, y + h - 13, w - 28, 5, progress, accent)

    cv2.circle(frame, (x + w - 18, y + 18), 5, accent, -1, cv2.LINE_AA)


def draw_info_panel(
    frame,
    state,
    metrics,
    calories_burned,
    current_set=1,
    total_sets=1,
    planned_reps=None,
    planned_duration=None,
    elapsed=0.0,
):
    h, w, _ = frame.shape

    margin = 14
    top_h = 104

    # Top HUD background
    _rrect(frame, margin, margin, w - margin, margin + top_h, C_BG, alpha=0.62, r=18)

    # Brand / exercise block
    brand_x = margin + 18
    _t(frame, "MoveMate AI", brand_x, margin + 29, scale=0.62, color=C_ACCENT, bold=True)
    _t(frame, state.exercise.upper(), brand_x, margin + 63, scale=0.72, color=C_WHITE, bold=True)

    badge_color = {
        "UP": C_GREEN,
        "DOWN": C_YELLOW,
        "HOLD": C_GREEN,
        "CLOSED": C_YELLOW,
        "OPEN": C_ACCENT,
        "RESET": C_RED,
        "UNKNOWN": C_MUTED,
    }.get(state.position, C_MUTED)

    _rrect(frame, brand_x, margin + 72, brand_x + 112, margin + 96, badge_color, alpha=0.92, r=8)
    _t(frame, state.position, brand_x + 11, margin + 90, scale=0.46, color=C_DARK, bold=True)

    # Main cards
    card_y = margin + 16
    card_h = 74
    gap = 10
    start_x = 210

    available = w - start_x - margin - gap * 3
    card_w = max(118, min(165, available // 4))

    if state.exercise == "Plank":
        main_value = f"{state.plank_seconds:.0f}s"
        main_label = "hold"
        main_progress = None
        if planned_duration:
            main_progress = elapsed / max(1, planned_duration)
    else:
        main_value = str(state.reps)
        main_label = "reps"
        main_progress = None
        if planned_reps:
            main_value = f"{state.reps}/{planned_reps}"
            main_progress = state.reps / max(1, planned_reps)

    form_score = int(max(0, min(100, state.form_score)))
    form_color = C_GREEN if form_score >= 80 else C_YELLOW if form_score >= 50 else C_RED

    cards = [
        (main_label, main_value, C_ACCENT, main_progress),
        ("set", f"{current_set}/{total_sets}", C_GREEN, current_set / max(1, total_sets)),
        ("form", f"{form_score}%", form_color, form_score / 100),
        ("kcal", f"{calories_burned:.2f}", C_YELLOW, None),
    ]

    x = start_x
    for label, value, color, progress in cards:
        _stat_card(frame, x, card_y, card_w, card_h, label, value, color, progress)
        x += card_w + gap

    # Set dots under set card area
    dot_start = start_x + card_w + gap + 14
    dot_y = margin + top_h - 13
    for i in range(min(total_sets, 10)):
        color = C_GREEN if i < current_set - 1 else C_ACCENT if i == current_set - 1 else (60, 62, 72)
        cv2.circle(frame, (dot_start + i * 14, dot_y), 4, color, -1, cv2.LINE_AA)

    # Feedback pill
    fb = _ellipsis(state.feedback, 82)
    tw, th = _text_size(fb, scale=0.56, bold=True)
    pill_w = min(w - 2 * margin, tw + 42)
    pill_x = max(margin, (w - pill_w) // 2)
    pill_y = h - 70

    _rrect(frame, pill_x, pill_y, pill_x + pill_w, pill_y + 42, C_BG, alpha=0.76, r=16)
    cv2.circle(frame, (pill_x + 20, pill_y + 21), 5, C_ACCENT, -1, cv2.LINE_AA)
    _t(frame, fb, pill_x + 34, pill_y + 28, scale=0.56, color=C_YELLOW, bold=True)

    # Compact metrics bottom-left
    if metrics:
        items = list(metrics.items())[:2]
        box_w = 285
        box_h = 32 + 22 * len(items)
        box_x = margin
        box_y = h - 88 - box_h

        _rrect(frame, box_x, box_y, box_x + box_w, box_y + box_h, C_BG, alpha=0.52, r=12)
        _t(frame, "LIVE METRICS", box_x + 14, box_y + 22, scale=0.42, color=C_MUTED, bold=True)

        yy = box_y + 47
        for label, val in items:
            short = label.replace(" angle", " deg").replace(" seconds", "s").replace(" ratio", "")
            _t(frame, f"{short}: {format_metric(val)}", box_x + 14, yy, scale=0.46, color=C_WHITE)
            yy += 22

    # Controls
    _t(frame, "Q quit   N next set   R reset   C calories", margin, h - 12, scale=0.42, color=(95, 95, 110))


def draw_set_complete_screen(frame, current_set, total_sets, reps_done, planned_reps, calories):
    h, w, _ = frame.shape
    _alpha_rect(frame, 0, 0, w, h, (8, 9, 12), alpha=0.72)

    bx, by, bw, bh = w // 2 - 240, h // 2 - 145, 480, 290
    _rrect(frame, bx, by, bx + bw, by + bh, C_PANEL, alpha=0.96, r=22)

    cx, cy = bx + bw // 2, by + 58
    cv2.circle(frame, (cx, cy), 34, C_GREEN, -1, cv2.LINE_AA)

    # Draw check mark without unicode
    cv2.line(frame, (cx - 15, cy), (cx - 4, cy + 12), C_DARK, 4, cv2.LINE_AA)
    cv2.line(frame, (cx - 4, cy + 12), (cx + 17, cy - 14), C_DARK, 4, cv2.LINE_AA)

    _t(frame, f"SET {current_set} COMPLETE", bx + 118, by + 120, scale=0.82, color=C_WHITE, bold=True)
    _t(frame, f"Reps: {reps_done} / {planned_reps or reps_done}", bx + 160, by + 156, scale=0.58, color=C_MUTED)
    _t(frame, f"Calories: {calories:.2f} kcal", bx + 148, by + 184, scale=0.58, color=C_ACCENT, bold=True)

    next_set = current_set + 1
    remaining = total_sets - current_set
    _t(frame, f"{remaining} set{'s' if remaining != 1 else ''} remaining", bx + 160, by + 216, scale=0.52, color=C_MUTED)

    _rrect(frame, bx + 130, by + 236, bx + bw - 130, by + 270, C_ACCENT, alpha=0.92, r=10)
    _t(frame, f"Press N - Start Set {next_set}", bx + 148, by + 259, scale=0.52, color=C_DARK, bold=True)


def draw_all_sets_done_screen(frame, exercise_name, total_sets, total_reps, calories):
    h, w, _ = frame.shape
    _alpha_rect(frame, 0, 0, w, h, (8, 9, 12), alpha=0.74)

    bx, by, bw, bh = w // 2 - 250, h // 2 - 165, 500, 330
    _rrect(frame, bx, by, bx + bw, by + bh, C_PANEL, alpha=0.96, r=22)

    cx, cy = bx + bw // 2, by + 62
    cv2.circle(frame, (cx, cy), 38, C_ACCENT, -1, cv2.LINE_AA)
    _t(frame, "OK", cx - 19, cy + 10, scale=0.72, color=C_DARK, bold=True)

    _t(frame, "WORKOUT COMPLETE", bx + 108, by + 128, scale=0.86, color=C_GREEN, bold=True)
    _t(frame, exercise_name, bx + 205, by + 158, scale=0.58, color=C_MUTED)

    cv2.line(frame, (bx + 28, by + 178), (bx + bw - 28, by + 178), (50, 52, 62), 1)

    stats = [
        ("Sets", str(total_sets)),
        ("Reps", str(total_reps)),
        ("Calories", f"{calories:.1f}"),
    ]

    sx = bx + 52
    for label, val in stats:
        _t(frame, label, sx, by + 213, scale=0.48, color=C_MUTED, bold=True)
        _t(frame, val, sx, by + 247, scale=0.76, color=C_WHITE, bold=True)
        sx += 150

    _t(frame, "Great work! Saving results...", bx + 132, by + 288, scale=0.54, color=C_ACCENT, bold=True)