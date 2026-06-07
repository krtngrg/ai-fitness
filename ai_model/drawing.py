import cv2
import numpy as np

from landmarks import POSE_CONNECTIONS
from pose_helpers import landmark_visible

# ── Palette ─────────────────────────────────────────────────────────────────
C_BG      = (15, 15, 20)
C_ACCENT  = (99, 202, 183)
C_WHITE   = (235, 235, 245)
C_GREY    = (130, 130, 145)
C_GREEN   = (80, 220, 100)
C_YELLOW  = (40, 210, 240)
C_RED     = (80,  80, 220)
C_SKEL_L  = (80, 220, 120)
C_SKEL_D  = (40, 230, 240)


def _alpha_rect(frame, x1, y1, x2, y2, color, alpha=0.72):
    ov = frame.copy()
    cv2.rectangle(ov, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, frame)


def _rrect(frame, x1, y1, x2, y2, color, alpha=0.78, r=10):
    ov = frame.copy()
    cv2.rectangle(ov, (x1+r, y1), (x2-r, y2), color, -1)
    cv2.rectangle(ov, (x1, y1+r), (x2, y2-r), color, -1)
    for cx, cy in [(x1+r,y1+r),(x2-r,y1+r),(x1+r,y2-r),(x2-r,y2-r)]:
        cv2.circle(ov, (cx, cy), r, color, -1)
    cv2.addWeighted(ov, alpha, frame, 1 - alpha, 0, frame)


def _bar(frame, x, y, w, h, pct, fg, bg=(40,40,50)):
    cv2.rectangle(frame, (x, y), (x+w, y+h), bg, -1)
    cv2.rectangle(frame, (x, y), (x+max(2,int(w*min(pct,1.0))), y+h), fg, -1)


def _t(frame, text, x, y, scale=0.55, color=C_WHITE, bold=False):
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                scale, color, 2 if bold else 1, cv2.LINE_AA)


def normalized_to_pixel(lm, w, h):
    return int(lm.x * w), int(lm.y * h)


def draw_pose(frame, landmarks):
    h, w, _ = frame.shape
    for s, e in POSE_CONNECTIONS:
        if s >= len(landmarks) or e >= len(landmarks): continue
        if not landmark_visible(landmarks, s) or not landmark_visible(landmarks, e): continue
        x1,y1 = normalized_to_pixel(landmarks[s], w, h)
        x2,y2 = normalized_to_pixel(landmarks[e], w, h)
        cv2.line(frame, (x1,y1), (x2,y2), C_SKEL_L, 2, cv2.LINE_AA)
    for i, lm in enumerate(landmarks):
        if not landmark_visible(landmarks, i): continue
        x, y = normalized_to_pixel(lm, w, h)
        cv2.circle(frame, (x,y), 5, C_SKEL_D, -1, cv2.LINE_AA)
        cv2.circle(frame, (x,y), 5, C_WHITE, 1, cv2.LINE_AA)


def format_metric(v):
    return "--" if v is None else f"{v:.1f}"


