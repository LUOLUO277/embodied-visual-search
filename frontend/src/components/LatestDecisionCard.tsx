import type { AgentState, AgentStepResponse, TrajectoryItem } from "../api/client";
import {
  getActionArgumentLabel,
  getActionLabel,
  getConfidenceLabel,
  getFeedbackLabel,
  getMemoryUpdate,
  getStepStatus,
  getStepSummary,
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

export function LatestDecisionCard({ latestStep, agentState, onOpenTrajectory }: Props) {
  const status = getStepStatus(latestStep, agentState);
  const memory = getMemoryUpdate(latestStep);
  const confidence = getConfidenceLabel(latestStep?.action);
  const thoughtSections = getThoughtSections(latestStep?.thought).filter((item) => item.value);
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
          <span className="section-kicker">关键线索</span>
          {renderField("正向线索", memory.positive_clue)}
          {renderField("负向发现", memory.negative_finding)}
          {renderField("当前假设", memory.current_hypothesis)}
          {!memory.positive_clue && !memory.negative_finding && !memory.current_hypothesis ? <p className="muted">暂无关键线索。</p> : null}
        </div>
      </div>

      <div className="decision-feedback muted">反馈：{getFeedbackLabel(latestStep)}</div>

      {thoughtSections.length > 0 ? (
        <details className="detail-accordion">
          <summary>展开详细思考</summary>
          <div className="detail-stack">
            {thoughtSections.map((section) => (
              <div key={section.key} className="detail-card">
                <h3>{section.label}</h3>
                <p>{section.value}</p>
              </div>
            ))}
          </div>
        </details>
      ) : null}
    </section>
  );
}
