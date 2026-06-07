export default function StatCard({ value, label }) {
  return (
    <div className="stat-card">
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );
}