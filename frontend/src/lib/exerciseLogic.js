/**
 * exerciseLogic.js
 * Browser port of ai_model/exercise_logic.py + pose_helpers.py + config.py
 *
 * Exercises supported: Squat, Push-up, Sit-up, Jumping Jack, Plank,
 *                      Lunge, Burpee, Mountain Climber
 */

// ─── LANDMARK INDICES ────────────────────────────────────────────────────────
export const LM = {
  NOSE: 0,
  LEFT_SHOULDER: 11, RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,    RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,    RIGHT_WRIST: 16,
  LEFT_HIP: 23,      RIGHT_HIP: 24,
  LEFT_KNEE: 25,     RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,    RIGHT_ANKLE: 28,
  LEFT_HEEL: 29,     RIGHT_HEEL: 30,
  LEFT_FOOT_INDEX: 31, RIGHT_FOOT_INDEX: 32,
};

export const POSE_CONNECTIONS = [
  [LM.LEFT_SHOULDER,  LM.RIGHT_SHOULDER],
  [LM.LEFT_SHOULDER,  LM.LEFT_ELBOW],
  [LM.LEFT_ELBOW,     LM.LEFT_WRIST],
  [LM.RIGHT_SHOULDER, LM.RIGHT_ELBOW],
  [LM.RIGHT_ELBOW,    LM.RIGHT_WRIST],
  [LM.LEFT_SHOULDER,  LM.LEFT_HIP],
  [LM.RIGHT_SHOULDER, LM.RIGHT_HIP],
  [LM.LEFT_HIP,       LM.RIGHT_HIP],
  [LM.LEFT_HIP,       LM.LEFT_KNEE],
  [LM.LEFT_KNEE,      LM.LEFT_ANKLE],
  [LM.LEFT_ANKLE,     LM.LEFT_HEEL],
  [LM.LEFT_HEEL,      LM.LEFT_FOOT_INDEX],
  [LM.RIGHT_HIP,      LM.RIGHT_KNEE],
  [LM.RIGHT_KNEE,     LM.RIGHT_ANKLE],
  [LM.RIGHT_ANKLE,    LM.RIGHT_HEEL],
  [LM.RIGHT_HEEL,     LM.RIGHT_FOOT_INDEX],
];

// ─── CONFIG ───────────────────────────────────────────────────────────────────
const MIN_VISIBILITY = 0.05;

const SQUAT_DOWN_KNEE_ANGLE   = 105;
const SQUAT_UP_KNEE_ANGLE     = 160;
const PUSHUP_DOWN_ELBOW_ANGLE = 95;
const PUSHUP_UP_ELBOW_ANGLE   = 155;
const JACK_OPEN_FOOT_MULT     = 1.25;
const JACK_CLOSED_FOOT_MULT   = 1.00;
const PLANK_GOOD_BODY_ANGLE   = 160;
const LUNGE_DOWN_KNEE_ANGLE   = 115;
const LUNGE_UP_KNEE_ANGLE     = 155;
const SITUP_DOWN_HIP_ANGLE    = 70;   // torso curled (up position for sit-up)
const SITUP_UP_HIP_ANGLE      = 120;  // torso flat (down/start position)

// More forgiving thresholds
const SQUAT_DOWN_TRIGGER  = Math.max(SQUAT_DOWN_KNEE_ANGLE, 125);
const SQUAT_UP_TRIGGER    = Math.min(SQUAT_UP_KNEE_ANGLE, 155);
const PUSHUP_DOWN_TRIGGER = Math.max(PUSHUP_DOWN_ELBOW_ANGLE, 115);
const PUSHUP_UP_TRIGGER   = Math.min(PUSHUP_UP_ELBOW_ANGLE, 145);

const REP_COOLDOWN_MS = 350;

