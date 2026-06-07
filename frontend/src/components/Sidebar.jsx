import { NavLink } from "react-router-dom";
import {
  Home,
  ClipboardList,
  ChartNoAxesColumn,
  History,
  User,
} from "lucide-react";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h2>MoveMate AI</h2>
        <p>Elite Performance</p>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/goal-planner" className="sidebar-link">
          <Home size={18} />
          <span>Home</span>
        </NavLink>

        <NavLink to="/goal-planner" className="sidebar-link">
          <ClipboardList size={18} />
          <span>Goal Planner</span>
        </NavLink>

        <NavLink to="/dashboard" className="sidebar-link">
          <ChartNoAxesColumn size={18} />
          <span>Dashboard</span>
        </NavLink>

        <NavLink to="/workout-history" className="sidebar-link">
          <History size={18} />
          <span>Workout History</span>
        </NavLink>

        <NavLink to="/profile" className="sidebar-link">
          <User size={18} />
          <span>Profile</span>
        </NavLink>
      </nav>
    </aside>
  );
}