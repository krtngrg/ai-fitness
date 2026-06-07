import { Link, useNavigate } from "react-router-dom";
import {
  Activity,
  Camera,
  Brain,
  ChartNoAxesColumn,
  Shield,
  Trophy,
  Zap,
} from "lucide-react";

import FeatureCard from "./FeatureCard.jsx";

export default function AuthLayout({ type }) {
  const navigate = useNavigate();
  const isLogin = type === "login";

  function handleSubmit(event) {
    event.preventDefault();

    // Later connect Django login/register API here.
    // For now, demo login redirects to Goal Planner dashboard.
    navigate("/goal-planner");
  }

  return (
    <div className="auth-page">
      <div className="auth-left">
        <div className="auth-brand">
          <div className="logo">
            <Activity size={24} />
          </div>
          <h1>MoveMate AI</h1>
        </div>

        <p className="auth-subtitle">
          {isLogin
            ? "Your AI Fitness Coach powered by Real-time Body Tracking"
            : "Join thousands training smarter with AI"}
        </p>

        <div className="auth-features">
          <FeatureCard
            icon={isLogin ? <Camera size={18} /> : <Zap size={18} />}
            title={isLogin ? "Live Pose Detection" : "Instant AI Plan"}
            text={
              isLogin
                ? "Webcam-based real-time form tracking"
                : "Get your personalized fitness plan in seconds"
            }
          />

          <FeatureCard
            icon={isLogin ? <Brain size={18} /> : <Shield size={18} />}
            title={isLogin ? "AI Goal Planner" : "Safe & Science-Backed"}
            text={
              isLogin
                ? "Personalized plans generated instantly"
                : "Plans designed for sustainable progress"
            }
          />

          <FeatureCard
            icon={isLogin ? <ChartNoAxesColumn size={18} /> : <Trophy size={18} />}
            title={isLogin ? "Progress Dashboard" : "Track Every Win"}
            text={
              isLogin
                ? "Charts, streaks, and calorie tracking"
                : "Celebrate milestones and streaks daily"
            }
          />
        </div>
      </div>

      <div className="auth-right">
        <form className="auth-card" onSubmit={handleSubmit}>
          <h2>{isLogin ? "Welcome Back 👋" : "Create Your Account 🚀"}</h2>

          <p>
            {isLogin
              ? "Sign in to continue your fitness journey"
              : "Start your AI fitness journey today — it's free"}
          </p>

          {!isLogin && (
            <label>
              Full Name
              <input type="text" placeholder="Alex Johnson" />
            </label>
          )}

          <label>
            Email
            <input type="email" placeholder="you@example.com" />
          </label>

          <label>
            Password
            <input
              type="password"
              placeholder={isLogin ? "••••••••" : "Create a password"}
            />
          </label>

          {!isLogin && (
            <label>
              Confirm Password
              <input type="password" placeholder="Repeat your password" />
            </label>
          )}

          {!isLogin && (
            <div className="terms-box">
              <input type="checkbox" />
              <span>I agree to the Terms of Service and Privacy Policy</span>
            </div>
          )}

          {isLogin && (
            <div className="forgot-password">
              <a href="#">Forgot password?</a>
            </div>
          )}

          <button className="submit-btn" type="submit">
            {isLogin ? "Login" : "Create Account →"}
          </button>

          <div className="divider">OR</div>

          <button className="google-btn" type="button">
            {isLogin ? "Continue with Google" : "Sign up with Google"}
          </button>

          <p className="switch-page">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <Link to={isLogin ? "/register" : "/login"}>
              {isLogin ? "Create one" : "Sign in"}
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}