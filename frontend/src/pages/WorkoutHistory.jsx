import { useEffect, useState } from "react";
import { Calendar, Flame, Target, CheckCircle } from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";
import { getSessions } from "../api/client.js";

function formatDate(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function formatDuration(seconds) {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

export default function WorkoutHistory() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    getSessions()
      .then((data) => setSessions(data?.results || data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardLayout>
      <section className="dashboard-content">
        <div className="dash-header">
          <div>
            <h1>Workout History</h1>
            <p className="dash-sub">Every session you've completed.</p>
          </div>
        </div>

        {loading && <p style={{ color: "#aaa" }}>Loading…</p>}

        {!loading && sessions.length === 0 && (
          <div className="plan-card">
            <p style={{ color: "#aaa", margin: 0 }}>
              No workout sessions yet. Start your first workout from the Dashboard.
            </p>
          </div>
        )}

        <div className="session-list">
          {sessions.map((s) => (
            <div key={s.id} className="session-card">
              <div
                className="session-header"
                onClick={() => setExpanded(expanded === s.id ? null : s.id)}
              >
                <div>
                  <div className="session-date">
                    <Calendar size={14} />
                    {formatDate(s.started_at)}
                  </div>
                  <div className="session-meta">
                    {formatDuration(s.total_duration_seconds)} ·{" "}
                    {s.total_calories_burned} kcal
                    {s.average_posture_score && ` · Score: ${s.average_posture_score}`}
                  </div>
                </div>
                <div className="session-badge-row">
                  {s.completed ? (
                    <span className="badge green"><CheckCircle size={12} /> Done</span>
                  ) : (
                    <span className="badge grey">In progress</span>
                  )}
                  <span className="session-expand">{expanded === s.id ? "▲" : "▼"}</span>
                </div>
              </div>

              {expanded === s.id && s.exercise_logs?.length > 0 && (
                <div className="session-logs">
                  {s.exercise_logs.map((log, i) => (
                    <div key={i} className="log-row">
                      <div className="log-name">{log.exercise?.name}</div>
                      <div className="log-detail">
                        {log.actual_sets} sets × {log.actual_reps} reps ·{" "}
                        {log.calories_burned} kcal
                        {log.posture_score && ` · Form: ${log.posture_score}`}
                        {log.incorrect_reps > 0 && (
                          <span className="log-bad"> · {log.incorrect_reps} bad reps</span>
                        )}
                        {log.completed && <span className="log-check"> ✓</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    </DashboardLayout>
  );
}