// ─── CALORIE CONSTANTS ───────────────────────────────────────────────────────
export const CALORIES_PER_REP = {
  "Squat":           0.32,
  "Push-up":         0.29,
  "Jumping Jack":    0.20,
  "Lunge":           0.30,
  "Sit-up":          0.25,
  "Burpee":          0.50,
  "Mountain Climber":0.18,
};
export const PLANK_CALORIES_PER_SECOND = 0.06;

// ─── POSE HELPERS ─────────────────────────────────────────────────────────────

export function calculateAngle(a, b, c) {
  const radians =
    Math.atan2(c[1] - b[1], c[0] - b[0]) -
    Math.atan2(a[1] - b[1], a[0] - b[0]);
  let angle = Math.abs((radians * 180.0) / Math.PI);
  if (angle > 180) angle = 360 - angle;
  return angle;
}

function lmXY(landmarks, idx) {
  const lm = landmarks[idx];
  return [lm.x, lm.y];
}

function lmVisible(landmarks, idx) {
  const lm = landmarks[idx];
  if (!lm) return false;
  if (lm.x < -0.2 || lm.x > 1.2) return false;
  if (lm.y < -0.2 || lm.y > 1.2) return false;
  const vis = lm.visibility ?? 1.0;
  const pre = lm.presence ?? 1.0;
  return vis >= MIN_VISIBILITY && pre >= MIN_VISIBILITY;
}

function allVisible(landmarks, indices) {
  return indices.every((i) => lmVisible(landmarks, i));
}

const SIDE_MAP = {
  left: {
    shoulder: LM.LEFT_SHOULDER, elbow: LM.LEFT_ELBOW,
    wrist: LM.LEFT_WRIST, hip: LM.LEFT_HIP,
    knee: LM.LEFT_KNEE, ankle: LM.LEFT_ANKLE,
  },
  right: {
    shoulder: LM.RIGHT_SHOULDER, elbow: LM.RIGHT_ELBOW,
    wrist: LM.RIGHT_WRIST, hip: LM.RIGHT_HIP,
    knee: LM.RIGHT_KNEE, ankle: LM.RIGHT_ANKLE,
  },
};

function sideVisible(landmarks, side, parts) {
  const map = SIDE_MAP[side];
  return allVisible(landmarks, parts.map((p) => map[p]));
}

function getSidePoints(landmarks, side) {
  const map = SIDE_MAP[side];
  const result = {};
  for (const [part, idx] of Object.entries(map)) {
    result[part] = lmXY(landmarks, idx);
  }
  return result;
}

function avg(arr) {
  const clean = arr.filter((v) => v != null);
  if (!clean.length) return null;
  return clean.reduce((a, b) => a + b, 0) / clean.length;
}

function minVal(arr) {
  const clean = arr.filter((v) => v != null);
  if (!clean.length) return null;
  return Math.min(...clean);
}

function noLandmarks(state, msg) {
  state.feedback = msg;
  state.formScore = 0;
  if (state.exercise === "Plank") {
    state.plankStartTime = null;
    state.plankSeconds = 0;
    state.plankCountdownStartTime = null;
    state.plankCountdownDone = false;
  }
  return { metrics: {}, state };
}

function countRep(state, nowMs) {
  const last = state.lastRepTime || 0;
  if (nowMs - last >= REP_COOLDOWN_MS) {
    state.reps += 1;
    state.lastRepTime = nowMs;
    return true;
  }
  return false;
}

// ─── STATE FACTORY ────────────────────────────────────────────────────────────

export function createState(exercise) {
  return {
    exercise,
    position: "UNKNOWN",
    reps: 0,
    bestDepthAngle: 999,
    // Plank specific
    plankStartTime: null,
    plankSeconds: 0,
    bestPlankSeconds: 0,
    plankCountdownStartTime: null, // when the user first got into good position
    plankCountdownDone: false,     // countdown finished, timer running
    plankFormBad: false,           // true when form is currently broken
    plankLastAlarmMs: 0,           // last time alarm fired (ms)
    // General
    feedback: "Stand where your full body is visible.",
    formScore: 100,
    lastRepTime: 0,
  };
}

