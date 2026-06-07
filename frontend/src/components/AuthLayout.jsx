import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity, Camera, Brain, ChartNoAxesColumn, Shield, Trophy, Zap,
} from "lucide-react";

import FeatureCard from "./FeatureCard.jsx";
import { login as apiLogin, register as apiRegister } from "../api/client.js";
import { useAuth } from "../context/AuthContext.jsx";

export default function AuthLayout({ type }) {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const isLogin = type === "login";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!isLogin && password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (!isLogin && !agreed) {
      setError("Please agree to the Terms of Service.");
      return;
    }

    setLoading(true);
    try {
      if (isLogin) {
        const data = await apiLogin({ email, password });
        setUser({ email: data.email, name: data.username });
        navigate("/dashboard");
      } else {
        await apiRegister({ name, email, password });
        const data = await apiLogin({ email, password });
        setUser({ email: data.email, name: data.username });
        navigate("/goal-planner");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-left">
        <div className="auth-brand">
          <div className="logo"><Activity size={24} /></div>
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
            text={isLogin ? "Webcam-based real-time form tracking" : "Get your personalized fitness plan in seconds"}
          />
          <FeatureCard
            icon={isLogin ? <Brain size={18} /> : <Shield size={18} />}
            title={isLogin ? "AI Goal Planner" : "Safe & Science-Backed"}
            text={isLogin ? "Personalized plans generated instantly" : "Plans designed for sustainable progress"}
          />
          <FeatureCard
            icon={isLogin ? <ChartNoAxesColumn size={18} /> : <Trophy size={18} />}
            title={isLogin ? "Progress Dashboard" : "Track Every Win"}
            text={isLogin ? "Charts, streaks, and calorie tracking" : "Celebrate milestones and streaks daily"}
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

          {error && <div className="form-error">{error}</div>}

          {!isLogin && (
            <label>
              Full Name
              <input
                type="text"
                placeholder="Alex Johnson"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
          )}

          <label>
            Email
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              placeholder={isLogin ? "••••••••" : "Create a password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </label>

          {!isLogin && (
            <label>
              Confirm Password
              <input
                type="password"
                placeholder="Repeat your password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
              />
            </label>
          )}

          {!isLogin && (
            <div className="terms-box">
              <input
                type="checkbox"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
              />
              <span>I agree to the Terms of Service and Privacy Policy</span>
            </div>
          )}

          {isLogin && (
            <div className="forgot-password">
              <a href="#">Forgot password?</a>
            </div>
          )}

          <button className="submit-btn" type="submit" disabled={loading}>
            {loading ? "Please wait…" : isLogin ? "Login" : "Create Account →"}
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
