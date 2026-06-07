import Sidebar from "./Sidebar.jsx";

export default function DashboardLayout({ children }) {
  return (
    <div className="dashboard-layout">
      <Sidebar />
      <main className="dashboard-main">{children}</main>
    </div>
  );
}