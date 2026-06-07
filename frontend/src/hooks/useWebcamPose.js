/**
 * useWebcamPose.js — fixed version
 *
 * Fixes:
 * 1. WASM CDN version matches installed package (0.10.35)
 * 2. Falls back from GPU → CPU delegate so WASM works without COOP headers
 * 3. Uses performance.now() for MediaPipe timestamps (not RAF timestamp)
 * 4. All RAF-internal logic uses refs only — no stale closures
 * 5. renderLoop stored in a ref so start() always calls the live version
 */

import { useRef, useState, useEffect, useCallback } from "react";
import {
  analyzeExercise,
  createState,
  POSE_CONNECTIONS,
  SLUG_TO_NAME,
  CALORIES_PER_REP,
  PLANK_CALORIES_PER_SECOND,
} from "../lib/exerciseLogic.js";

// Match the installed package version exactly
const MP_CDN = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm";

// ─── ALARM BEEP (Web Audio API — no file needed) ─────────────────────────────
function playAlarmBeep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    // Two-tone urgent beep
    const freqs  = [880, 660];
    const timing = [0, 0.18];
    freqs.forEach((freq, i) => {
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = "square";
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.35, ctx.currentTime + timing[i]);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + timing[i] + 0.16);
      osc.start(ctx.currentTime + timing[i]);
      osc.stop(ctx.currentTime + timing[i] + 0.16);
    });
    // Auto-close after beep finishes
    setTimeout(() => { try { ctx.close(); } catch (_) {} }, 600);
  } catch (_) {
    // AudioContext not available — silent fail
  }
}

// ─── CALORIE HELPER ───────────────────────────────────────────────────────────
function calcCalories(exerciseName, totalReps) {
  return (CALORIES_PER_REP[exerciseName] ?? 0.25) * totalReps;
}