// ─── SQUAT ───────────────────────────────────────────────────────────────────

function analyzeSquat(landmarks, state, nowMs) {
  const kneeAngles = [], hipAngles = [];

  for (const side of ["left", "right"]) {
    if (sideVisible(landmarks, side, ["shoulder", "hip", "knee", "ankle"])) {
      const p = getSidePoints(landmarks, side);
      kneeAngles.push(calculateAngle(p.hip, p.knee, p.ankle));
      hipAngles.push(calculateAngle(p.shoulder, p.hip, p.knee));
    }
  }

  const kneeAngle = minVal(kneeAngles);
  const avgKnee   = avg(kneeAngles);
  const hipAngle  = avg(hipAngles);

  if (kneeAngle == null) {
    return noLandmarks(state, "Move back. Keep hips, knees, and ankles visible.");
  }

  if (kneeAngle < state.bestDepthAngle) state.bestDepthAngle = kneeAngle;

  if (kneeAngle <= SQUAT_DOWN_TRIGGER) {
    state.position = "DOWN";
  } else if ((avgKnee ?? kneeAngle) >= SQUAT_UP_TRIGGER) {
    if (state.position === "DOWN") { countRep(state, nowMs); state.bestDepthAngle = 999; }
    state.position = "UP";
  }

  let score = 100;
  const feedbacks = [];

  if (state.position === "UNKNOWN") feedbacks.push("Start standing tall, then squat.");
  else if (state.position === "UP")   feedbacks.push("Standing tall. Start next rep.");
  else if (state.position === "DOWN") feedbacks.push("Good depth. Push back up.");

  if (state.position !== "DOWN" && kneeAngle > SQUAT_DOWN_TRIGGER) { feedbacks.push("Go lower."); score -= 10; }
  if (hipAngle != null && hipAngle < 55) { feedbacks.push("Keep chest up."); score -= 20; }
  if (!feedbacks.length) feedbacks.push("Move with control.");

  state.feedback  = feedbacks.join(" ");
  state.formScore = Math.max(0, Math.min(100, score));

  return { metrics: { "Knee angle": kneeAngle, "Hip angle": hipAngle }, state };
}

// ─── PUSH-UP ──────────────────────────────────────────────────────────────────
// Requires body to be HORIZONTAL (prone position) before counting reps.
// Body is horizontal when shoulders and hips are at similar vertical (Y) positions.
// This prevents counting when standing, sitting or bending over.
//
// PRONE check: |shoulder.y - ankle.y| < 0.35  (normalized coords)
//              body angle between shoulder→hip→ankle must be > 140° (straight body)

const PUSHUP_MIN_BODY_ANGLE   = 140;  // body must be this straight to count
const PUSHUP_PRONE_Y_DIFF     = 0.35; // shoulder and ankle must be within this vertically

