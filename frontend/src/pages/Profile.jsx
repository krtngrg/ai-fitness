import { useEffect, useState } from "react";
import { Save, LogOut } from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";
import { getProfile, patchProfile } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useNavigate } from "react-router-dom";

const ACTIVITY_OPTIONS = [
  { value: "sedentary", label: "Sedentary" },
  { value: "light", label: "Light" },
  { value: "moderate", label: "Moderate" },
  { value: "active", label: "Active" },
  { value: "very_active", label: "Very Active" },
];

export default function Profile() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    age: "", gender: "", height_cm: "", current_weight_kg: "", activity_level: "moderate",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getProfile()
      .then((p) => {
        setForm({
          age: p.age || "",
          gender: p.gender || "",
          height_cm: p.height_cm || "",
          current_weight_kg: p.current_weight_kg || "",
          activity_level: p.activity_level || "moderate",
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  function set(key, val) {
    setForm((prev) => ({ ...prev, [key]: val }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      await patchProfile(form);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <DashboardLayout>
      <section className="dashboard-content">
        <div className="dash-header">
          <div>
            <h1>Profile</h1>
            <p className="dash-sub">{user?.email}</p>
          </div>
          <button className="outline-btn" onClick={handleLogout}>
            <LogOut size={15} /> Sign out
          </button>
        </div>

        {loading ? (
          <p style={{ color: "#aaa" }}>Loading…</p>
        ) : (
          <form className="goal-card profile-form" onSubmit={handleSave}>
            {error && <div className="form-error" style={{ marginBottom: 16 }}>{error}</div>}
            {saved && <div className="form-success" style={{ marginBottom: 16 }}>Profile saved ✓</div>}

            <div className="form-grid">
              <label>
                Age
                <input type="number" value={form.age} onChange={(e) => set("age", e.target.value)} min={13} max={100} />
              </label>

              <div>
                <p className="field-title">Gender</p>
                <div className="gender-grid">
                  {[["male","M"],["female","F"],["other","O"]].map(([val, label]) => (
                    <button
                      key={val}
                      type="button"
                      className={form.gender === val ? "gender-btn active" : "gender-btn"}
                      onClick={() => set("gender", val)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <label>
                Height (cm)
                <input type="number" value={form.height_cm} onChange={(e) => set("height_cm", e.target.value)} step="0.1" />
              </label>

              <label>
                Current Weight (kg)
                <input type="number" value={form.current_weight_kg} onChange={(e) => set("current_weight_kg", e.target.value)} step="0.1" />
              </label>
            </div>

            <div style={{ marginTop: 24 }}>
              <p className="field-title">Activity Level</p>
              <select className="activity-select" value={form.activity_level} onChange={(e) => set("activity_level", e.target.value)}>
                {ACTIVITY_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            <div className="goal-divider" />

            <button type="submit" className="generate-btn" disabled={saving}>
              {saving ? "Saving…" : "Save Profile"} <Save size={18} />
            </button>
          </form>
        )}
      </section>
    </DashboardLayout>
  );
}
