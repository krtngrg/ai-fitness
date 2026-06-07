import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Zap, Calendar, Dumbbell, Clock, CheckCircle, Coffee } from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";
import { getRoadmap, getRoadmaps } from "../api/client.js";

const FOCUS_COLORS = {
  "Full Body": "#00bfa5",
  "Core":      "#7c4dff",
  "Lower Body":"#ff6d00",
  "Upper Body":"#0288d1",
  "Cardio":    "#e91e63",
  "Rest":      "#555",
};

function focusBadge(focus) {
  const color = FOCUS_COLORS[focus] || "#888";
  return (
    <span
      style={{
        background: color + "22",
        color,
        border: `1px solid ${color}44`,
        borderRadius: 999,
        padding: "2px 10px",
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: 0.5,
        whiteSpace: "nowrap",
      }}
    >
      {focus}
    </span>
  );
}

export default function RoadmapDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [roadmap, setRoadmap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedWeeks, setExpandedWeeks] = useState({ 1: true }); // week 1 open by default

  useEffect(() => {
    async function load() {
      try {
        let roadmapId = id;
        // If no id provided, load the first (active) roadmap
        if (!roadmapId) {
          const list = await getRoadmaps();
          const active = list.find((r) => r.status === "active") || list[0];
          if (!active) throw new Error("No roadmap found.");
          roadmapId = active.id;
        }
        const data = await getRoadmap(roadmapId);
        setRoadmap(data);
        // Auto-expand the current week
        const today = new Date().toISOString().slice(0, 10);
        const todayDay = data.days?.find((d) => d.workout_date === today);
        if (todayDay) {
          setExpandedWeeks({ [todayDay.week_number]: true });
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  function toggleWeek(week) {
    setExpandedWeeks((prev) => ({ ...prev, [week]: !prev[week] }));
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="coming-soon"><p>Loading roadmap…</p></div>
      </DashboardLayout>
    );
  }

  if (error || !roadmap) {
    return (
      <DashboardLayout>
        <div className="coming-soon">
          <p className="form-error">{error || "Roadmap not found."}</p>
          <button className="btn ghost" onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </div>
      </DashboardLayout>
    );
  }

  // Group days by week number
  const today = new Date().toISOString().slice(0, 10);
  const weeks = {};
  for (const day of roadmap.days || []) {
    if (!weeks[day.week_number]) weeks[day.week_number] = [];
    weeks[day.week_number].push(day);
  }

  const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <DashboardLayout>
      <section className="dashboard-content">
        {/* Header */}
        <div className="dash-header">
          <div>
            <h1>Full Plan Roadmap</h1>
            <p className="dash-sub">{roadmap.title}</p>
          </div>
          <button
            className="btn ghost"
            onClick={() => navigate("/dashboard")}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <ArrowLeft size={15} /> Dashboard
          </button>
        </div>

        {/* Plan summary bar */}
        <div className="roadmap-summary-bar">
          <div className="roadmap-summary-item">
            <Calendar size={14} />
            <span>{roadmap.total_weeks} weeks · {roadmap.total_days} days</span>
          </div>
          <div className="roadmap-summary-item">
            <Zap size={14} />
            <span>{roadmap.daily_calorie_burn_target} kcal/day target</span>
          </div>
          <div className="roadmap-summary-item">
            <Zap size={14} />
            <span>{roadmap.weekly_calorie_burn_target} kcal/week target</span>
          </div>
          {roadmap.warning_message && (
            <div className="roadmap-warning">⚠ {roadmap.warning_message}</div>
          )}
        </div>

        {/* Week-by-week accordion */}
        {Object.keys(weeks)
          .map(Number)
          .sort((a, b) => a - b)
          .map((weekNum) => {
            const days = weeks[weekNum];
            const isOpen = !!expandedWeeks[weekNum];
            const hasToday = days.some((d) => d.workout_date === today);
            const completedCount = days.filter((d) => d.completed && !d.is_rest_day).length;
            const workoutDays = days.filter((d) => !d.is_rest_day).length;

            return (
              <div key={weekNum} className="roadmap-week-block">
                {/* Week header — clickable toggle */}
                <button
                  className={`roadmap-week-header ${hasToday ? "roadmap-week-current" : ""}`}
                  onClick={() => toggleWeek(weekNum)}
                >
                  <div className="roadmap-week-header-left">
                    <span className="roadmap-week-num">Week {weekNum}</span>
                    {hasToday && (
                      <span className="roadmap-current-badge">Current Week</span>
                    )}
                    <span className="roadmap-week-progress">
                      {completedCount}/{workoutDays} workouts done
                    </span>
                  </div>
                  <span className="roadmap-toggle-icon">{isOpen ? "▲" : "▼"}</span>
                </button>

                {/* Days grid */}
                {isOpen && (
                  <div className="roadmap-days-grid">
                    {days.map((day, idx) => {
                      const isToday = day.workout_date === today;
                      return (
                        <div
                          key={day.id}
                          className={`roadmap-day-card ${isToday ? "roadmap-day-today" : ""} ${day.completed ? "roadmap-day-done" : ""} ${day.is_rest_day ? "roadmap-day-rest" : ""}`}
                        >
                          {/* Day card header */}
                          <div className="roadmap-day-header">
                            <div className="roadmap-day-meta">
                              <span className="roadmap-day-name">
                                {DAY_NAMES[idx] || `Day ${day.day_number}`}
                              </span>
                              <span className="roadmap-day-date">
                                {new Date(day.workout_date + "T00:00:00").toLocaleDateString("en-GB", {
                                  day: "numeric",
                                  month: "short",
                                })}
                              </span>
                            </div>
                            <div className="roadmap-day-badges">
                              {focusBadge(day.focus)}
                              {day.completed && (
                                <CheckCircle size={14} color="#00bfa5" style={{ flexShrink: 0 }} />
                              )}
                              {isToday && !day.completed && (
                                <span className="roadmap-today-pill">TODAY</span>
                              )}
                            </div>
                          </div>

                          {/* Rest day */}
                          {day.is_rest_day ? (
                            <div className="roadmap-rest-body">
                              <Coffee size={20} color="#555" />
                              <span>Rest & Recovery</span>
                            </div>
                          ) : (
                            <>
                              {/* Calories line */}
                              <div className="roadmap-day-calories">
                                <Zap size={12} color="#00bfa5" />
                                <span>{day.planned_calories} kcal planned</span>
                              </div>

                              {/* Exercise list */}
                              <div className="roadmap-exercise-list">
                                {(day.exercises || []).map((rde) => (
                                  <div key={rde.id} className="roadmap-exercise-row">
                                    <div className="roadmap-exercise-name">
                                      <Dumbbell size={11} color="#888" />
                                      {rde.exercise.name}
                                      {rde.exercise.has_ai_detection && (
                                        <span className="ai-badge" style={{ fontSize: 9, padding: "1px 5px" }}>AI</span>
                                      )}
                                    </div>
                                    <div className="roadmap-exercise-detail">
                                      {rde.planned_sets} sets ×{" "}
                                      {rde.planned_reps
                                        ? `${rde.planned_reps} reps`
                                        : rde.planned_duration_seconds
                                        ? `${rde.planned_duration_seconds}s`
                                        : "—"}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
      </section>
    </DashboardLayout>
  );
}