function analyzePushup(landmarks, state, nowMs) {
  const elbowAngles = [], bodyAngles = [];
  const shoulderYs  = [], ankleYs   = [];

  for (const side of ["left", "right"]) {
    if (sideVisible(landmarks, side, ["shoulder", "elbow", "wrist", "hip", "ankle"])) {
      const p = getSidePoints(landmarks, side);
      elbowAngles.push(calculateAngle(p.shoulder, p.elbow, p.wrist));
      bodyAngles.push(calculateAngle(p.shoulder, p.hip, p.ankle));
      shoulderYs.push(p.shoulder[1]);
      ankleYs.push(p.ankle[1]);
    }
  }

  const elbowAngle = avg(elbowAngles);
  const bodyAngle  = avg(bodyAngles);
  const shoulderY  = avg(shoulderYs);
  const ankleY     = avg(ankleYs);

  if (elbowAngle == null) {
    return noLandmarks(state, "Side view needed. Keep shoulder, elbow, wrist, hip and ankle visible.");
  }

  // ── Gate: person must be in prone (lying down) position ──────────────────
  // In MediaPipe Y coords: 0 = top of frame, 1 = bottom.
  // When lying flat, shoulder Y and ankle Y are close together (both ~0.5).
  // When standing, shoulder is near 0.2–0.4 and ankle near 0.8–1.0 → big diff.
  const yDiff       = Math.abs((ankleY ?? 1) - (shoulderY ?? 0));
  const isProne     = yDiff < PUSHUP_PRONE_Y_DIFF && (bodyAngle == null || bodyAngle > PUSHUP_MIN_BODY_ANGLE);

  if (!isProne) {
    // Reset state so no phantom reps accumulate
    state.position  = "UNKNOWN";
    state.feedback  = "Get into push-up position — lie flat, face down.";
    state.formScore = 0;
    return { metrics: { "Elbow angle": elbowAngle, "Body angle": bodyAngle }, state };
  }

  if (elbowAngle <= PUSHUP_DOWN_TRIGGER) {
    state.position = "DOWN";
  } else if (elbowAngle >= PUSHUP_UP_TRIGGER) {
    if (state.position === "DOWN") countRep(state, nowMs);
    state.position = "UP";
  }

  let score = 100;
  const feedbacks = [];

  if (state.position === "UNKNOWN") feedbacks.push("Start in a high plank, then lower.");
  else if (state.position === "UP")   feedbacks.push("Arms extended. Lower with control.");
  else if (state.position === "DOWN") feedbacks.push("Good depth. Push back up.");

  if (bodyAngle != null && bodyAngle < 150) { feedbacks.push("Keep body straight — don't let hips sag."); score -= 25; }
  if (state.position !== "DOWN" && elbowAngle > PUSHUP_DOWN_TRIGGER) { feedbacks.push("Lower your chest more."); score -= 10; }
  if (!feedbacks.length) feedbacks.push("Good form. Keep going.");

  state.feedback  = feedbacks.join(" ");
  state.formScore = Math.max(0, Math.min(100, score));

  return { metrics: { "Elbow angle": elbowAngle, "Body angle": bodyAngle }, state };
}

// ─── SIT-UP ───────────────────────────────────────────────────────────────────
// Lying flat → torso upright is ONE rep.
// Detect via shoulder–hip–knee angle (hip flexion).
// DOWN = flat on back (hip angle > SITUP_UP_HIP_ANGLE)
// UP   = torso curled (hip angle < SITUP_DOWN_HIP_ANGLE)

function analyzeSitup(landmarks, state, nowMs) {
  const hipAngles = [];

  for (const side of ["left", "right"]) {
    if (sideVisible(landmarks, side, ["shoulder", "hip", "knee"])) {
      const p = getSidePoints(landmarks, side);
      hipAngles.push(calculateAngle(p.shoulder, p.hip, p.knee));
    }
  }

  const hipAngle = avg(hipAngles);

  if (hipAngle == null) {
    return noLandmarks(state, "Lie down sideways so shoulder, hip and knee are visible.");
  }

  // State machine: DOWN (flat) → UP (curled) = 1 rep
  if (hipAngle > SITUP_UP_HIP_ANGLE) {
    if (state.position === "UP") {
      // completed the rep when returning to DOWN
      countRep(state, nowMs);
    }
    state.position = "DOWN";
  } else if (hipAngle < SITUP_DOWN_HIP_ANGLE) {
    state.position = "UP";
  }

  let score = 100;
  const feedbacks = [];

  if (state.position === "UNKNOWN") feedbacks.push("Lie flat, then curl up.");
  else if (state.position === "DOWN") feedbacks.push("Flat. Now crunch up.");
  else if (state.position === "UP")   feedbacks.push("Good crunch! Lower back down.");

  if (hipAngle > SITUP_UP_HIP_ANGLE + 10 && state.position === "DOWN") {
    feedbacks.push("Fully extend back down.");
    score -= 10;
  }

  state.feedback  = feedbacks.join(" ");
  state.formScore = Math.max(0, Math.min(100, score));

  return { metrics: { "Hip angle": hipAngle }, state };
}

