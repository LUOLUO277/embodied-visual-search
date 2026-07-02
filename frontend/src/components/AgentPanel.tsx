type Props = {
  task: string;
  thought: string;
  disabled: boolean;
  onStep: () => void;
};

export function AgentPanel({ task, thought, disabled, onStep }: Props) {
  return (
    <section className="panel">
      <h2>Agent Step</h2>
      <p className="muted">Current task: {task || "None"}</p>
      <button disabled={disabled} onClick={onStep}>
        Agent Step
      </button>
      <div className="thought-box">{thought || "DummyAgent has not stepped yet."}</div>
    </section>
  );
}
