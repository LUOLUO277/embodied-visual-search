import type { TrajectoryItem } from "../api/client";

type Props = {
  items: TrajectoryItem[];
};

export function TrajectoryPanel({ items }: Props) {
  return (
    <section className="panel">
      <h2>Trajectory History</h2>
      {items.length === 0 ? (
        <div className="empty">No trajectory yet</div>
      ) : (
        <div className="trajectory-list">
          {items.map((item) => (
            <article key={item.step} className="trajectory-item">
              <div className="trajectory-header">
                <strong>Step {item.step}</strong>
                <span>{item.action}</span>
                <span>{item.success ? "success" : "failed"}</span>
              </div>
              <div className="trajectory-body">
                <p>Scene: {item.scene}</p>
                <p>Task: {item.task || "None"}</p>
                <p>Thought: {item.thought}</p>
                <p>Error: {item.error_message || "-"}</p>
                <p>Visible Objects: {item.visible_objects.join(", ") || "-"}</p>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
