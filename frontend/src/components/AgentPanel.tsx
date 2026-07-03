type Props = {
  taskInstruction: string;
  maxSteps: number;
  disabled: boolean;
  running: boolean;
  currentStep: number;
  onTaskInstructionChange: (value: string) => void;
  onMaxStepsChange: (value: number) => void;
  onToggleRun: () => void;
};

export function AgentPanel({
  taskInstruction,
  maxSteps,
  disabled,
  running,
  currentStep,
  onTaskInstructionChange,
  onMaxStepsChange,
  onToggleRun,
}: Props) {
  return (
    <section className="panel side-panel">
      <div className="panel-title-row">
        <h2>指令</h2>
      </div>
      <label>
        指令输入
        <textarea
          className="command-textarea"
          value={taskInstruction}
          onChange={(event) => onTaskInstructionChange(event.target.value)}
          placeholder="寻找房间里纸箱子并拿起来"
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