// ─── JUMPING JACK ─────────────────────────────────────────────────────────────

function analyzeJumpingJack(landmarks, state, nowMs) {
  const required = [
    LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER,
    LM.LEFT_WRIST,    LM.RIGHT_WRIST,
    LM.LEFT_ANKLE,    LM.RIGHT_ANKLE,
  ];

  if (!allVisible(landmarks, required)) {
    return noLandmarks(state, "Move back. Wrists, shoulders, and ankles must be visible.");
  }

  const ls = lmXY(landmarks, LM.LEFT_SHOULDER);
  const rs = lmXY(landmarks, LM.RIGHT_SHOULDER);
  const lw = lmXY(landmarks, LM.LEFT_WRIST);
  const rw = lmXY(landmarks, LM.RIGHT_WRIST);
  const la = lmXY(landmarks, LM.LEFT_ANKLE);
  const ra = lmXY(landmarks, LM.RIGHT_ANKLE);

  const shoulderWidth = Math.max(Math.abs(rs[0] - ls[0]), 0.01);
  const footWidth     = Math.abs(ra[0] - la[0]);
  const footRatio     = footWidth / shoulderWidth;

  const avgWristY    = (lw[1] + rw[1]) / 2;
  const avgShoulderY = (ls[1] + rs[1]) / 2;

  const wristsAbove  = avgWristY < avgShoulderY;
  const wristsBelow  = avgWristY > avgShoulderY + 0.10;
  const isOpen       = wristsAbove && footRatio > JACK_OPEN_FOOT_MULT;
  const isClosed     = wristsBelow && footRatio < JACK_CLOSED_FOOT_MULT;

  if (isOpen) {
    if (state.position === "CLOSED") countRep(state, nowMs);
    state.position = "OPEN";
  } else if (isClosed) {
    state.position = "CLOSED";
  }

  let score = 100;
  const feedbacks = [];

  if (state.position === "UNKNOWN") feedbacks.push("Start closed, then jump open.");
  else if (state.position === "CLOSED") feedbacks.push("Closed. Jump open!");
  else if (state.position === "OPEN")   feedbacks.push("Open. Return closed.");

  if (!wristsAbove && state.position === "OPEN")               { feedbacks.push("Raise arms overhead."); score -= 20; }
  if (footRatio < JACK_OPEN_FOOT_MULT && state.position === "OPEN") { feedbacks.push("Jump feet wider.");     score -= 20; }

  state.feedback  = feedbacks.join(" ");
  state.formScore = Math.max(0, Math.min(100, score));

  return { metrics: { "Foot ratio": footRatio, "Wrist height": avgShoulderY - avgWristY }, state };
}

// ─── PLANK ────────────────────────────────────────────────────────────────────
// Flow:
//   1. User gets into plank position (body angle ≥ 160°)
//   2. 3-second countdown plays (plankCountdownDone = false)
//   3. Once countdown done, hold timer starts (plankSeconds counts up)
//   4. If form breaks at any point → alarm flag set, timer pauses

const PLANK_COUNTDOWN_SECS = 3;    // seconds to hold before timer starts
const PLANK_ALARM_COOLDOWN = 2000; // ms between repeated alarms

