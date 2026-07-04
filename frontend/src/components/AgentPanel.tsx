import type { SelectedTarget } from "../api/client";

type Props = {
  taskInstruction: string;
  maxSteps: number;
  disabled: boolean;
  running: boolean;
  currentStep: number;
  selectedTarget: SelectedTarget | null;
  targetPromptPreview: string | null;
  onTaskInstructionChange: (value: string) => void;
  onMaxStepsChange: (value: number) => void;
  onToggleRun: () => void;
  onClearTarget: () => void;
};

export function AgentPanel({
  taskInstruction,
  maxSteps,
  disabled,
  running,
  currentStep,
  selectedTarget,
  targetPromptPreview,
  onTaskInstructionChange,
  onMaxStepsChange,
  onToggleRun,
  onClearTarget,
}: Props) {
  return (
    <section className="panel side-panel">
      <div className="panel-title-row">
        <h2>指令</h2>
      </div>
      {selectedTarget ? (
        <div className="target-card">
          <div className="target-card-media">
            <img src={`data:image/png;base64,${selectedTarget.image}`} alt="Selected target snapshot" />
          </div>
          <div className="target-card-body">
            <strong>{selectedTarget.objectType || "已选择目标"}</strong>
            {targetPromptPreview ? <span className="mini-muted">{targetPromptPreview}</span> : null}
            <button className="ghost-button" type="button" onClick={onClearTarget} disabled={disabled || running}>
              清除目标
            </button>
          </div>
        </div>
      ) : null}
      <label>
        指令输入
        <textarea
          className="command-textarea"
          value={taskInstruction}
          onChange={(event) => onTaskInstructionChange(event.target.value)}
          placeholder={selectedTarget ? "例如：把这个物体拿起来 / 打开这个物体 / 找到它并移动过去" : "寻找房间里纸箱子并拿起来"}
          rows={3}
          disabled={disabled || running}
        />
      </label>
      <div className="agent-control-row">
        <label>
          最大步数
          <input
            type="number"
            min={1}
            max={200}
            value={maxSteps}
            onChange={(event) => onMaxStepsChange(Number(event.target.value))}
            disabled={disabled || running}
          />
        </label>
        <button className={`primary-cta ${running ? "danger-cta" : ""}`} disabled={disabled && !running} onClick={onToggleRun}>
          {running ? "停止" : "开始"}
        </button>
      </div>
      <div className="agent-status-inline muted">当前步数：Step {currentStep}</div>
    </section>
  );
}
