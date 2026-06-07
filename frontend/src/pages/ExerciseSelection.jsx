/**
 * ExerciseSelection.jsx
 *
 * Shows today's exercises. Each card has a "Start AI Camera" button that
 * goes directly to the in-browser webcam workout.
 *
 * Tracks which exercises are already completed so the user can work through
 * all exercises in one session without restarting.
 */

import { useLocation, useNavigate } from "react-router-dom";
import { Zap, Clock, Dumbbell, ArrowLeft, Camera, CheckCircle } from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";

export default function ExerciseSelection() {
  const { state } = useLocation();
  const navigate = useNavigate();

  const sessionId    = state?.session_id;
  const exercises    = state?.exercises || [];
  // Set of roadmap_day_exercise_ids that are already done this session
  const completedIds = new Set(state?.completed_ids || []);

  if (!sessionId) {
    return (
      <DashboardLayout>
        <section className="dashboard-content">
          <p style={{ color: "#aaa" }}>
            No active session. Go back to Dashboard and click Start Workout.
          </p>
          <button className="btn light" onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </section>
      </DashboardLayout>
    );
  }

  const remaining = exercises.filter(
    (ex) => !completedIds.has(ex.roadmap_day_exercise_id)
  );
  const allDone = remaining.length === 0;

  function handleStart(ex) {
    navigate("/live-workout", {
      state: {
        // exercise details
        session_id:               sessionId,
        roadmap_day_exercise_id:  ex.roadmap_day_exercise_id,
        exercise_slug:            ex.exercise_slug,
        exercise_name:            ex.exercise_name,
        planned_sets:             ex.planned_sets,
        planned_reps:             ex.planned_reps,
        planned_duration_seconds: ex.planned_duration_seconds,
        planned_calories:         ex.planned_calories,
        has_ai_detection:         ex.has_ai_detection,
        // carry the full list back so results page can return here
        exerciseSelectionState: {
          session_id:    sessionId,
          exercises,
          completed_ids: [...completedIds],   // will add this exercise's id on save
        },
      },
    });
  }

  return (
    <DashboardLayout>
      <section className="dashboard-content">
        <div className="dash-header">
          <div>
            <h1>Today's Workout</h1>
            <p className="dash-sub">
              {allDone
                ? "All exercises complete! Great work."
                : `${remaining.length} of ${exercises.length} remaining — AI webcam tracks your form in the browser.`}
            </p>
          </div>
          <button
            className="btn ghost"
            onClick={() => navigate("/dashboard")}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <ArrowLeft size={15} /> Dashboard
          </button>
        </div>

        {/* Camera tip banner */}
        {!allDone && (
          <div className="exercise-select-tip">
            <Camera size={14} color="#63cab7" />
            <span>
              AI detection runs directly in your browser using your webcam — no external app needed.
              Full body must be visible in the frame.
            </span>
          </div>
        )}

        <div className="exercise-select-list">
          {exercises.map((ex) => {
            const done = completedIds.has(ex.roadmap_day_exercise_id);
            return (
              <div
                key={ex.roadmap_day_exercise_id}
                className={`exercise-select-card ${
                  ex.has_ai_detection && !done ? "exercise-select-card-ai" : ""
                } ${done ? "exercise-select-card-done" : ""}`}
                style={done ? { opacity: 0.55 } : {}}
              >
                <div className="exercise-select-info">
                  <div className="exercise-select-name">
                    <Dumbbell size={16} />
                    {ex.exercise_name}
                    {ex.has_ai_detection && !done && (
                      <span className="ai-badge">AI</span>
                    )}
                    {done && (
                      <span style={{
                        display: "inline-flex", alignItems: "center", gap: 4,
                        color: "#50dc6e", fontSize: 12, marginLeft: 6,
                      }}>
                        <CheckCircle size={13} /> Done
                      </span>
                    )}
                  </div>
                  <div className="exercise-select-detail">
                    {ex.planned_sets} sets ×{" "}
                    {ex.planned_reps
                      ? `${ex.planned_reps} reps`
                      : ex.planned_duration_seconds
                      ? `${ex.planned_duration_seconds}s`
                      : "—"}
                    {" · "}
                    {ex.planned_calories} kcal
                    {!ex.has_ai_detection && (
                      <span style={{ color: "#888", marginLeft: 8, display: "inline-flex", alignItems: "center", gap: 3 }}>
                        <Clock size={12} /> Manual
                      </span>
                    )}
                  </div>
                </div>

                {!done && (
                  <button
                    className={ex.has_ai_detection ? "start-btn" : "btn ghost"}
                    onClick={() => handleStart(ex)}
                    style={{ display: "flex", alignItems: "center", gap: 5, whiteSpace: "nowrap" }}
                  >
                    {ex.has_ai_detection ? (
                      <><Camera size={14} /> Start AI Camera</>
                    ) : (
                      <><Zap size={14} /> Start</>
                    )}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {exercises.length === 0 && (
          <div className="plan-card">
            <p style={{ color: "#aaa", margin: 0 }}>No exercises found for this session.</p>
          </div>
        )}

        {allDone && (
          <div style={{ marginTop: 24, display: "flex", gap: 12 }}>
            <button className="start-btn" onClick={() => navigate("/dashboard")}>
              <CheckCircle size={15} /> Back to Dashboard
            </button>
          </div>
        )}
      </section>
    </DashboardLayout>
  );
}