function analyzePlank(landmarks, state, nowMs) {
  const bodyAngles = [];

  for (const side of ["left", "right"]) {
    if (sideVisible(landmarks, side, ["shoulder", "hip", "ankle"])) {
      const p = getSidePoints(landmarks, side);
      bodyAngles.push(calculateAngle(p.shoulder, p.hip, p.ankle));
    }
  }

  const bodyAngle = avg(bodyAngles);

  if (bodyAngle == null) {
    return noLandmarks(state, "Side view needed. Keep shoulder, hip and ankle visible.");
  }

  const goodForm  = bodyAngle >= PLANK_GOOD_BODY_ANGLE;
  const hipIssue  = bodyAngle < 170 && bodyAngle >= PLANK_GOOD_BODY_ANGLE - 10;
  let score       = 100;
  const feedbacks = [];

  if (goodForm) {
    state.plankFormBad = false;

    if (!state.plankCountdownDone) {
      // ── Phase 1: countdown ──────────────────────────────────────────────
      if (state.plankCountdownStartTime == null) {
        state.plankCountdownStartTime = nowMs;
      }
      const elapsed = (nowMs - state.plankCountdownStartTime) / 1000;
      const remaining = Math.ceil(PLANK_COUNTDOWN_SECS - elapsed);

      if (elapsed >= PLANK_COUNTDOWN_SECS) {
        state.plankCountdownDone = true;
        state.plankStartTime     = nowMs;
        state.position           = "HOLD";
        feedbacks.push("Hold! Timer started.");
      } else {
        state.position = "COUNTDOWN";
        // remaining exposed via formScore hack: store in plankCountdown field
        state.plankCountdown = remaining;
        feedbacks.push(`Hold position… ${remaining}`);
      }
    } else {
      // ── Phase 2: hold timer ─────────────────────────────────────────────
      state.position    = "HOLD";
      state.plankSeconds = (nowMs - state.plankStartTime) / 1000;
      state.bestPlankSeconds = Math.max(state.bestPlankSeconds, state.plankSeconds);
      feedbacks.push("Perfect plank! Keep holding.");

      if (hipIssue) {
        feedbacks.push("Slight hip issue — keep body flat.");
        score -= 10;
      }
    }
  } else {
    // ── Bad form ────────────────────────────────────────────────────────────
    state.position = "RESET";

    if (state.plankCountdownDone) {
      // Was in hold — form broke, set alarm flag
      if (!state.plankFormBad) {
        state.plankFormBad = true;
        state.plankLastAlarmMs = nowMs; // trigger alarm immediately
      } else if (nowMs - state.plankLastAlarmMs >= PLANK_ALARM_COOLDOWN) {
        state.plankLastAlarmMs = nowMs; // repeat alarm
      }
    }

    // Reset countdown & timer
    state.plankCountdownStartTime = null;
    state.plankCountdownDone      = false;
    state.plankStartTime          = null;
    state.plankSeconds            = 0;
    state.plankCountdown          = PLANK_COUNTDOWN_SECS;

    if (bodyAngle < 140) {
      feedbacks.push("Hips too high or too low. Straighten your body.");
      score -= 40;
    } else {
      feedbacks.push("Almost there — straighten your body to start.");
      score -= 20;
    }
  }

  state.feedback  = feedbacks.join(" ");
  state.formScore = Math.max(0, Math.min(100, score));

  return {
    metrics: { "Body angle": bodyAngle, "Hold seconds": state.plankSeconds },
    alarmNow: state.plankFormBad && (nowMs - state.plankLastAlarmMs < 100),
    state,
  };
}

// ─── LUNGE ────────────────────────────────────────────────────────────────────

