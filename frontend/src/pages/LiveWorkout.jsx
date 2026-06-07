import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Camera, CheckCircle, Loader, ArrowLeft } from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";

const AI_URL = import.meta.env.VITE_AI_SERVICE_URL || "http://127.0.0.1:9001";
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

export default function LiveWorkout() {
  const { state } = useLocation();
  const navigate = useNavigate();

  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [errorMsg, setErrorMsg] = useState("");
  const [result, setResult] = useState(null);

  if (!state?.session_id) {
    return (
      <DashboardLayout>
        <section className="dashboard-content">
          <p style={{ color: "#aaa" }}>No workout session found.</p>
          <button className="btn light" onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </section>
      </DashboardLayout>
    );
  }

  const {
    session_id,
    roadmap_day_exercise_id,
    exercise_slug,
    exercise_name,
    planned_sets,
    planned_reps,
    planned_duration_seconds,
    planned_calories,
  } = state;

  async function handleStartAI() {
    setStatus("running");
    setErrorMsg("");

    // Get access token from localStorage (set by login response)
    const accessToken = localStorage.getItem("access_token") || null;
    const callbackUrl = `${API_BASE}/fitness/workout-sessions/${session_id}/ai-result/`;

    try {
      const resp = await fetch(`${AI_URL}/ai/start-workout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id,
          exercise_slug,
          planned_sets,
          planned_reps,
          planned_duration_seconds,
          roadmap_day_exercise_id,
          backend_callback_url: callbackUrl,
          access_token: accessToken,
        }),
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data?.detail || `AI service error ${resp.status}`);
      }

      setResult(data);
      setStatus("done");
    } catch (err) {
      setErrorMsg(err.message);
      setStatus("error");
    }
  }

  function handleViewResults() {
    navigate("/workout-results", { state: { result, session_id } });
  }

  return (
    <DashboardLayout>
      <section className="dashboard-content">
        <div className="dash-header">
          <div>
            <h1>{exercise_name}</h1>
            <p className="dash-sub">
              {planned_sets} sets ×{" "}
              {planned_reps ? `${planned_reps} reps` : `${planned_duration_seconds}s`}
              {" · "}
              {planned_calories} kcal planned
            </p>
          </div>
          <button
            className="btn ghost"
            onClick={() => navigate(-1)}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <ArrowLeft size={15} /> Back
          </button>
        </div>

        <div className="plan-card" style={{ maxWidth: 520 }}>
          <div style={{ marginBottom: 12, color: "#aaa", fontSize: 13 }}>
            Session ID: <code style={{ color: "#fff" }}>{session_id}</code>
          </div>

          {status === "idle" && (
            <>
              <p style={{ color: "#ccc", marginBottom: 20 }}>
                Click the button below to open the local webcam AI window.
                Perform your exercise — the AI will count your reps and track your form.
                Press <kbd style={{ background: "#222", padding: "2px 6px", borderRadius: 4 }}>Q</kbd> in the webcam window to finish.
              </p>
              <button className="start-btn" onClick={handleStartAI} style={{ width: "100%", justifyContent: "center" }}>
                <Camera size={16} /> Start Local AI Camera
              </button>
            </>
          )}

          {status === "running" && (
            <div style={{ textAlign: "center", padding: "24px 0" }}>
              <Loader size={32} style={{ animation: "spin 1s linear infinite", marginBottom: 12 }} />
              <p style={{ color: "#aaa" }}>
                AI camera running…<br />
                Complete your exercise in the webcam window, then press Q to finish.
              </p>
            </div>
          )}

          {status === "done" && (
            <div style={{ textAlign: "center" }}>
              <CheckCircle size={40} color="#22c55e" style={{ marginBottom: 12 }} />
              <p style={{ color: "#22c55e", fontWeight: 700, marginBottom: 16 }}>
                Workout complete! Result saved.
              </p>
              <button className="start-btn" onClick={handleViewResults} style={{ width: "100%", justifyContent: "center" }}>
                View Results
              </button>
            </div>
          )}

          {status === "error" && (
            <div>
              <p className="form-error" style={{ marginBottom: 16 }}>
                {errorMsg}
              </p>
              <p style={{ color: "#aaa", fontSize: 13, marginBottom: 16 }}>
                Make sure the AI service is running:<br />
                <code style={{ color: "#fff" }}>
                  uvicorn ai_model.api_server:app --host 127.0.0.1 --port 9001 --reload
                </code>
              </p>
              <button className="start-btn" onClick={handleStartAI}>
                Retry
              </button>
            </div>
          )}
        </div>
      </section>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        kbd { font-family: monospace; }
      `}</style>
    </DashboardLayout>
  );
}
