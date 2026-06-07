import { Link } from "react-router-dom";
import { Camera, Brain, ChartNoAxesColumn } from "lucide-react";

import Navbar from "../components/Navbar.jsx";
import FeatureCard from "../components/FeatureCard.jsx";
import StatCard from "../components/StatCard.jsx";

export default function Landing() {
  return (
    <div className="page">
      <Navbar />

      <section className="hero">
        <div className="pill">✦ AI-Powered Fitness Coach</div>

        <h1>
          Train Smarter. Move Better. Live Longer.
        </h1>

        <p>
          MoveMate AI uses real-time webcam pose detection and AI to coach your
          workouts, track your form, and build personalized fitness plans — all
          in your browser.
        </p>

        <div className="hero-actions">
          <Link to="/register" className="btn light big">
            Start Training Free →
          </Link>

          <button className="btn dark big">
            Watch Demo ▶
          </button>
        </div>
      </section>

      <section className="section">
        <h2>Everything You Need to Reach Your Goals</h2>
        <p>
          A modern AI fitness experience built for clarity, consistency, and real
          progress.
        </p>

        <div className="cards">
          <FeatureCard
            icon={<Camera size={20} />}
            title="Real-Time Pose Detection"
            text="MediaPipe AI tracks your body skeleton live via webcam and counts reps with high accuracy."
          />

          <FeatureCard
            icon={<Brain size={20} />}
            title="AI Goal Planner"
            text="Enter your stats and get a personalized workout and calorie plan generated instantly."
          />

          <FeatureCard
            icon={<ChartNoAxesColumn size={20} />}
            title="Progress Dashboard"
            text="Track weight loss, calories burned, workout streaks, and form scores over time."
          />
        </div>
      </section>

      <section className="stats">
        <StatCard value="10,000+" label="Users" />
        <StatCard value="500K+" label="Reps Tracked" />
        <StatCard value="98%" label="Form Accuracy" />
        <StatCard value="50+" label="Exercises" />
      </section>

      <section className="cta">
        <h2>Ready to Meet Your AI Coach?</h2>
        <p>
          Start training with real-time guidance, personalized plans, and a
          dashboard that keeps you moving forward.
        </p>

        <Link to="/register" className="btn light big">
          Create Free Account →
        </Link>
      </section>

      <footer className="footer">
        <div>MoveMate AI</div>
        <div>© 2025 MoveMate AI. All rights reserved.</div>
        <div>Privacy · Terms · Contact</div>
      </footer>
    </div>
  );
}