function analyzeLunge(landmarks, state, nowMs) {
  let leftKnee = null, rightKnee = null;
  const torsoAngles = [];

  if (sideVisible(landmarks, "left", ["shoulder", "hip", "knee", "ankle"])) {
    const p = getSidePoints(landmarks, "left");
    leftKnee = calculateAngle(p.hip, p.knee, p.ankle);
    torsoAngles.push(calculateAngle(p.shoulder, p.hip, p.knee));
  }
  if (sideVisible(landmarks, "right", ["shoulder", "hip", "knee", "ankle"])) {
    const p = getSidePoints(landmarks, "right");
    rightKnee = calculateAngle(p.hip, p.knee, p.ankle);
    torsoAngles.push(calculateAngle(p.shoulder, p.hip, p.knee));
  }

  const kneeAngles = [leftKnee, rightKnee].filter((v) => v != null);
  const torsoAngle = avg(torsoAngles);

  if (kneeAngles.length < 2) {
    return noLandmarks(state, "Move back. Both legs must be visible for lunges.");
  }

  const frontKnee    = Math.min(...kneeAngles);
  const bothStraight = leftKnee > LUNGE_UP_KNEE_ANGLE && rightKnee > LUNGE_UP_KNEE_ANGLE;

  if (bothStraight) {
    if (state.position === "DOWN") countRep(state, nowMs);
    state.position = "UP";
  } else if (frontKnee < LUNGE_DOWN_KNEE_ANGLE) {
    state.position = "DOWN";
  }

  let score = 100;
  const feedbacks = [];

  if (state.position === "UNKNOWN") feedbacks.push("Step into a lunge, then stand tall.");
  else if (state.position === "UP")   feedbacks.push("Standing tall. Start next lunge.");
  else if (state.position === "DOWN") feedbacks.push("Good lunge depth. Push back up.");

  if (state.position === "DOWN") {
    if (frontKnee < 75)  { feedbacks.push("Don't overbend the front knee."); score -= 15; }
    else if (frontKnee > 105) { feedbacks.push("Lower a little more."); score -= 15; }
  }
  if (torsoAngle != null && torsoAngle < 55) { feedbacks.push("Keep chest up."); score -= 20; }

  state.feedback  = feedbacks.join(" ");
  state.formScore = Math.max(0, Math.min(100, score));

  return { metrics: { "Front knee": frontKnee, "Left knee": leftKnee, "Right knee": rightKnee }, state };
}

// ─── BURPEE ───────────────────────────────────────────────────────────────────
// Simple approach: detect squat-to-standing transition (same landmarks as squat)
// then detect arms raised overhead → full burpee rep
// DOWN = squat/floor position (knee angle ≤ 115)
// UP   = standing with wrists above shoulders (jump phase)

function analyzeBurpee(landmarks, state, nowMs) {
  const kneeAngles = [];

  for (const side of ["left", "right"]) {
    if (sideVisible(landmarks, side, ["hip", "knee", "ankle"])) {
      const p = getSidePoints(landmarks, side);
      kneeAngles.push(calculateAngle(p.hip, p.knee, p.ankle));
    }
  }

  const kneeAngle = avg(kneeAngles);

  // Check wrists above shoulders for the jump-up detection
  let wristsUp = false;
  if (allVisible(landmarks, [LM.LEFT_WRIST, LM.RIGHT_WRIST, LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER])) {
    const lw = lmXY(landmarks, LM.LEFT_WRIST);
    const rw = lmXY(landmarks, LM.RIGHT_WRIST);
    const ls = lmXY(landmarks, LM.LEFT_SHOULDER);
    const rs = lmXY(landmarks, LM.RIGHT_SHOULDER);
    const avgWristY    = (lw[1] + rw[1]) / 2;
    const avgShoulderY = (ls[1] + rs[1]) / 2;
    wristsUp = avgWristY < avgShoulderY - 0.05;
  }

  if (kneeAngle == null && !wristsUp) {
    return noLandmarks(state, "Move back so your full body is visible for burpees.");
  }

  const isDown = kneeAngle != null && kneeAngle <= 115;
  const isUp   = wristsUp && (kneeAngle == null || kneeAngle > 140);

  if (isDown) {
    state.position = "DOWN";
  } else if (isUp) {
    if (state.position === "DOWN") countRep(state, nowMs);
    state.position = "UP";
  }

  let score = 100;
  const feedbacks = [];

  if (state.position === "UNKNOWN") feedbacks.push("Start standing, drop to floor, then jump up.");
  else if (state.position === "DOWN") feedbacks.push("Floor position. Push up and jump!");
  else if (state.position === "UP")   feedbacks.push("Great jump! Drop back down.");

  state.feedback  = feedbacks.join(" ");
  state.formScore = Math.max(0, Math.min(100, score));

  return { metrics: { "Knee angle": kneeAngle }, state };
}

