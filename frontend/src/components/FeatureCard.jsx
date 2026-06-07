export default function FeatureCard({ icon, title, text }) {
  return (
    <div className="feature-card">
      <div className="icon">{icon}</div>

      <div>
        <h3>{title}</h3>
        <p>{text}</p>
      </div>
    </div>
  );
}