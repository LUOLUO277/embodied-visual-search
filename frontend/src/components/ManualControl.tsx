const ACTIONS = [
  "MoveAhead",
  "MoveBack",
  "MoveLeft",
  "MoveRight",
  "RotateLeft",
  "RotateRight",
  "LookUp",
  "LookDown",
  "Done",
];

type Props = {
  disabled: boolean;
  onAction: (action: string) => void;
};

export function ManualControl({ disabled, onAction }: Props) {
  return (
    <section className="panel side-panel">
      <div className="panel-title-row">
        <h2>手动动作</h2>
      </div>
      <div className="action-grid compact-action-grid">
        {ACTIONS.map((action) => (
          <button key={action} disabled={disabled} onClick={() => onAction(action)}>
            {action}
          </button>
        ))}
      </div>
    </section>
  );
}
