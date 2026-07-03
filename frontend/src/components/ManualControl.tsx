import { useEffect, useMemo, useState } from "react";
import type { ManualActionMetadata, Observation, VisibleObject } from "../api/client";
import { getInventoryLabel } from "../utils/agentPresentation";

type Props = {
  disabled: boolean;
  observation: Observation | null;
  actions: ManualActionMetadata[];
  onAction: (action: string) => Promise<void>;
};

type TargetOption = {
  value: string;
  label: string;
};

function buildTargetOptions(visibleObjects: VisibleObject[]): TargetOption[] {
  const seen = new Set<string>();
  return visibleObjects
    .filter((item) => item.visible)
    .filter((item) => {
      if (seen.has(item.objectId)) {
        return false;
      }
      seen.add(item.objectId);
      return true;
    })
    .map((item) => ({
      value: item.objectId,
      label: `${item.objectType}${item.distance != null ? ` · ${item.distance.toFixed(2)}m` : ""}`,
    }));
}

export function ManualControl({ disabled, observation, actions, onAction }: Props) {
  const [selectedAction, setSelectedAction] = useState("");
  const [selectedTarget, setSelectedTarget] = useState("");

  useEffect(() => {
    if (!selectedAction && actions[0]) {
      setSelectedAction(actions[0].name);
    }
  }, [actions, selectedAction]);

  const selectedMetadata = useMemo(
    () => actions.find((item) => item.name === selectedAction) ?? actions[0] ?? null,
    [actions, selectedAction],
  );
  const targetOptions = useMemo(
    () => buildTargetOptions(observation?.metadata.visible_objects ?? []),
    [observation?.metadata.visible_objects],
  );
  const requiresTarget = Boolean(selectedMetadata?.requires_target);
  const targetDisabled = !requiresTarget || disabled;
  const executeDisabled =
    disabled ||
    !selectedMetadata ||
    (requiresTarget && (!selectedTarget || targetOptions.length === 0));

  return (
    <section className="panel side-panel manual-card">
      <div className="panel-title-row">
        <h2>手动动作</h2>
        <span className="mini-muted">手中：{getInventoryLabel(observation?.metadata.inventory_objects)}</span>
      </div>
      <div className="manual-control-row">
        <label>
          动作命令
          <select value={selectedMetadata?.name ?? ""} onChange={(event) => setSelectedAction(event.target.value)} disabled={disabled}>
            {actions.map((action) => (
              <option key={action.name} value={action.name}>
                {action.display_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          目标对象
          <select
            value={selectedTarget}
            onChange={(event) => setSelectedTarget(event.target.value)}
            disabled={targetDisabled}
          >
            {requiresTarget ? (
              <>
                <option value="">请选择目标</option>
                {targetOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </>
            ) : (
              <option value="">无需目标</option>
            )}
          </select>
        </label>
        <button onClick={() => void onAction(selectedMetadata?.name ?? "")} disabled={executeDisabled}>
          执行
        </button>
      </div>
      {requiresTarget && targetOptions.length === 0 ? <div className="mini-muted">当前视野中没有可用目标对象。</div> : null}
    </section>
  );
}