def draw_info_panel(frame, state, metrics, calories_burned,
                    current_set=1, total_sets=1,
                    planned_reps=None, planned_duration=None, elapsed=0.0):
    h, w, _ = frame.shape

    # ── LEFT PANEL ──────────────────────────────────────────────────────────
    px, py, pw, ph = 12, 12, 275, 330
    _rrect(frame, px, py, px+pw, py+ph, C_BG, alpha=0.82)

    # Brand
    _t(frame, "MoveMate AI", px+14, py+28, scale=0.62, color=C_ACCENT, bold=True)
    cv2.line(frame, (px+10, py+36), (px+pw-10, py+36), (50,50,60), 1)

    # Exercise name
    _t(frame, state.exercise.upper(), px+14, py+60, scale=0.78, color=C_WHITE, bold=True)

    # State badge
    bc = {"UP":C_GREEN,"DOWN":C_YELLOW,"HOLD":C_GREEN,
          "CLOSED":C_YELLOW,"OPEN":C_ACCENT,"RESET":C_RED}.get(state.position, C_GREY)
    _rrect(frame, px+14, py+68, px+105, py+88, bc, alpha=0.90, r=6)
    _t(frame, state.position, px+22, py+83, scale=0.46, color=(10,10,15), bold=True)

    # ── BIG REP COUNTER + target ─────────────────────────────────────────
    rep_str = str(state.reps) if state.exercise != "Plank" else f"{state.plank_seconds:.0f}s"
    _t(frame, rep_str, px+14, py+142, scale=1.8, color=C_WHITE, bold=True)

    if planned_reps:
        _t(frame, f"/ {planned_reps}", px+80, py+142, scale=1.0, color=C_GREY)
        # Rep progress bar
        pct = state.reps / planned_reps
        bar_color = C_GREEN if pct >= 1.0 else C_ACCENT
        _bar(frame, px+14, py+150, pw-28, 7, pct, bar_color)
    elif planned_duration:
        remaining = max(0, planned_duration - elapsed)
        _t(frame, f"{remaining:.0f}s left", px+80, py+132, scale=0.50, color=C_GREY)
        _bar(frame, px+14, py+150, pw-28, 7, elapsed/planned_duration, C_ACCENT)

    _t(frame, "reps" if state.exercise != "Plank" else "hold", px+14, py+168, scale=0.44, color=C_GREY)

    # Calories
    _t(frame, f"{calories_burned:.2f}", px+150, py+142, scale=1.1, color=C_ACCENT, bold=True)
    _t(frame, "kcal", px+150, py+162, scale=0.44, color=C_GREY)

    # Form score bar
    sc = state.form_score
    sc_col = C_GREEN if sc >= 80 else (C_YELLOW if sc >= 50 else C_RED)
    _t(frame, f"Form  {sc}/100", px+14, py+192, scale=0.48, color=C_GREY)
    _bar(frame, px+14, py+200, pw-28, 7, sc/100, sc_col)

    # Metrics
    my = py+222
    for label, val in list(metrics.items())[:2]:
        short = label.replace(" angle","°").replace(" seconds","s").replace(" ratio","")
        _t(frame, f"{short}: {format_metric(val)}", px+14, my, scale=0.44, color=C_GREY)
        my += 18

    # ── TOP-RIGHT: Set indicator ─────────────────────────────────────────
    # e.g.  SET  2 / 3
    sx = w - 180
    _rrect(frame, sx, 12, sx+168, 74, C_BG, alpha=0.82)
    _t(frame, "SET", sx+12, py+30, scale=0.50, color=C_GREY)
    set_str = f"{current_set} / {total_sets}"
    _t(frame, set_str, sx+50, py+30, scale=0.72, color=C_WHITE, bold=True)
    # Dots
    dot_x = sx+12
    for i in range(total_sets):
        color = C_GREEN if i < current_set - 1 else (C_ACCENT if i == current_set-1 else (50,50,60))
        cv2.circle(frame, (dot_x+8, py+48), 6, color, -1, cv2.LINE_AA)
        dot_x += 20

    # ── FEEDBACK pill (bottom-centre) ───────────────────────────────────
    fb = state.feedback[:80]
    (tw, _), _ = cv2.getTextSize(fb, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
    fx = max(10, (w - tw)//2 - 16)
    fy = h - 52
    _rrect(frame, fx, fy, fx+tw+32, fy+34, C_BG, alpha=0.85)
    cv2.line(frame, (fx+8, fy), (fx+11, fy), C_ACCENT, 3)
    _t(frame, fb, fx+16, fy+22, scale=0.52, color=C_YELLOW)

    # Key hints
    _t(frame, "Q quit  N next-set  R reset  C calories", 10, h-12, scale=0.40, color=(70,70,85))


def draw_set_complete_screen(frame, current_set, total_sets, reps_done, planned_reps, calories):
    """Overlay shown between sets."""
    h, w, _ = frame.shape
    _alpha_rect(frame, 0, 0, w, h, (10,10,15), alpha=0.70)

    bx, by, bw, bh = w//2 - 220, h//2 - 140, 440, 280
    _rrect(frame, bx, by, bx+bw, by+bh, (20,22,28), alpha=0.96, r=16)

    # Tick icon (circle + check)
    cx, cy = bx+bw//2, by+52
    cv2.circle(frame, (cx, cy), 30, C_GREEN, -1, cv2.LINE_AA)
    cv2.putText(frame, "✓", (cx-12, cy+10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (10,10,15), 2, cv2.LINE_AA)

    _t(frame, f"SET {current_set} COMPLETE!", bx+bw//2-110, by+104, scale=0.80, color=C_WHITE, bold=True)
    _t(frame, f"Reps done: {reps_done} / {planned_reps or reps_done}",
       bx+bw//2-90, by+138, scale=0.58, color=C_GREY)
    _t(frame, f"Calories so far: {calories:.2f} kcal",
       bx+bw//2-90, by+162, scale=0.54, color=C_ACCENT)

    next_set = current_set + 1
    remaining = total_sets - current_set
    _t(frame, f"{remaining} set{'s' if remaining>1 else ''} remaining",
       bx+bw//2-70, by+196, scale=0.52, color=C_GREY)

    # Next button hint
    _rrect(frame, bx+bw//2-80, by+216, bx+bw//2+80, by+248, C_ACCENT, alpha=0.90, r=8)
    _t(frame, f"Press N — Start Set {next_set}", bx+bw//2-74, by+238, scale=0.50, color=(10,10,15), bold=True)


def draw_all_sets_done_screen(frame, exercise_name, total_sets, total_reps, calories):
    """Overlay shown when all sets are completed."""
    h, w, _ = frame.shape
    _alpha_rect(frame, 0, 0, w, h, (10,10,15), alpha=0.72)

    bx, by, bw, bh = w//2 - 230, h//2 - 160, 460, 320
    _rrect(frame, bx, by, bx+bw, by+bh, (20,22,28), alpha=0.96, r=16)

    # Trophy
    cv2.circle(frame, (bx+bw//2, by+54), 34, C_ACCENT, -1, cv2.LINE_AA)
    _t(frame, "!", (bx+bw//2)-6, by+64, scale=1.0, color=(10,10,15), bold=True)

    _t(frame, "WORKOUT COMPLETE!", bx+bw//2-130, by+108, scale=0.85, color=C_GREEN, bold=True)
    _t(frame, exercise_name, bx+bw//2-60, by+136, scale=0.60, color=C_GREY)

    cv2.line(frame, (bx+20, by+148), (bx+bw-20, by+148), (40,40,50), 1)

    # Stats grid
    stats = [
        ("Sets",    str(total_sets)),
        ("Reps",    str(total_reps)),
        ("Calories",f"{calories:.1f} kcal"),
    ]
    sx = bx + 30
    for label, val in stats:
        _t(frame, label, sx, by+176, scale=0.46, color=C_GREY)
        _t(frame, val,   sx, by+202, scale=0.68, color=C_WHITE, bold=True)
        sx += bw // 3

    _t(frame, "Great work! Results are being saved...",
       bx+40, by+238, scale=0.50, color=C_ACCENT)
    _t(frame, "Window closes automatically.",
       bx+80, by+264, scale=0.46, color=C_GREY)
