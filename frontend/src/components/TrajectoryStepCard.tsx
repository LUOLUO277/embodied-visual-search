import type { TrajectoryItem } from "../api/client";
import {
  getActionArgumentLabel,
  getActionLabel,
  getConfidenceLabel,
  getFeedbackLabel,
  getMemoryUpdate,
  getStepImageSource,
  getStepStatus,
  getStepSummary,
  getThoughtSections,
} from "../utils/agentPresentation";

type Props = {
  item: TrajectoryItem;
};

function renderMemoryRow(label: string, value: string | null | undefined) {
  if (!value) {
    return null;
  }
  return (
    <div className="memory-row">
      <span>{label}</span>
      <p>{value}</p>
    </div>
  );
}

export function TrajectoryStepCard({ item }: Props) {
  const status = getStepStatus(item);
  const memory = getMemoryUpdate(item);
  const thoughtSections = getThoughtSections(item.thought).filter((section) => section.value);
  const imageSource = getStepImageSource(item);
  const confidence = getConfidenceLabel(item.action);

  return (
    <article className="timeline-card">
      <div className="timeline-card-header">
        <div className="timeline-card-meta">
          <span className="timeline-step">Step {item.step}</span>
          <h2>{getActionLabel(item.action, item.action_result.action_name)}</h2>
        </div>
        <div className="timeline-card-badges">
          <span className={`status-badge tone-${status.tone}`}>{status.label}</span>
          {confidence ? <span className="neutral-badge">置信度 {confidence}</span> : null}
        </div>
      </div>

      <div className="timeline-card-body">
        {imageSource ? <img className="timeline-preview" src={imageSource} alt={`Step ${item.step} preview`} /> : null}
        <div className="timeline-main-info">
          <div className="timeline-summary">
            <span className="section-kicker">决策摘要</span>
            <p>{getStepSummary(item)}</p>
          </div>
          <div className="timeline-info-grid">
            <div>
              <span>动作</span>
              <strong>{getActionLabel(item.action, item.action_result.action_name)}</strong>
            </div>
            <div>
              <span>目标</span>
              <strong>{getActionArgumentLabel(item.action)}</strong>
            </div>
            <div>
              <span>反馈</span>
              <strong>{getFeedbackLabel(item)}</strong>
            </div>
            <div>
              <span>当前假设</span>
              <strong>{memory.current_hypothesis ?? "-"}</strong>
            </div>
            <div>
              <span>正向线索</span>
              <strong>{memory.positive_clue ?? "-"}</strong>
            </div>
            <div>
              <span>负向发现</span>
              <strong>{memory.negative_finding ?? "-"}</strong>
            </div>
          </div>
        </div>
      </div>

      {thoughtSections.length > 0 ? (
        <details className="detail-accordion">
          <summary>详细思考</summary>
          <div className="detail-stack detail-stack-tight">
            {thoughtSections.map((section) => (
              <div key={section.key} className="detail-card">
                <h3>{section.label}</h3>
                <p>{section.value}</p>
              </div>
            ))}
          </div>
        </details>
      ) : null}

      <details className="detail-accordion">
        <summary>记忆更新</summary>
        <div className="memory-stack">
          {renderMemoryRow("Observed", memory.observed_area)}
          {renderMemoryRow("Searched", memory.searched_area)}
          {renderMemoryRow("Negative", memory.negative_finding)}
          {renderMemoryRow("Positive", memory.positive_clue)}
          {renderMemoryRow("Hypothesis", memory.current_hypothesis)}
          {renderMemoryRow("Summary", memory.summary)}
          {!memory.observed_area && !memory.searched_area && !memory.negative_finding && !memory.positive_clue && !memory.current_hypothesis && !memory.summary ? (
            <p className="muted">暂无记忆更新。</p>
          ) : null}
        </div>
      </details>
    </article>
  );
}
