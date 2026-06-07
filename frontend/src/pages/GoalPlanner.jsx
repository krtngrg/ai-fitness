import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Zap, AlertTriangle, CheckCircle } from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";
import { generatePlan } from "../api/client.js";

const ACTIVITY_OPTIONS = [
  { value: "sedentary", label: "Sedentary (little/no exercise)" },
  { value: "light", label: "Light (1–3 days/week)" },
  { value: "moderate", label: "Moderate (3–5 days/week)" },
  { value: "active", label: "Active (6–7 days/week)" },
  { value: "very_active", label: "Very Active (hard exercise daily)" },
];

export default function GoalPlanner() {
  const navigate = useNavigate();

  const [gender, setGender] = useState("male");
  const [form, setForm] = useState({
    age: 25,
    height_cm: 175,
    current_weight_kg: 75,
    target_weight_kg: 70,
    duration_weeks: 8,
    activity_level: "moderate",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  function set(key, val) {
    setForm((prev) => ({ ...prev, [key]: val }));
  }

  async function handleGenerate(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);

    try {
      const data = await generatePlan({
        goal_type: "weight_loss",
        current_weight_kg: parseFloat(form.current_weight_kg),
        target_weight_kg: parseFloat(form.target_weight_kg),
        duration_weeks: parseInt(form.duration_weeks),
        age: parseInt(form.age),
        gender,
        height_cm: parseFloat(form.height_cm),
        activity_level: form.activity_level,
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (result) {
    const r = result.roadmap;
    return (
      <DashboardLayout>
        <section className="goal-page">
          <div className="goal-header">
            <h1>Plan Generated ✓</h1>
            <p>Your personalised roadmap is ready. View the full week-by-week plan or head to the dashboard.</p>
          </div>

          <div className="goal-card plan-result">
            {result.warning && (
              <div className="plan-warning">
                <AlertTriangle size={16} />
                <span>{result.warning}</span>
              </div>
            )}

            <div className="plan-stats">
              <div className="plan-stat">
                <span className="plan-stat-label">Plan Title</span>
                <span className="plan-stat-value">{r.title}</span>
              </div>
              <div className="plan-stat">
                <span className="plan-stat-label">Duration</span>
                <span className="plan-stat-value">{r.total_weeks} weeks · {r.total_days} days</span>
              </div>
              <div className="plan-stat">
                <span className="plan-stat-label">Daily Burn Target</span>
                <span className="plan-stat-value">{r.daily_calorie_burn_target} kcal</span>
              </div>
              <div className="plan-stat">
                <span className="plan-stat-label">Weekly Burn Target</span>
                <span className="plan-stat-value">{r.weekly_calorie_burn_target} kcal</span>
              </div>
              <div className="plan-stat">
                <span className="plan-stat-label">Total Calorie Deficit</span>
                <span className="plan-stat-value">{r.estimated_total_calorie_deficit?.toLocaleString()} kcal</span>
              </div>
            </div>

            <p className="plan-summary">{r.ai_summary}</p>

            <div className="plan-actions">
              <button className="generate-btn" onClick={() => navigate(`/roadmap/${r.id}`)}>
                View Full Plan (Week by Week) <CheckCircle size={18} />
              </button>
              <button className="generate-btn outline" onClick={() => navigate("/dashboard")}>
                Go to Dashboard
              </button>
              <button className="generate-btn outline" onClick={() => setResult(null)}>
                Make a new plan
              </button>
            </div>
          </div>
        </section>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <section className="goal-page">
        <div className="goal-header">
          <h1>Define Parameters</h1>
          <p>Input your metrics to engineer a precision-calibrated performance protocol.</p>
        </div>

        <form className="goal-card" onSubmit={handleGenerate}>
          {error && <div className="form-error" style={{ marginBottom: 20 }}>{error}</div>}

          <div className="form-grid">
            <label>
              Age
              <input
                type="number"
                value={form.age}
                onChange={(e) => set("age", e.target.value)}
                min={13}
                max={100}
                required
              />
            </label>

            <div>
              <p className="field-title">Gender</p>
              <div className="gender-grid">
                {[["male", "M"], ["female", "F"], ["other", "O"]].map(([val, label]) => (
                  <button
                    key={val}
                    type="button"
                    className={gender === val ? "gender-btn active" : "gender-btn"}
                    onClick={() => setGender(val)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <label>
              Height (cm)
              <input
                type="number"
                value={form.height_cm}
                onChange={(e) => set("height_cm", e.target.value)}
                min={100}
                max={250}
                required
              />
            </label>

            <label>
              Current Weight (kg)
              <input
                type="number"
                value={form.current_weight_kg}
                onChange={(e) => set("current_weight_kg", e.target.value)}
                min={30}
                max={300}
                step="0.1"
                required
              />
            </label>

            <label>
              Target Weight (kg)
              <input
                type="number"
                value={form.target_weight_kg}
                onChange={(e) => set("target_weight_kg", e.target.value)}
                min={30}
                max={300}
                step="0.1"
                required
              />
            </label>

            <label>
              Duration (weeks)
              <input
                type="number"
                value={form.duration_weeks}
                onChange={(e) => set("duration_weeks", e.target.value)}
                min={1}
                max={52}
                required
              />
            </label>
          </div>

          <div style={{ marginTop: 24 }}>
            <p className="field-title">Activity Level</p>
            <select
              className="activity-select"
              value={form.activity_level}
              onChange={(e) => set("activity_level", e.target.value)}
            >
              {ACTIVITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div className="goal-divider" />

          <button type="submit" className="generate-btn" disabled={loading}>
            {loading ? "Generating…" : "Generate AI Plan"} <Zap size={18} />
          </button>
        </form>
      </section>
    </DashboardLayout>
  );
}
