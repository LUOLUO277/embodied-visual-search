import type { AgentState, AgentStepResponse } from "../api/client";

type Props = {
  taskInstruction: string;
  maxSteps: number;
  disabled: boolean;
  agentState: AgentState | null;
  latestStep: AgentStepResponse | null;
  onTaskInstructionChange: (value: string) => void;
  onMaxStepsChange: (value: number) => void;
  onStart: () => void;
  onReset: () => void;
  onStep: () => void;
  onStop: () => void;
};

export function AgentPanel({
  taskInstruction,
  maxSteps,
  disabled,
  agentState,
  latestStep,
  onTaskInstructionChange,
  onMaxStepsChange,
  onStart,
  onReset,
  onStep,
  onStop,
}: Props) {
  const failed = latestStep ? !latestStep.action_result.success : false;

  return (
    <section className="panel side-panel">
      <div className="panel-title-row">
        <h2>思考与任务指令</h2>
      </div>
      <label>
        指令
        <div className="inline-command-row">
          <input value={taskInstruction} onChange={(event) => onTaskInstructionChange(event.target.value)} placeholder="寻找房间里纸箱子并拿起来" />
          <button className="primary-cta" disabled={disabled} onClick={onStart}>开始</button>
        </div>
      </label>
      <label>
        最大步数
        <input type="number" min={1} max={200} value={maxSteps} onChange={(event) => onMaxStepsChange(Number(event.target.value))} />
      </label>
      <div className="button-row triple-row">
        <button disabled={disabled} onClick={onReset}>重置</button>
        <button disabled={disabled || !agentState?.active} onClick={onStep}>单步</button>
        <button disabled={!agentState?.running && !agentState?.active} onClick={onStop}>停止</button>
      </div>
      <div className="agent-status-box">
        <div>当前步数：{agentState?.current_step ?? 0}</div>
        <div>完成状态：{String(agentState?.done ?? false)}</div>
        <div>最近错误：{agentState?.last_error || "-"}</div>
      </div>
      {latestStep ? (
        <div className="thought-box compact-thought-box">
          <strong>最近决策</strong>
          <div>动作：{latestStep.action.name}{latestStep.action.argument ? ` ${latestStep.action.argument}` : ""}</div>
          <div>置信度：{latestStep.action.confidence ?? "-"}</div>
          <div>选择对象：{latestStep.action_result.selected_object_id || "-"}</div>
          <div>结果：{latestStep.action_result.success ? "success" : "failed"} {latestStep.action_result.message || ""}</div>
          {failed ? <div className="failure-text">反馈：{latestStep.action_result.error || latestStep.action_result.message}</div> : null}
          <div className="thought-summary">{latestStep.thought.situation_analysis || "暂无模型分析。"}</div>
          <details>
            <summary>展开完整思考</summary>
            <div>{latestStep.thought.spatial_reasoning}</div>
            <div>{latestStep.thought.task_planning}</div>
            <div>{latestStep.thought.self_reflection}</div>
            <div>{latestStep.thought.verification}</div>
          </details>
        </div>
      ) : (
        <div className="thought-box compact-thought-box">模型尚未开始决策。</div>
      )}
    </section>
  );
}
