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
    <section className="panel">
      <h2>Manual Control</h2>
      <div className="action-grid">
        {ACTIONS.map((action) => (
          <button key={action} disabled={disabled} onClick={() => onAction(action)}>
            {action}
          </button>
        ))}
      </div>
    </section>
  );
}
