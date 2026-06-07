import { useLocation, useNavigate } from "react-router-dom";
import { Zap, Clock, Dumbbell, ArrowLeft } from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";

export default function ExerciseSelection() {
  const { state } = useLocation();
  const navigate = useNavigate();

  const sessionId = state?.session_id;
  const exercises = state?.exercises || [];

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

  function handleStart(ex) {
    navigate("/live-workout", {
      state: {
        session_id: sessionId,
        roadmap_day_exercise_id: ex.roadmap_day_exercise_id,
        exercise_slug: ex.exercise_slug,
        exercise_name: ex.exercise_name,
        planned_sets: ex.planned_sets,
        planned_reps: ex.planned_reps,
        planned_duration_seconds: ex.planned_duration_seconds,
        planned_calories: ex.planned_calories,
        has_ai_detection: ex.has_ai_detection,
      },
    });
  }

  return (
    <DashboardLayout>
      <section className="dashboard-content">
        <div className="dash-header">
          <div>
            <h1>Today's AI Workout</h1>
            <p className="dash-sub">Select an exercise to start with the AI camera.</p>
          </div>
          <button
            className="btn ghost"
            onClick={() => navigate("/dashboard")}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <ArrowLeft size={15} /> Dashboard
          </button>
        </div>

        <div className="exercise-select-list">
          {exercises.map((ex) => (
            <div key={ex.roadmap_day_exercise_id} className="exercise-select-card">
              <div className="exercise-select-info">
                <div className="exercise-select-name">
                  <Dumbbell size={16} />
                  {ex.exercise_name}
                  {ex.has_ai_detection && (
                    <span className="ai-badge">AI</span>
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
                    <span style={{ color: "#888", marginLeft: 6 }}>
                      <Clock size={12} style={{ verticalAlign: "middle" }} /> Manual / timer
                    </span>
                  )}
                </div>
              </div>
              <button
                className="start-btn"
                onClick={() => handleStart(ex)}
              >
                <Zap size={14} /> Start
              </button>
            </div>
          ))}
        </div>
      </section>
    </DashboardLayout>
  );
}
