import { Link } from "react-router-dom";
import { Activity } from "lucide-react";

export default function Navbar() {
  return (
    <nav className="nav">
      <Link to="/" className="brand">
        <Activity size={18} />
        <span>MoveMate AI</span>
      </Link>

      <div className="nav-actions">
        <Link to="/login" className="btn ghost">
          Log In
        </Link>
        <Link to="/register" className="btn light">
          Get Started Free
        </Link>
      </div>
    </nav>
  );
}