// ─── SKELETON DRAW ────────────────────────────────────────────────────────────
// NOTE: The video is drawn mirrored (flipped horizontally). MediaPipe landmarks
// have lm.x = 0 (left edge of the RAW camera frame) → 1 (right edge).
// To align with the mirrored video we must mirror the x coordinate:
//   mirroredX = (1 - lm.x) * w
function drawSkeleton(ctx, landmarks, w, h) {
  ctx.lineWidth = 2;
  ctx.strokeStyle = "rgba(80,220,120,0.85)";
  for (const [a, b] of POSE_CONNECTIONS) {
    const lmA = landmarks[a], lmB = landmarks[b];
    if (!lmA || !lmB) continue;
    if ((lmA.visibility ?? 1) < 0.05 || (lmB.visibility ?? 1) < 0.05) continue;
    ctx.beginPath();
    ctx.moveTo((1 - lmA.x) * w, lmA.y * h);
    ctx.lineTo((1 - lmB.x) * w, lmB.y * h);
    ctx.stroke();
  }
  for (const lm of landmarks) {
    if ((lm.visibility ?? 1) < 0.05) continue;
    ctx.beginPath();
    ctx.arc((1 - lm.x) * w, lm.y * h, 4, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(40,230,240,0.9)";
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.8)";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

// ─── HUD HELPERS ──────────────────────────────────────────────────────────────
const POS_COLORS = {
  UP: "#50dc6e", DOWN: "#f0d040", HOLD: "#50dc6e",
  OPEN: "#63cab7", CLOSED: "#f0d040", RESET: "#e05050", UNKNOWN: "#909090",
};

function rrect(ctx, x, y, w, h, r = 12) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function drawStatCard(ctx, x, y, w, h, label, value, accent, progress) {
  ctx.fillStyle = "rgba(20,22,30,0.86)";
  rrect(ctx, x, y, w, h, 12);
  ctx.fill();
  ctx.fillStyle = "#919197";
  ctx.font = "bold 10px Inter,Arial,sans-serif";
  ctx.fillText(label.toUpperCase(), x + 12, y + 20);
  ctx.fillStyle = "#eeeef5";
  ctx.font = "bold 19px Inter,Arial,sans-serif";
  ctx.fillText(String(value), x + 12, y + 50);
  if (progress != null) {
    const bx = x + 12, by = y + h - 10, bw = w - 24;
    ctx.fillStyle = "#2d2f3a";
    ctx.fillRect(bx, by, bw, 4);
    ctx.fillStyle = accent;
    ctx.fillRect(bx, by, bw * Math.min(1, Math.max(0, progress)), 4);
  }
  ctx.beginPath();
  ctx.arc(x + w - 14, y + 14, 4, 0, Math.PI * 2);
  ctx.fillStyle = accent;
  ctx.fill();
}

function drawPlankCountdown(ctx, cw, ch, remaining) {
  // Big centred countdown number
  ctx.fillStyle = "rgba(8,10,16,0.55)";
  ctx.fillRect(0, 0, cw, ch);

  ctx.textAlign = "center";
  ctx.fillStyle = "#63cab7";
  ctx.font = `bold ${Math.min(cw, ch) * 0.25}px Inter,Arial,sans-serif`;
  ctx.fillText(String(remaining), cw / 2, ch / 2 + 40);

  ctx.fillStyle = "#eeeef5";
  ctx.font = "bold 22px Inter,Arial,sans-serif";
  ctx.fillText("Get into position — hold still…", cw / 2, ch / 2 - 60);
  ctx.textAlign = "left";
}

function drawPlankAlarm(ctx, cw, ch) {
  // Red flash overlay when form breaks during hold
  ctx.fillStyle = "rgba(220,30,30,0.28)";
  ctx.fillRect(0, 0, cw, ch);

  ctx.textAlign = "center";
  ctx.fillStyle = "#ff4444";
  ctx.font = "bold 28px Inter,Arial,sans-serif";
  ctx.fillText("⚠  Fix your form!", cw / 2, ch / 2);
  ctx.fillStyle = "#ffaaaa";
  ctx.font = "16px Inter,Arial,sans-serif";
  ctx.fillText("Hips sagging or raised — straighten your body", cw / 2, ch / 2 + 36);
  ctx.textAlign = "left";
}

function drawHUD(ctx, cw, ch, state, metrics, calories, currentSet, totalSets, plannedReps, plannedDuration, elapsedSet) {
  // Top bar
  ctx.fillStyle = "rgba(8,10,16,0.72)";
  rrect(ctx, 10, 10, cw - 20, 90, 16);
  ctx.fill();

  ctx.fillStyle = "#63cab7";
  ctx.font = "bold 13px Inter,Arial,sans-serif";
  ctx.fillText("MoveMate AI", 26, 36);
  ctx.fillStyle = "#eeeef5";
  ctx.font = "bold 17px Inter,Arial,sans-serif";
  ctx.fillText(state.exercise.toUpperCase(), 26, 62);

  // Position badge
  const posLabel  = state.position === "COUNTDOWN"
    ? `READY ${state.plankCountdown ?? ""}…`
    : state.position;
  const posColor = state.position === "COUNTDOWN" ? "#f0d040"
    : (POS_COLORS[state.position] || "#909090");
  ctx.fillStyle = posColor + "dd";
  rrect(ctx, 26, 68, 140, 22, 7);
  ctx.fill();
  ctx.fillStyle = "#080a10";
  ctx.font = "bold 11px Inter,Arial,sans-serif";
  ctx.fillText(posLabel, 36, 83);

  // Stat cards
  const cardW = Math.min(150, Math.max(100, (cw - 220) / 4 - 8));
  const gap = 8;
  let cx = 200;

  const mainVal = state.exercise === "Plank"
    ? `${Math.floor(state.plankSeconds)}s`
    : plannedReps ? `${state.reps}/${plannedReps}` : `${state.reps}`;
  const mainPct = state.exercise === "Plank"
    ? (plannedDuration ? Math.min(1, elapsedSet / plannedDuration) : null)
    : (plannedReps ? Math.min(1, state.reps / plannedReps) : null);

  drawStatCard(ctx, cx, 18, cardW, 74, state.exercise === "Plank" ? "hold" : "reps", mainVal, "#63cab7", mainPct);
  cx += cardW + gap;
  drawStatCard(ctx, cx, 18, cardW, 74, "set", `${currentSet}/${totalSets}`, "#50dc6e", currentSet / Math.max(1, totalSets));
  cx += cardW + gap;
  const fs = Math.max(0, Math.min(100, state.formScore));
  const fc = fs >= 80 ? "#50dc6e" : fs >= 50 ? "#f0d040" : "#e05050";
  drawStatCard(ctx, cx, 18, cardW, 74, "form", `${fs}%`, fc, fs / 100);
  cx += cardW + gap;
  drawStatCard(ctx, cx, 18, cardW, 74, "kcal", calories.toFixed(2), "#f0d040", null);

  // Set dots
  const dotX0 = 200 + cardW + gap + 12;
  for (let i = 0; i < Math.min(totalSets, 10); i++) {
    const dc = i < currentSet - 1 ? "#50dc6e" : i === currentSet - 1 ? "#63cab7" : "#3c3e48";
    ctx.beginPath();
    ctx.arc(dotX0 + i * 14, 18 + 74 - 10, 4, 0, Math.PI * 2);
    ctx.fillStyle = dc;
    ctx.fill();
  }

  // Feedback pill
  const pillText = (state.feedback || "").slice(0, 80);
  ctx.font = "bold 13px Inter,Arial,sans-serif";
  const tw = ctx.measureText(pillText).width;
  const pillW = Math.min(cw - 30, tw + 40);
  const pillX = Math.max(10, (cw - pillW) / 2);
  const pillY = ch - 64;
  ctx.fillStyle = "rgba(8,10,16,0.78)";
  rrect(ctx, pillX, pillY, pillW, 38, 14);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(pillX + 18, pillY + 19, 5, 0, Math.PI * 2);
  ctx.fillStyle = "#63cab7";
  ctx.fill();
  ctx.fillStyle = "#f0d040";
  ctx.font = "bold 13px Inter,Arial,sans-serif";
  ctx.fillText(pillText, pillX + 32, pillY + 24);

  // Live metrics
  const mItems = Object.entries(metrics).slice(0, 2);
  if (mItems.length) {
    const bW = 200, bH = 26 + mItems.length * 20;
    const bX = 10, bY = ch - 72 - bH;
    ctx.fillStyle = "rgba(8,10,16,0.55)";
    rrect(ctx, bX, bY, bW, bH, 10);
    ctx.fill();
    ctx.fillStyle = "#909090";
    ctx.font = "bold 10px Inter,Arial,sans-serif";
    ctx.fillText("LIVE METRICS", bX + 12, bY + 16);
    let my = bY + 36;
    for (const [lbl, val] of mItems) {
      const short = lbl.replace(" angle", "°").replace(" seconds", "s").replace(" ratio", "");
      ctx.fillStyle = "#eeeef5";
      ctx.font = "11px Inter,Arial,sans-serif";
      ctx.fillText(`${short}: ${val != null ? val.toFixed(1) : "--"}`, bX + 12, my);
      my += 20;
    }
  }
}

function drawSetCompleteScreen(ctx, cw, ch, setNum, totalSets, reps, plannedReps, calories) {
  ctx.fillStyle = "rgba(8,9,12,0.75)";
  ctx.fillRect(0, 0, cw, ch);
  const bw = 420, bh = 260, bx = (cw - bw) / 2, by = (ch - bh) / 2;
  ctx.fillStyle = "rgba(20,22,30,0.96)";
  rrect(ctx, bx, by, bw, bh, 20);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cw / 2, by + 56, 30, 0, Math.PI * 2);
  ctx.fillStyle = "#50dc6e";
  ctx.fill();
  ctx.strokeStyle = "#080a10";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(cw / 2 - 12, by + 56);
  ctx.lineTo(cw / 2 - 2, by + 68);
  ctx.lineTo(cw / 2 + 14, by + 44);
  ctx.stroke();
  ctx.textAlign = "center";
  ctx.fillStyle = "#eeeef5";
  ctx.font = "bold 20px Inter,Arial,sans-serif";
  ctx.fillText(`SET ${setNum} COMPLETE!`, cw / 2, by + 110);
  ctx.fillStyle = "#919197";
  ctx.font = "14px Inter,Arial,sans-serif";
  ctx.fillText(`Reps: ${reps} / ${plannedReps ?? reps}`, cw / 2, by + 140);
  ctx.fillStyle = "#63cab7";
  ctx.font = "bold 14px Inter,Arial,sans-serif";
  ctx.fillText(`${calories.toFixed(2)} kcal so far`, cw / 2, by + 165);
  if (setNum < totalSets) {
    ctx.fillStyle = "rgba(99,202,183,0.92)";
    rrect(ctx, bx + 80, by + 195, bw - 160, 40, 10);
    ctx.fill();
    ctx.fillStyle = "#080a10";
    ctx.font = "bold 13px Inter,Arial,sans-serif";
    ctx.fillText(`Starting Set ${setNum + 1} in 3s…`, cw / 2, by + 220);
  }
  ctx.textAlign = "left";
}

function drawAllDoneScreen(ctx, cw, ch, exerciseName, totalSets, totalReps, calories) {
  ctx.fillStyle = "rgba(8,9,12,0.78)";
  ctx.fillRect(0, 0, cw, ch);
  const bw = 440, bh = 280, bx = (cw - bw) / 2, by = (ch - bh) / 2;
  ctx.fillStyle = "rgba(20,22,30,0.96)";
  rrect(ctx, bx, by, bw, bh, 20);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(cw / 2, by + 60, 34, 0, Math.PI * 2);
  ctx.fillStyle = "#63cab7";
  ctx.fill();
  ctx.textAlign = "center";
  ctx.fillStyle = "#080a10";
  ctx.font = "bold 20px Inter,Arial,sans-serif";
  ctx.fillText("✓", cw / 2, by + 68);
  ctx.fillStyle = "#50dc6e";
  ctx.font = "bold 22px Inter,Arial,sans-serif";
  ctx.fillText("WORKOUT COMPLETE!", cw / 2, by + 120);
  ctx.fillStyle = "#919197";
  ctx.font = "14px Inter,Arial,sans-serif";
  ctx.fillText(exerciseName, cw / 2, by + 148);
  const stats = [["Sets", totalSets], ["Reps", totalReps], ["Calories", calories.toFixed(1)]];
  let sx = bx + 60;
  for (const [lbl, val] of stats) {
    ctx.fillStyle = "#919197";
    ctx.font = "bold 11px Inter,Arial,sans-serif";
    ctx.fillText(lbl.toUpperCase(), sx + 40, by + 185);
    ctx.fillStyle = "#eeeef5";
    ctx.font = "bold 22px Inter,Arial,sans-serif";
    ctx.fillText(String(val), sx + 40, by + 215);
    sx += 120;
  }
  ctx.fillStyle = "#63cab7";
  ctx.font = "bold 13px Inter,Arial,sans-serif";
  ctx.fillText("Saving results…", cw / 2, by + 258);
  ctx.textAlign = "left";
}

// ─── MAIN HOOK ────────────────────────────────────────────────────────────────
export default function useWebcamPose({
  exerciseSlug,
  plannedSets = 3,
  plannedReps = null,
  plannedDurationSeconds = null,
}) {
  const exerciseName = SLUG_TO_NAME[exerciseSlug] ?? "Squat";

  // DOM refs
  const videoRef  = useRef(null);
  const canvasRef = useRef(null);

  // Internal runtime refs (never cause re-renders)
  const landmarkerRef        = useRef(null);
  const animFrameRef         = useRef(null);
  const streamRef            = useRef(null);
  const stateRef             = useRef(createState(exerciseName));
  const caloriesRef          = useRef(0);
  const currentSetRef        = useRef(1);
  const completedSetsRef     = useRef(0);
  const totalRepsRef         = useRef(0);
  const incorrectRepsRef     = useRef(0);
  const postureEventsRef     = useRef([]);
  const workoutStartRef      = useRef(null);
  const setStartRef          = useRef(null);
  const lastTsRef            = useRef(-1);          // last perf timestamp sent to MP
  const waitingNextSetRef    = useRef(false);
  const nextSetTimerRef      = useRef(null);
  const allDoneRef           = useRef(false);
  const phaseRef             = useRef("idle");
  const renderLoopRef        = useRef(null);        // holds the RAF callback itself

  // React state (only for UI display)
  const [phase, setPhaseState]       = useState("idle");
  const [displayReps, setDispReps]   = useState(0);
  const [displaySet, setDispSet]     = useState(1);
  const [displayCalories, setDispCal]= useState(0);
  const [displayForm, setDispForm]   = useState(100);
  const [displayFeedback, setDispFb] = useState("");
  const [displayPlank, setDispPlank] = useState(0);
  const [errorMsg, setErrorMsg]      = useState("");

  function setPhase(p) {
    phaseRef.current = p;
    setPhaseState(p);
  }

  // ── Load MediaPipe ────────────────────────────────────────────────────────
  async function loadLandmarker() {
    const { PoseLandmarker, FilesetResolver } = await import("@mediapipe/tasks-vision");
    const vision = await FilesetResolver.forVisionTasks(MP_CDN);

    // Try GPU first, fall back to CPU if GPU/SharedArrayBuffer unavailable
    const makeOptions = (delegate) => ({
      baseOptions: {
        modelAssetPath:
          "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
        delegate,
      },
      runningMode: "VIDEO",
      numPoses: 1,
      minPoseDetectionConfidence: 0.5,
      minPosePresenceConfidence:  0.5,
      minTrackingConfidence:      0.5,
    });

    try {
      return await PoseLandmarker.createFromOptions(vision, makeOptions("GPU"));
    } catch {
      console.warn("[useWebcamPose] GPU delegate failed — falling back to CPU");
      return await PoseLandmarker.createFromOptions(vision, makeOptions("CPU"));
    }
  }

  // ── Open webcam ───────────────────────────────────────────────────────────
  async function openCamera() {
    // Stop any existing stream first
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
      audio: false,
    });

    streamRef.current = stream;

    const video = videoRef.current;
    if (!video) throw new Error("Video element not mounted.");

    video.srcObject = stream;
    video.muted = true;

    await new Promise((resolve, reject) => {
      video.onloadedmetadata = () => {
        video.play().then(resolve).catch(reject);
      };
      // timeout after 10s
      setTimeout(() => reject(new Error("Camera timed out. Check permissions.")), 10000);
    });
  }

  // ── Build result payload ──────────────────────────────────────────────────
  function buildResult(sessionId, roadmapDayExerciseId) {
    const totalDuration = workoutStartRef.current
      ? Math.round((Date.now() - workoutStartRef.current) / 1000)
      : 0;
    const totalReps    = totalRepsRef.current;
    const incorrectReps = incorrectRepsRef.current;
    const correctReps  = Math.max(0, totalReps - incorrectReps);
    const calories     = caloriesRef.current;
    const completedSets = completedSetsRef.current;
    const postureScore  = totalReps > 0
      ? Math.max(0, 100 - incorrectReps * 10)
      : exerciseName === "Plank" && totalDuration > 0 ? 100 : 0;

    return {
      model: {
        model_name:    "MoveMate Pose AI",
        model_version: "1.0",
        detector_type: `${exerciseSlug}_detector`,
        metadata: { source: "browser_mediapipe", device: "webcam" },
      },
      session: {
        session_id:              sessionId,
        total_duration_seconds:  totalDuration,
        total_calories_burned:   parseFloat(calories.toFixed(2)),
        average_posture_score:   postureScore,
      },
      exercises: [{
        roadmap_day_exercise_id: roadmapDayExerciseId || null,
        exercise_slug:           exerciseSlug,
        exercise_name:           exerciseName,
        actual_sets:             completedSets,
        planned_sets:            plannedSets,
        actual_reps:             totalReps,
        planned_reps:            plannedReps,
        actual_duration_seconds: totalDuration,
        correct_reps:            correctReps,
        incorrect_reps:          incorrectReps,
        calories_burned:         parseFloat(calories.toFixed(2)),
        posture_score:           postureScore,
        posture_events:          postureEventsRef.current,
      }],
    };
  }

  // ── Advance to next set ───────────────────────────────────────────────────
  function advanceToNextSet() {
    clearTimeout(nextSetTimerRef.current);
    currentSetRef.current += 1;
    stateRef.current = createState(exerciseName);
    setStartRef.current = performance.now();
    waitingNextSetRef.current = false;
    setPhase("active");
  }

  // ── Finish current set ────────────────────────────────────────────────────
  function finishSet(state) {
    if (waitingNextSetRef.current || allDoneRef.current) return;

    totalRepsRef.current    += state.reps;
    completedSetsRef.current += 1;

    const isLast = currentSetRef.current >= plannedSets;

    if (isLast) {
      allDoneRef.current = true;
      setPhase("all_done");
    } else {
      waitingNextSetRef.current = true;
      setPhase("set_done");
      nextSetTimerRef.current = setTimeout(advanceToNextSet, 3000);
    }
  }

  // ── RAF render loop (stored in ref — never goes stale) ────────────────────
  renderLoopRef.current = function renderLoop() {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    const lm     = landmarkerRef.current;

    if (!video || !canvas || !lm) {
      animFrameRef.current = requestAnimationFrame(renderLoopRef.current);
      return;
    }

    // Canvas must match video natural size for correct landmark coordinates
    if (video.videoWidth && canvas.width !== video.videoWidth) {
      canvas.width  = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    const cw = canvas.width  || 1280;
    const ch = canvas.height || 720;
    const ctx = canvas.getContext("2d");

    // Draw mirrored video frame
    ctx.save();
    ctx.scale(-1, 1);
    ctx.drawImage(video, -cw, 0, cw, ch);
    ctx.restore();

    // MediaPipe VIDEO mode: timestamp must be strictly increasing (use perf.now)
    const nowPerf = performance.now();
    const tsMs = Math.max(nowPerf, lastTsRef.current + 1);
    lastTsRef.current = tsMs;

    const nowMs = Date.now();
    const elapsedSet   = setStartRef.current   ? (nowPerf - setStartRef.current) / 1000   : 0;
    const elapsedTotal = workoutStartRef.current ? (nowPerf - workoutStartRef.current) / 1000 : 0;

    let landmarks = null;
    if (video.readyState >= 2) {
      try {
        const result = lm.detectForVideo(video, tsMs);
        if (result.landmarks?.length > 0) landmarks = result.landmarks[0];
      } catch (e) {
        console.warn("[pose] detectForVideo error:", e.message);
      }
    }

    const state = stateRef.current;

    // ── Set-complete overlay ──────────────────────────────────────────────
    if (waitingNextSetRef.current) {
      if (landmarks) drawSkeleton(ctx, landmarks, cw, ch);
      drawSetCompleteScreen(
        ctx, cw, ch,
        currentSetRef.current,   // set just completed
        plannedSets,
        state.reps,
        plannedReps,
        caloriesRef.current,
      );
      animFrameRef.current = requestAnimationFrame(renderLoopRef.current);
      return;
    }

    // ── All-done overlay ──────────────────────────────────────────────────
    if (allDoneRef.current) {
      if (landmarks) drawSkeleton(ctx, landmarks, cw, ch);
      drawAllDoneScreen(ctx, cw, ch, exerciseName, completedSetsRef.current, totalRepsRef.current, caloriesRef.current);
      animFrameRef.current = requestAnimationFrame(renderLoopRef.current);
      return;
    }

    // ── Duration-based timeout ────────────────────────────────────────────
    if (plannedDurationSeconds && elapsedTotal >= plannedDurationSeconds) {
      finishSet(state);
      animFrameRef.current = requestAnimationFrame(renderLoopRef.current);
      return;
    }

    // ── Pose analysis ─────────────────────────────────────────────────────
    let metrics = {};
    let plankAlarmNow = false;
    if (landmarks) {
      const oldReps = state.reps;
      const analysis = analyzeExercise(landmarks, state, nowMs);
      metrics = analysis.metrics;
      if (analysis.alarmNow) plankAlarmNow = true;

      // Calories
      if (exerciseName === "Plank") {
        caloriesRef.current = state.plankSeconds * PLANK_CALORIES_PER_SECOND;
      } else {
        caloriesRef.current = calcCalories(exerciseName, totalRepsRef.current + state.reps);
      }

      // Posture events on bad reps
      if (state.reps > oldReps && state.formScore < 70) {
        incorrectRepsRef.current += 1;
        postureEventsRef.current.push({
          timestamp_seconds: parseFloat(elapsedTotal.toFixed(3)),
          issue_type: "poor_form",
          feedback: state.feedback,
          posture_score: state.formScore,
          landmark_data: Object.fromEntries(
            Object.entries(metrics).map(([k, v]) => [k, v != null ? parseFloat(v.toFixed(2)) : null])
          ),
        });
      }

      drawSkeleton(ctx, landmarks, cw, ch);

      // ── Plank countdown big number overlay ──────────────────────────────
      if (exerciseName === "Plank" && state.position === "COUNTDOWN") {
        drawPlankCountdown(ctx, cw, ch, state.plankCountdown ?? 3);
      }

      // ── Plank form-break alarm overlay + audio ───────────────────────────
      if (exerciseName === "Plank" && state.position === "RESET" && state.plankFormBad) {
        drawPlankAlarm(ctx, cw, ch);
        if (plankAlarmNow) playAlarmBeep();
      }
    } else {
      state.feedback  = "No person detected — step into view.";
      state.formScore = 0;
      if (exerciseName === "Plank") {
        state.plankStartTime          = null;
        state.plankSeconds            = 0;
        state.plankCountdownStartTime = null;
        state.plankCountdownDone      = false;
      }
    }

    // Draw HUD
    drawHUD(
      ctx, cw, ch, state, metrics, caloriesRef.current,
      currentSetRef.current, plannedSets, plannedReps,
      plannedDurationSeconds, elapsedSet,
    );

    // Sync React display state
    setDispReps(state.reps);
    setDispSet(currentSetRef.current);
    setDispCal(parseFloat(caloriesRef.current.toFixed(2)));
    setDispForm(state.formScore);
    setDispFb(state.feedback);
    setDispPlank(Math.floor(state.plankSeconds));

    // Auto-finish set when reps target hit
    if (plannedReps && state.reps >= plannedReps) {
      finishSet(state);
    }

    animFrameRef.current = requestAnimationFrame(renderLoopRef.current);
  };

  // ── Public: start ─────────────────────────────────────────────────────────
  const start = useCallback(async () => {
    setPhase("loading");
    setErrorMsg("");

    // Let React re-render (mount the hidden <video> element) before proceeding
    await new Promise((res) => setTimeout(res, 0));

    try {
      // Run camera open and model load in parallel
      const [, landmarker] = await Promise.all([openCamera(), loadLandmarker()]);
      landmarkerRef.current = landmarker;

      // Reset all counters
      workoutStartRef.current   = performance.now();
      setStartRef.current       = performance.now();
      currentSetRef.current     = 1;
      completedSetsRef.current  = 0;
      totalRepsRef.current      = 0;
      incorrectRepsRef.current  = 0;
      postureEventsRef.current  = [];
      caloriesRef.current       = 0;
      allDoneRef.current        = false;
      waitingNextSetRef.current = false;
      lastTsRef.current         = -1;
      stateRef.current          = createState(exerciseName);

      setPhase("active");
      animFrameRef.current = requestAnimationFrame(renderLoopRef.current);
    } catch (err) {
      console.error("[useWebcamPose] start error:", err);
      setErrorMsg(err.message || "Failed to start camera or AI model.");
      setPhase("error");
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Public: manually advance set ─────────────────────────────────────────
  const nextSet = useCallback(() => {
    if (phaseRef.current === "set_done") {
      advanceToNextSet();
    } else if (phaseRef.current === "active") {
      finishSet(stateRef.current);
    }
  }, []);

  // ── Public: stop early & return payload ───────────────────────────────────
  const stop = useCallback((sessionId, roadmapDayExerciseId) => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    clearTimeout(nextSetTimerRef.current);

    // Count any in-progress reps
    const state = stateRef.current;
    if (state.reps > 0 && !allDoneRef.current) {
      totalRepsRef.current    += state.reps;
      completedSetsRef.current += 1;
    }

    allDoneRef.current = true;
    setPhase("all_done");

    return buildResult(sessionId, roadmapDayExerciseId);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Cleanup on unmount ────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      clearTimeout(nextSetTimerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (landmarkerRef.current) {
        try { landmarkerRef.current.close(); } catch (_) {}
      }
    };
  }, []);

  return {
    videoRef,
    canvasRef,
    phase,
    errorMsg,
    // display values
    reps:         displayReps,
    currentSet:   displaySet,
    totalSets:    plannedSets,
    calories:     displayCalories,
    formScore:    displayForm,
    feedback:     displayFeedback,
    plankSeconds: displayPlank,
    exerciseName,
    // actions
    start,
    nextSet,
    stop,
    buildResult,
  };
}
