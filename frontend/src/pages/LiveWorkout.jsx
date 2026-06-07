/**
 * LiveWorkout.jsx — in-browser webcam AI workout
 *
 * KEY DESIGN RULE:
 *   <video> and <canvas> are rendered ONCE, unconditionally, always in the DOM.
 *   Different "phases" are shown as overlays on top of the canvas area — never
 *   by unmounting the video element, which would destroy the srcObject and cause
 *   a black screen.
 */

import { useRef, useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Camera, CheckCircle, Loader, ArrowLeft,
  SkipForward, StopCircle, Maximize2,
} from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";
import useWebcamPose from "../hooks/useWebcamPose.js";
import { saveAIResult } from "../api/client.js";

export default function LiveWorkout() {
  const { state }  = useLocation();
  const navigate   = useNavigate();
  const [saving,    setSaving]    = useState(false);
  const [saveError, setSaveError] = useState("");
  const containerRef = useRef(null);
  const hasSavedRef  = useRef(false);

  // Safe defaults so hook always gets valid values
  const session_id               = state?.session_id              ?? "";
  const roadmap_day_exercise_id  = state?.roadmap_day_exercise_id ?? null;
  const exercise_slug            = state?.exercise_slug           ?? "squat";
  const exercise_name            = state?.exercise_name           ?? "Exercise";
  const planned_sets             = state?.planned_sets            ?? 3;
  const planned_reps             = state?.planned_reps            ?? null;
  const planned_duration_seconds = state?.planned_duration_seconds ?? null;
  const planned_calories         = state?.planned_calories        ?? 0;

  // Hook ALWAYS called unconditionally (React Rules of Hooks)
  const pose = useWebcamPose({
    exerciseSlug:           exercise_slug,
    plannedSets:            planned_sets,
    plannedReps:            planned_reps,
    plannedDurationSeconds: planned_duration_seconds,
  });

  // Auto-save when all sets complete
  useEffect(() => {
    if (pose.phase === "all_done" && !saving && !hasSavedRef.current) {
      handleFinish();
    }
  }, [pose.phase]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Handlers ──────────────────────────────────────────────────────────────
  async function handleFinish() {
    if (hasSavedRef.current || saving) return;
    hasSavedRef.current = true;
    setSaving(true);
    setSaveError("");
    const payload = pose.buildResult(session_id, roadmap_day_exercise_id);
    try {
      await saveAIResult(session_id, payload);
      // Build updated exerciseSelectionState with this exercise marked done
      const prevSelState = state?.exerciseSelectionState ?? null;
      const updatedSelState = prevSelState
        ? {
            ...prevSelState,
            completed_ids: [
              ...new Set([...(prevSelState.completed_ids || []), roadmap_day_exercise_id]),
            ],
          }
        : null;
      navigate("/workout-results", {
        state: { result: payload, session_id, exerciseSelectionState: updatedSelState },
      });
    } catch (err) {
      hasSavedRef.current = false;
      setSaveError(err.message || "Failed to save results.");
      setSaving(false);
    }
  }

  async function handleStopEarly() {
    if (hasSavedRef.current) return;
    hasSavedRef.current = true;
    const payload = pose.stop(session_id, roadmap_day_exercise_id);
    setSaving(true);
    try {
      await saveAIResult(session_id, payload);
      const prevSelState = state?.exerciseSelectionState ?? null;
      const updatedSelState = prevSelState
        ? {
            ...prevSelState,
            completed_ids: [
              ...new Set([...(prevSelState.completed_ids || []), roadmap_day_exercise_id]),
            ],
          }
        : null;
      navigate("/workout-results", {
        state: { result: payload, session_id, exerciseSelectionState: updatedSelState },
      });
    } catch (err) {
      hasSavedRef.current = false;
      setSaveError(err.message || "Failed to save results.");
      setSaving(false);
    }
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  }

  // ── Guard: no session ─────────────────────────────────────────────────────
  if (!state?.session_id) {
    return (
      <DashboardLayout>
        <section className="dashboard-content">
          <p style={{ color: "#aaa" }}>No workout session found. Start from the dashboard.</p>
          <button className="btn light" style={{ marginTop: 16 }}
            onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </section>
      </DashboardLayout>
    );
  }

  // ── Determine what to show as the "phase overlay" ─────────────────────────
  const isIdle    = pose.phase === "idle";
  const isLoading = pose.phase === "loading";
  const isError   = pose.phase === "error";
  const isActive  = pose.phase === "active" || pose.phase === "set_done" || pose.phase === "all_done";
  // Show the canvas area whenever we are loading, active, or done
  const showCanvas = isLoading || isActive;

  return (
    <DashboardLayout>

      {/*
        ── IDLE SCREEN ────────────────────────────────────────────────────────
        Shown before start. video/canvas not yet needed but are still
        rendered off-screen so videoRef is always valid.
      */}
      {isIdle && (
        <section className="dashboard-content">
          {/* Hidden video always in DOM so videoRef survives phase transitions */}
          <video
            ref={pose.videoRef}
            muted
            playsInline
            autoPlay
            style={{ position: "fixed", width: 1, height: 1, opacity: 0, pointerEvents: "none" }}
          />
          <div className="dash-header">
            <div>
              <h1>{exercise_name}</h1>
              <p className="dash-sub">
                {planned_sets} sets ×{" "}
                {planned_reps
                  ? `${planned_reps} reps`
                  : planned_duration_seconds
                  ? `${planned_duration_seconds}s`
                  : "—"}
                {" · "}{planned_calories} kcal planned
              </p>
            </div>
            <button className="btn ghost" onClick={() => navigate(-1)}
              style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <ArrowLeft size={15} /> Back
            </button>
          </div>

          <div className="live-workout-idle-card">
            <div className="live-workout-icon-ring">
              <Camera size={36} color="#63cab7" />
            </div>
            <h2>Ready to start?</h2>
            <p>
              Your webcam opens right here in the browser. The AI counts your reps
              and scores your form in real time — no app required.
            </p>
            <ul className="live-workout-tips">
              <li>📏 Step back so your <strong>full body</strong> fits the frame</li>
              <li>💡 Room must be <strong>well-lit</strong> — avoid back-lighting</li>
              <li>🔄 Push-ups &amp; planks: use a <strong>side profile</strong> view</li>
              <li>👟 Lunges: face the camera, step <strong>forward</strong></li>
            </ul>
            <button
              className="start-btn"
              style={{ width: "100%", justifyContent: "center", marginTop: 8 }}
              onClick={pose.start}
            >
              <Camera size={16} /> Start AI Webcam Workout
            </button>
          </div>
        </section>
      )}

      {/*
        ── ERROR SCREEN ───────────────────────────────────────────────────────
      */}
      {isError && (
        <section className="dashboard-content">
          {/* Hidden video so Retry can reuse the same ref */}
          <video
            ref={pose.videoRef}
            muted
            playsInline
            autoPlay
            style={{ position: "fixed", width: 1, height: 1, opacity: 0, pointerEvents: "none" }}
          />
          <div className="live-workout-idle-card">
            <p className="form-error" style={{ marginBottom: 16 }}>
              {pose.errorMsg}
            </p>
            <p style={{ color: "#aaa", fontSize: 13, marginBottom: 20 }}>
              Common fixes:
              <br />• Allow camera permission in your browser address bar
              <br />• Use <strong>localhost</strong> (not 127.0.0.1) — some browsers require it
              <br />• Close other apps that may be using the camera
            </p>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="start-btn" onClick={pose.start}>Retry</button>
              <button className="btn ghost" onClick={() => navigate(-1)}>Back</button>
            </div>
          </div>
        </section>
      )}

      {/*
        ── SAVING SCREEN ──────────────────────────────────────────────────────
      */}
      {saving && (
        <section className="dashboard-content"
          style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 80 }}>
          <div style={{ animation: "spin 1s linear infinite" }}>
            <Loader size={40} color="#63cab7" />
          </div>
          <h2 style={{ marginTop: 24 }}>Saving results…</h2>
          {saveError && (
            <>
              <p className="form-error" style={{ marginTop: 12 }}>{saveError}</p>
              <button className="start-btn" style={{ marginTop: 16 }}
                onClick={() => { hasSavedRef.current = false; handleFinish(); }}>
                Retry Save
              </button>
            </>
          )}
          <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
        </section>
      )}

      {/*
        ── CANVAS WORKOUT VIEW (loading + active + set_done + all_done) ───────
        This section is ALWAYS rendered once showCanvas is true.
        We never unmount it — only hide it — so the <video> srcObject survives.
      */}
      {showCanvas && !saving && (
        <section className="live-workout-section">

          {/* Top bar */}
          <div className="live-workout-topbar">
            <div>
              <span className="live-workout-title">{exercise_name}</span>
              <span className="live-workout-subtitle">
                {" "}Set {pose.currentSet}/{pose.totalSets}
                {" · "}
                {planned_reps
                  ? `${planned_reps} reps`
                  : planned_duration_seconds
                  ? `${planned_duration_seconds}s`
                  : ""}
              </span>
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {(pose.phase === "active" || pose.phase === "set_done") && (
                <button className="btn ghost" onClick={pose.nextSet}
                  style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <SkipForward size={14} /> Next Set
                </button>
              )}
              {pose.phase === "active" && (
                <button className="btn ghost" onClick={handleStopEarly}
                  style={{ display: "flex", alignItems: "center", gap: 5, color: "#f87171" }}>
                  <StopCircle size={14} /> Finish Early
                </button>
              )}
              {pose.phase === "all_done" && !saving && (
                <button className="start-btn" onClick={handleFinish}
                  style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <CheckCircle size={14} /> Save &amp; Continue
                </button>
              )}
              <button className="btn ghost" onClick={toggleFullscreen}
                style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <Maximize2 size={14} />
              </button>
            </div>
          </div>

          {/* Canvas wrap — video hidden, canvas renders mirrored feed + HUD */}
          <div className="live-workout-canvas-wrap" ref={containerRef}
            style={{ position: "relative" }}>

            {/* ── THE VIDEO: always mounted here once showCanvas is true ── */}
            <video
              ref={pose.videoRef}
              muted
              playsInline
              autoPlay
              style={{
                position: "absolute",
                width: 1,
                height: 1,
                opacity: 0,
                pointerEvents: "none",
              }}
            />

            {/* Canvas that shows the mirrored feed + pose HUD */}
            <canvas
              ref={pose.canvasRef}
              className="live-workout-canvas"
              width={1280}
              height={720}
            />

            {/* Loading overlay on top of (blank) canvas while model loads */}
            {isLoading && (
              <div style={{
                position: "absolute", inset: 0,
                display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                background: "rgba(5,5,5,0.88)",
                borderRadius: 12,
              }}>
                <div style={{ animation: "spin 1s linear infinite" }}>
                  <Loader size={44} color="#63cab7" />
                </div>
                <h2 style={{ marginTop: 20, marginBottom: 8, color: "#eeeef5" }}>
                  Starting AI camera…
                </h2>
                <p style={{ color: "#888", maxWidth: 360, textAlign: "center", fontSize: 14 }}>
                  Loading pose model — first load takes 5–10 s.
                  <br />Allow camera access when prompted.
                </p>
                <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
              </div>
            )}
          </div>

          {/* Stats bar */}
          <div className="live-workout-stats-bar">
            <div className="lw-stat">
              <div className="lw-stat-val">
                {exercise_slug === "plank" ? `${pose.plankSeconds}s` : pose.reps}
              </div>
              <div className="lw-stat-label">
                {exercise_slug === "plank" ? "Hold" : "Reps"}
              </div>
            </div>
            <div className="lw-stat">
              <div className="lw-stat-val">{pose.currentSet} / {pose.totalSets}</div>
              <div className="lw-stat-label">Set</div>
            </div>
            <div className="lw-stat">
              <div className="lw-stat-val" style={{
                color: pose.formScore >= 80 ? "#50dc6e"
                     : pose.formScore >= 50 ? "#f0d040"
                     : "#e05050",
              }}>
                {pose.formScore}%
              </div>
              <div className="lw-stat-label">Form</div>
            </div>
            <div className="lw-stat">
              <div className="lw-stat-val" style={{ color: "#63cab7" }}>{pose.calories}</div>
              <div className="lw-stat-label">kcal</div>
            </div>
            <div className="lw-stat lw-feedback">
              <div className="lw-stat-label">Feedback</div>
              <div className="lw-feedback-text">{pose.feedback}</div>
            </div>
          </div>

        </section>
      )}

    </DashboardLayout>
  );
}
