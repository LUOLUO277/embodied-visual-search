import type { TrajectoryItem } from "../api/client";
import {
  getActionArgumentLabel,
  getActionLabel,
  getConfidenceLabel,
  getFeedbackLabel,
  getMemoryUpdate,
  getSearchMemory,
  getStepImageSource,
  getStepStatus,
  getStepSummary,
  getThoughtPhase,
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

function renderMemoryList(label: string, values: string[]) {
  if (values.length === 0) {
    return null;
  }
  return (
    <div className="memory-row">
      <span>{label}</span>
      <p>{values.join("; ")}</p>
    </div>
  );
}

export function TrajectoryStepCard({ item }: Props) {
  const status = getStepStatus(item);
  const memory = getMemoryUpdate(item);
  const searchMemory = getSearchMemory(item, null);
  const imageSource = getStepImageSource(item);
  const confidence = getConfidenceLabel(item.action);
  const phase = getThoughtPhase(item.thought);
  const thoughtSections = getThoughtSections(item.thought).filter((section) => section.value);

  return (
    <article className="timeline-card">
      <div className="timeline-card-header">
        <div className="timeline-card-meta">
          <span className="timeline-step">Step {item.step}</span>
          <h2>{getActionLabel(item.action, item.action_result.action_name)}</h2>
        </div>
        <div className="timeline-card-badges">
          <span className={`status-badge tone-${status.tone}`}>{status.label}</span>
          <span className="phase-badge">{phase}</span>
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
              <span>Phase</span>
              <strong>{phase}</strong>
            </div>
          </div>
        </div>
      </div>

      {thoughtSections.length > 0 ? (
        <details className="detail-accordion" open>
          <summary>Thought</summary>
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
          {renderMemoryRow("Checked", memory.checked)}
          {renderMemoryRow("Ruled Out", memory.ruled_out)}
          {renderMemoryRow("Clue", memory.clue)}
          {renderMemoryRow("Avoid", memory.avoid)}
          {!memory.checked && !memory.ruled_out && !memory.clue && !memory.avoid ? <p className="muted">暂无记忆更新。</p> : null}
        </div>
      </details>

      <details className="detail-accordion">
        <summary>Search Memory</summary>
        <div className="memory-stack">
          {searchMemory ? (
            <>
              <div className="decision-field">
                <span className="decision-field-label">Summary</span>
                <p>{searchMemory.summary}</p>
              </div>
              {renderMemoryList("Checked", searchMemory.checked)}
              {renderMemoryList("Ruled Out", searchMemory.ruled_out)}
              {renderMemoryList("Avoid", searchMemory.avoid)}
              {renderMemoryList("Recent Clues", searchMemory.recent_clues)}
            </>
          ) : (
            <p className="muted">暂无 search memory。</p>
          )}
        </div>
      </details>
    </article>
  );
}
