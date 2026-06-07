import { useState } from "react";
import { Zap } from "lucide-react";
import DashboardLayout from "../components/DashboardLayout.jsx";

export default function GoalPlanner() {
  const [gender, setGender] = useState("M");

  return (
    <DashboardLayout>
      <section className="goal-page">
        <div className="goal-header">
          <h1>Define Parameters</h1>
          <p>
            Input your metrics to engineer a precision-calibrated performance
            protocol.
          </p>
        </div>

        <form className="goal-card">
          <div className="form-grid">
            <label>
              Age
              <input defaultValue="25" type="number" />
            </label>

            <div>
              <p className="field-title">Gender</p>

              <div className="gender-grid">
                {["M", "F", "O"].map((item) => (
                  <button
                    key={item}
                    type="button"
                    className={gender === item ? "gender-btn active" : "gender-btn"}
                    onClick={() => setGender(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>

            <label>
              Height (cm)
              <input defaultValue="180" type="number" />
            </label>

            <label>
              Current Weight (kg)
              <input defaultValue="75" type="number" />
            </label>

            <label>
              Target Weight (kg)
              <input defaultValue="70" type="number" />
            </label>

            <label>
              Duration (weeks)
              <input defaultValue="12" type="number" />
            </label>
          </div>

          <div className="goal-divider"></div>

          <button type="button" className="generate-btn">
            Generate AI Plan <Zap size={18} fill="black" />
          </button>
        </form>
      </section>
    </DashboardLayout>
  );
}