// ─── MOUNTAIN CLIMBER ────────────────────────────────────────────────────────
// Each knee drive counts as half a rep (left + right = 1 rep)
// Detect: knee coming toward chest = hip angle < 80° on that side
// Both knees > 140° = reset position

function analyzeMountainClimber(landmarks, state, nowMs) {
  let leftHip = null, rightHip = null;

  if (sideVisible(landmarks, "left", ["shoulder", "hip", "knee"])) {
    const p = getSidePoints(landmarks, "left");
    leftHip = calculateAngle(p.shoulder, p.hip, p.knee);
  }
  if (sideVisible(landmarks, "right", ["shoulder", "hip", "knee"])) {
    const p = getSidePoints(landmarks, "right");
    rightHip = calculateAngle(p.shoulder, p.hip, p.knee);
  }

  if (leftHip == null && rightHip == null) {
    return noLandmarks(state, "Side view. Keep shoulder, hip and knee visible for mountain climbers.");
  }

  // Track which knee was last driven — alternate L/R for rep counting
  if (!state.mcLastDriven) state.mcLastDriven = null;
  if (!state.mcHalfReps)   state.mcHalfReps   = 0;

  const LEFT_DRIVE  = leftHip  != null && leftHip  < 80;
  const RIGHT_DRIVE = rightHip != null && rightHip < 80;

  if (LEFT_DRIVE && state.mcLastDriven !== "left") {
    state.mcLastDriven = "left";
    state.mcHalfReps  += 1;
  } else if (RIGHT_DRIVE && state.mcLastDriven !== "right") {
    state.mcLastDriven = "right";
    state.mcHalfReps  += 1;
  }

  // Every 2 half-reps = 1 full rep
  const fullReps = Math.floor(state.mcHalfReps / 2);
  if (fullReps > state.reps) {
    const diff = fullReps - state.reps;
    state.reps += diff;
    state.lastRepTime = nowMs;
  }

  state.position = LEFT_DRIVE ? "LEFT" : RIGHT_DRIVE ? "RIGHT" : "HOLD";

  const feedbacks = [];
  if (state.position === "HOLD")  feedbacks.push("Drive knees to chest alternately.");
  else if (state.position === "LEFT")  feedbacks.push("Left knee in. Switch!");
  else if (state.position === "RIGHT") feedbacks.push("Right knee in. Switch!");

  state.feedback  = feedbacks.join(" ");
  state.formScore = 100;

  return {
    metrics: { "Left hip": leftHip, "Right hip": rightHip },
    state,
  };
}

// ─── DISPATCHER ──────────────────────────────────────────────────────────────

export function analyzeExercise(landmarks, state, nowMs) {
  switch (state.exercise) {
    case "Squat":            return analyzeSquat(landmarks, state, nowMs);
    case "Push-up":          return analyzePushup(landmarks, state, nowMs);
    case "Sit-up":           return analyzeSitup(landmarks, state, nowMs);
    case "Jumping Jack":     return analyzeJumpingJack(landmarks, state, nowMs);
    case "Plank":            return analyzePlank(landmarks, state, nowMs);
    case "Lunge":            return analyzeLunge(landmarks, state, nowMs);
    case "Burpee":           return analyzeBurpee(landmarks, state, nowMs);
    case "Mountain Climber": return analyzeMountainClimber(landmarks, state, nowMs);
    default:
      state.feedback  = `Exercise "${state.exercise}" not supported.`;
      state.formScore = 0;
      return { metrics: {}, state };
  }
}

// ─── SLUG → DISPLAY NAME ─────────────────────────────────────────────────────

export const SLUG_TO_NAME = {
  squat:            "Squat",
  push_up:          "Push-up",
  pushup:           "Push-up",
  sit_up:           "Sit-up",
  situp:            "Sit-up",
  jumping_jack:     "Jumping Jack",
  plank:            "Plank",
  lunge:            "Lunge",
  lunges:           "Lunge",
  burpee:           "Burpee",
  burpees:          "Burpee",
  mountain_climber: "Mountain Climber",
};
