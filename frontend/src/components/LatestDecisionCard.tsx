import type { AgentState, AgentStepResponse, TrajectoryItem } from "../api/client";
import {
  getActionArgumentLabel,
  getActionLabel,
  getConfidenceLabel,
  getFeedbackLabel,
  getMemoryUpdate,
  getSearchMemory,
  getStepStatus,
  getStepSummary,
  getThoughtPhase,
  getThoughtSections,
} from "../utils/agentPresentation";

type Props = {
  latestStep: AgentStepResponse | TrajectoryItem | null;
  agentState: AgentState | null;
  onOpenTrajectory: () => void;
};

function renderField(label: string, value: string | null | undefined) {
  if (!value) {
    return null;
  }
  return (
    <div className="decision-field">
      <span className="decision-field-label">{label}</span>
      <p>{value}</p>
    </div>
  );
}

function renderMemoryList(label: string, values: string[]) {
  if (values.length === 0) {
    return null;
  }
  return (
    <div className="decision-field">
      <span className="decision-field-label">{label}</span>
      <p>{values.join("; ")}</p>
    </div>
  );
}

export function LatestDecisionCard({ latestStep, agentState, onOpenTrajectory }: Props) {
  const status = getStepStatus(latestStep, agentState);
  const memory = getMemoryUpdate(latestStep);
  const searchMemory = getSearchMemory(latestStep, agentState);
  const confidence = getConfidenceLabel(latestStep?.action);
  const thoughtSections = getThoughtSections(latestStep?.thought).filter((item) => item.value);
  const phase = getThoughtPhase(latestStep?.thought);
  const currentStep = latestStep?.step ?? agentState?.current_step ?? 0;
  const maxSteps = agentState?.max_steps ?? 20;

  return (
    <section className="panel side-panel latest-decision-card">
      <div className="panel-title-row">
        <h2>思考与决策</h2>
        <button className="ghost-button" type="button" onClick={onOpenTrajectory}>
          回顾轨迹
        </button>
      </div>

      <div className="decision-status-row">
        <span className={`status-badge tone-${status.tone}`}>{status.label}</span>
        <span className="neutral-badge">Step {currentStep} / {maxSteps}</span>
        <span className="neutral-badge">{getActionLabel(latestStep?.action, latestStep?.action_result.action_name)}</span>
        <span className="phase-badge">{phase}</span>
        {confidence ? <span className="neutral-badge">置信度 {confidence}</span> : null}
      </div>

      <div className="decision-summary-card">
        <span className="section-kicker">核心摘要</span>
        <p>{getStepSummary(latestStep)}</p>
      </div>

      <div className="decision-grid">
        <div className="decision-block">
          <span className="section-kicker">当前决策</span>
          <div className="decision-list">
            <div><span>动作</span><strong>{getActionLabel(latestStep?.action, latestStep?.action_result.action_name)}</strong></div>
            <div><span>目标</span><strong>{getActionArgumentLabel(latestStep?.action)}</strong></div>
            <div><span>重复</span><strong>{latestStep?.action?.repetitions ?? 1}</strong></div>
            <div><span>结果</span><strong>{getStepStatus(latestStep).label}</strong></div>
          </div>
        </div>
        <div className="decision-block">
          <span className="section-kicker">Thought</span>
          {thoughtSections.length > 0 ? (
            <div className="detail-stack detail-stack-tight no-pad-stack">
              {thoughtSections.map((section) => (
                <div key={section.key} className="decision-field">
                  <span className="decision-field-label">{section.label}</span>
                  <p>{section.value}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">暂无 thought 内容。</p>
          )}
        </div>
      </div>

      <details className="detail-accordion" open>
        <summary>记忆更新</summary>
        <div className="memory-stack">
          {renderField("Checked", memory.checked)}
          {renderField("Ruled Out", memory.ruled_out)}
          {renderField("Clue", memory.clue)}
          {renderField("Avoid", memory.avoid)}
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

      <div className="decision-feedback muted">反馈：{getFeedbackLabel(latestStep)}</div>
    </section>
  );
}
