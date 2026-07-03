import type { TrajectoryItem } from "../api/client";
import { TrajectoryStepCard } from "./TrajectoryStepCard";

type Props = {
  items: TrajectoryItem[];
};

export function TrajectoryPanel({ items }: Props) {
  return (
    <section className="panel side-panel">
      <div className="panel-title-row">
        <h2>轨迹</h2>
      </div>
      {items.length === 0 ? (
        <div className="empty">暂无轨迹</div>
      ) : (
        <div className="timeline-list">
          {items.map((item) => (
            <TrajectoryStepCard key={item.step} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}
