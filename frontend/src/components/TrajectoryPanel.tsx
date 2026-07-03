import type { TrajectoryItem } from "../api/client";

type Props = {
  items: TrajectoryItem[];
};

function renderImageSource(item: TrajectoryItem): string {
  const path = item.action_result.image_paths[0];
  if (path) {
    const normalized = path.replace(/\\/g, "/");
    return normalized.match(/^[A-Za-z]:\//) ? `file:///${normalized}` : normalized;
  }
  return `data:image/png;base64,${item.robot_view}`;
}

export function TrajectoryPanel({ items }: Props) {
  return (
    <section className="panel side-panel trajectory-side-panel">
      <div className="panel-title-row">
        <h2>轨迹</h2>
      </div>
      {items.length === 0 ? (
        <div className="empty">暂无轨迹</div>
      ) : (
        <div className="trajectory-list trajectory-visual-list compact-trajectory-list">
          {items.slice().reverse().map((item) => (
            <article key={item.step} className="trajectory-item trajectory-visual-item compact-trajectory-item">
              <img className="trajectory-preview" src={renderImageSource(item)} alt={`Step ${item.step} preview`} />
              <div className="trajectory-content">
                <div className="trajectory-header">
                  <strong>Step {item.step}</strong>
                  <span>{item.action.name}{item.action.argument ? ` ${item.action.argument}` : ""}</span>
                </div>
                <div className="trajectory-body compact-trajectory-body">
                  <p>结果：{item.action_result.success ? "success" : "failed"}</p>
                  <p>对象：{item.action_result.selected_object_id || "-"}</p>
                  <p>反馈：{item.action_result.error || item.action_result.message || "-"}</p>
                  <details>
                    <summary>展开详情</summary>
                    <p>Legal Navigations: {item.action_result.legal_navigations.join(", ") || "-"}</p>
                    <pre>{item.raw_model_output || "-"}</pre>
                  </details>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
