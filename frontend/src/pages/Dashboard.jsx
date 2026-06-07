import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Flame, Target, Zap, Trophy, TrendingUp, Calendar, Play } from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";
import { getDashboard, getTodayWorkout, startSession } from "../api/client.js";

export default function Dashboard() {
  const navigate = useNavigate();
  const [dash, setDash] = useState(null);
  const [today, setToday] = useState(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      getDashboard().catch((err) => { setError(err.message); return null; }),
      getTodayWorkout().catch(() => null),
    ]).then(([dashData, todayData]) => {
      setDash(dashData);
      setToday(todayData);
      setLoading(false);
    });
  }, []);

  async function handleStartWorkout() {
    if (!today?.roadmap_day_id) return;
    setStarting(true);
    try {
      const data = await startSession(today.roadmap_day_id);
      navigate("/exercise-selection", {
        state: {
          session_id: data.session_id,
          exercises: data.ai_launch?.exercise_options || [],
        },
      });
    } catch (err) {
      alert(err.message);
      setStarting(false);
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="coming-soon"><p>Loading dashboard…</p></div>
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout>
        <div className="coming-soon">
          <p className="form-error">{error}</p>
        </div>
      </DashboardLayout>
    );
  }

  if (!dash?.active_roadmap) {
    return (
      <DashboardLayout>
        <section className="coming-soon">
          <h1>No active plan</h1>
          <p>Generate your first AI fitness plan to get started.</p>
          <button className="generate-btn" style={{ width: "auto", padding: "14px 28px", marginTop: 24 }} onClick={() => navigate("/goal-planner")}>
            Create AI Plan <Zap size={18} />
          </button>
        </section>
      </DashboardLayout>
    );
  }

  const weightLost = dash.current_weight_kg && dash.target_weight_kg
    ? (parseFloat(dash.current_weight_kg) - parseFloat(dash.target_weight_kg)).toFixed(1)
    : null;

  return (
    <DashboardLayout>
      <section className="dashboard-content">
        <div className="dash-header">
          <div>
            <h1>Dashboard</h1>
            <p className="dash-sub">Track your progress, one rep at a time.</p>
          </div>
          {dash.workout_streak > 0 && (
            <div className="streak-badge">
              🔥 {dash.workout_streak} day streak
            </div>
          )}
        </div>

        {/* Stats row */}
        <div className="dash-stats">
          <div className="dash-stat-card">
            <div className="dash-stat-icon"><Flame size={18} /></div>
            <div>
              <div className="dash-stat-val">{dash.today_actual_calories} kcal</div>
              <div className="dash-stat-label">Burned Today</div>
            </div>
          </div>

          <div className="dash-stat-card">
            <div className="dash-stat-icon"><Target size={18} /></div>
            <div>
              <div className="dash-stat-val">{dash.today_planned_calories} kcal</div>
              <div className="dash-stat-label">Planned Today</div>
            </div>
          </div>

          <div className="dash-stat-card">
            <div className="dash-stat-icon"><TrendingUp size={18} /></div>
            <div>
              <div className="dash-stat-val">{dash.weekly_actual_calories} kcal</div>
              <div className="dash-stat-label">Burned This Week</div>
            </div>
          </div>

          <div className="dash-stat-card">
            <div className="dash-stat-icon"><Trophy size={18} /></div>
            <div>
              <div className="dash-stat-val">{dash.total_workouts_completed}</div>
              <div className="dash-stat-label">Workouts Done</div>
            </div>
          </div>

          {dash.average_posture_score && (
            <div className="dash-stat-card">
              <div className="dash-stat-icon"><Zap size={18} /></div>
              <div>
                <div className="dash-stat-val">{dash.average_posture_score}</div>
                <div className="dash-stat-label">Avg Posture Score</div>
              </div>
            </div>
          )}
        </div>

        {/* Active Roadmap */}
        <div className="dash-section">
          <h2>Active Plan</h2>
          <div className="plan-card">
            <div className="plan-card-title">{dash.active_roadmap.title}</div>
            <div className="plan-card-meta">
              {dash.active_roadmap.total_weeks} weeks ·{" "}
              {dash.current_weight_kg} kg → {dash.target_weight_kg} kg
            </div>
            <div className="plan-card-meta">
              Daily target: {dash.active_roadmap.daily_calorie_burn_target} kcal ·{" "}
              Weekly target: {dash.active_roadmap.weekly_calorie_burn_target} kcal
            </div>
          </div>
        </div>

        {/* Today's Workout */}
        <div className="dash-section">
          <h2>Today's Workout</h2>
          {!today ? (
            <div className="plan-card">
              <p style={{ color: "#aaa", margin: 0 }}>No workout scheduled for today.</p>
            </div>
          ) : today.is_rest_day ? (
            <div className="plan-card">
              <div className="plan-card-title">Rest Day 😴</div>
              <p style={{ color: "#aaa", margin: "8px 0 0" }}>
                Take it easy today. Recovery is part of the plan.
              </p>
            </div>
          ) : (
            <div className="plan-card">
              <div className="plan-card-top">
                <div>
                  <div className="plan-card-title">
                    Day {today.day_number} — {today.focus}
                  </div>
                  <div className="plan-card-meta">
                    {today.planned_calories} kcal planned ·{" "}
                    Week {today.week_number}
                    {today.completed && " · ✓ Completed"}
                  </div>
                </div>
                {!today.completed && (
                  <button
                    className="start-btn"
                    onClick={handleStartWorkout}
                    disabled={starting}
                  >
                    <Play size={15} />
                    {starting ? "Starting…" : "Start Workout"}
                  </button>
                )}
              </div>

              <div className="exercise-list">
                {today.exercises?.map((ex, i) => (
                  <div key={i} className="exercise-row">
                    <div className="exercise-name">
                      {ex.exercise}
                      {ex.has_ai_detection && (
                        <span className="ai-badge">AI</span>
                      )}
                    </div>
                    <div className="exercise-detail">
                      {ex.planned_sets} sets ×{" "}
                      {ex.planned_reps
                        ? `${ex.planned_reps} reps`
                        : `${ex.planned_duration_seconds}s`}
                      {" · "}
                      {ex.planned_calories} kcal
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </DashboardLayout>
  );
}
