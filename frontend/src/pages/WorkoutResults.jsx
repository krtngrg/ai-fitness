import { useLocation, useNavigate } from "react-router-dom";
import { Trophy, Flame, Target, CheckCircle, AlertCircle, ArrowLeft, Dumbbell } from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";

export default function WorkoutResults() {
  const { state } = useLocation();
  const navigate  = useNavigate();

  const aiResult  = state?.result?.result || state?.result;
  const session   = aiResult?.session;
  const exercises = aiResult?.exercises || [];

  // exerciseSelectionState carries the full exercise list + completed_ids
  // so the user can go back and do remaining exercises without losing progress.
  const exerciseSelectionState = state?.exerciseSelectionState ?? null;

  // Work out how many exercises are still remaining
  const allExercises   = exerciseSelectionState?.exercises ?? [];
  const completedIds   = new Set(exerciseSelectionState?.completed_ids ?? []);
  const remainingCount = allExercises.filter(
    (ex) => !completedIds.has(ex.roadmap_day_exercise_id)
  ).length;
  const hasMore = exerciseSelectionState != null && remainingCount > 0;

  if (!session) {
    return (
      <DashboardLayout>
        <section className="dashboard-content">
          <p style={{ color: "#aaa" }}>No workout result found.</p>
          <button className="btn light" onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </section>
      </DashboardLayout>
    );
  }

  function formatDuration(s) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  }

  return (
    <DashboardLayout>
      <section className="dashboard-content">
        <div className="dash-header">
          <div>
            <h1>
              {hasMore ? "Exercise Complete 💪" : "Workout Complete 🎉"}
            </h1>
            <p className="dash-sub">
              {hasMore
                ? `${remainingCount} exercise${remainingCount > 1 ? "s" : ""} remaining in today's workout.`
                : "Great work! Here's your session summary."}
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

        {/* Session summary */}
        <div className="dash-stats" style={{ marginBottom: 24 }}>
          <div className="dash-stat-card">
            <div className="dash-stat-icon"><Flame size={18} /></div>
            <div>
              <div className="dash-stat-val">{session.total_calories_burned} kcal</div>
              <div className="dash-stat-label">Calories Burned</div>
            </div>
          </div>
          <div className="dash-stat-card">
            <div className="dash-stat-icon"><Target size={18} /></div>
            <div>
              <div className="dash-stat-val">{formatDuration(session.total_duration_seconds)}</div>
              <div className="dash-stat-label">Duration</div>
            </div>
          </div>
          <div className="dash-stat-card">
            <div className="dash-stat-icon"><Trophy size={18} /></div>
            <div>
              <div className="dash-stat-val">{session.average_posture_score ?? "—"} / 100</div>
              <div className="dash-stat-label">Form Score</div>
            </div>
          </div>
        </div>

        {/* Per-exercise results */}
        {exercises.map((ex, i) => (
          <div key={i} className="plan-card" style={{ marginBottom: 16 }}>
            <div className="plan-card-title" style={{ marginBottom: 8 }}>
              {ex.exercise_name ||
                ex.exercise_slug.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </div>

            <div className="exercise-list">
              <div className="exercise-row">
                <div className="exercise-name">Reps completed</div>
                <div className="exercise-detail">{ex.actual_reps}</div>
              </div>
              <div className="exercise-row">
                <div className="exercise-name">
                  <CheckCircle size={13} color="#22c55e" /> Correct reps
                </div>
                <div className="exercise-detail" style={{ color: "#22c55e" }}>{ex.correct_reps}</div>
              </div>
              {ex.incorrect_reps > 0 && (
                <div className="exercise-row">
                  <div className="exercise-name">
                    <AlertCircle size={13} color="#f87171" /> Incorrect reps
                  </div>
                  <div className="exercise-detail" style={{ color: "#f87171" }}>{ex.incorrect_reps}</div>
                </div>
              )}
              <div className="exercise-row">
                <div className="exercise-name">Calories</div>
                <div className="exercise-detail">{ex.calories_burned} kcal</div>
              </div>
              <div className="exercise-row">
                <div className="exercise-name">Form score</div>
                <div className="exercise-detail">{ex.posture_score ?? "—"} / 100</div>
              </div>
            </div>

            {ex.posture_events?.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={{ color: "#aaa", fontSize: 12, marginBottom: 6 }}>Feedback:</div>
                {ex.posture_events.map((ev, j) => (
                  <div key={j} style={{ color: "#f87171", fontSize: 13, marginBottom: 4 }}>
                    • {ev.feedback}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Remaining exercises preview */}
        {hasMore && (
          <div className="plan-card" style={{ marginBottom: 20 }}>
            <div className="plan-card-title" style={{ marginBottom: 10 }}>
              Up next
            </div>
            {allExercises
              .filter((ex) => !completedIds.has(ex.roadmap_day_exercise_id))
              .map((ex) => (
                <div key={ex.roadmap_day_exercise_id} className="exercise-row">
                  <div className="exercise-name" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <Dumbbell size={13} color="#63cab7" />
                    {ex.exercise_name}
                  </div>
                  <div className="exercise-detail">
                    {ex.planned_sets} × {ex.planned_reps ? `${ex.planned_reps} reps` : `${ex.planned_duration_seconds}s`}
                  </div>
                </div>
              ))}
          </div>
        )}

        <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
          {hasMore ? (
            <button
              className="start-btn"
              onClick={() =>
                navigate("/exercise-selection", { state: exerciseSelectionState })
              }
            >
              <Dumbbell size={15} /> Continue — Next Exercise
            </button>
          ) : (
            <button className="start-btn" onClick={() => navigate("/dashboard")}>
              <CheckCircle size={15} /> Back to Dashboard
            </button>
          )}
          <button className="btn ghost" onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </div>
      </section>
    </DashboardLayout>
  );
}
