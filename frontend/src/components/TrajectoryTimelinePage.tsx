import type { TrajectoryItem } from "../api/client";
import { TrajectoryStepCard } from "./TrajectoryStepCard";

type Props = {
  items: TrajectoryItem[];
  onBack: () => void;
};

export function TrajectoryTimelinePage({ items, onBack }: Props) {
  return (
    <section className="trajectory-page">
      <div className="trajectory-page-header panel">
        <div>
          <span className="section-kicker">轨迹详情</span>
          <h1>Step 时间线</h1>
          <p className="muted">按执行顺序查看每一步的摘要、动作、反馈、线索和详细思考。</p>
        </div>
        <button className="ghost-button" type="button" onClick={onBack}>
          返回主页面
        </button>
      </div>
      {items.length === 0 ? (
        <div className="panel empty-state">暂无轨迹记录。</div>
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
