import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, ClipboardList, History, User, Activity, Map,
} from "lucide-react";

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Activity size={20} />
          <h2>MoveMate AI</h2>
        </div>
        <p>Elite Performance</p>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/dashboard"
          className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
        >
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </NavLink>

        <NavLink
          to="/goal-planner"
          className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
        >
          <ClipboardList size={18} />
          <span>Goal Planner</span>
        </NavLink>

        <NavLink
          to="/roadmap"
          className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
        >
          <Map size={18} />
          <span>Full Roadmap</span>
        </NavLink>

        <NavLink
          to="/workout-history"
          className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
        >
          <History size={18} />
          <span>Workout History</span>
        </NavLink>

        <NavLink
          to="/profile"
          className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}
        >
          <User size={18} />
          <span>Profile</span>
        </NavLink>
      </nav>
    </aside>
  );
}
