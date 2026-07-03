import type { AgentState, AgentStepResponse, AgentThought, HighLevelAction, TrajectoryItem } from "../api/client";

type MemoryUpdate = {
  observed_area?: string | null;
  searched_area?: string | null;
  negative_finding?: string | null;
  positive_clue?: string | null;
  current_hypothesis?: string | null;
  summary?: string | null;
};

type StepLike = AgentStepResponse | TrajectoryItem;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asText(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function parseRawJson(step: StepLike): Record<string, unknown> | null {
  const rawJson = step.action?.raw_json;
  if (isRecord(rawJson)) {
    return rawJson;
  }

  const rawOutput = step.raw_model_output?.trim();
  if (!rawOutput) {
    return null;
  }

  const directCandidate = rawOutput.startsWith("```")
    ? rawOutput.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/```$/, "").trim()
    : rawOutput;

  try {
    const parsed = JSON.parse(directCandidate);
    return isRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function getMemoryUpdate(step: StepLike | null | undefined): MemoryUpdate {
  if (!step) {
    return {};
  }
  const rawJson = parseRawJson(step);
  const memoryUpdate = isRecord(rawJson?.memory_update) ? rawJson.memory_update : {};
  return {
    observed_area: asText(memoryUpdate.observed_area),
    searched_area: asText(memoryUpdate.searched_area),
    negative_finding: asText(memoryUpdate.negative_finding),
    positive_clue: asText(memoryUpdate.positive_clue),
    current_hypothesis: asText(memoryUpdate.current_hypothesis),
    summary: asText(memoryUpdate.summary),
  };
}

export function getThoughtSections(thought: AgentThought | null | undefined): Array<{ key: keyof AgentThought; label: string; value: string | null }> {
  return [
    { key: "situation_analysis", label: "Situation", value: asText(thought?.situation_analysis) },
    { key: "spatial_reasoning", label: "Spatial", value: asText(thought?.spatial_reasoning) },
    { key: "task_planning", label: "Plan", value: asText(thought?.task_planning) },
    { key: "self_reflection", label: "Reflection", value: asText(thought?.self_reflection) },
    { key: "verification", label: "Verification", value: asText(thought?.verification) },
  ];
}

export function getActionName(action: HighLevelAction | null | undefined): string {
  const name = asText(action?.name);
  return name ?? "-";
}

export function getActionArgumentLabel(action: HighLevelAction | null | undefined): string {
  return asText(action?.argument) ?? "无目标";
}

export function getActionRepetitions(action: HighLevelAction | null | undefined): number {
  return action?.repetitions && action.repetitions > 0 ? action.repetitions : 1;
}

export function getActionLabel(action: HighLevelAction | null | undefined, fallbackActionName?: string | null): string {
  const primaryName = asText(action?.name);
  const manualName = primaryName === "observe" ? asText(action?.argument) : null;
  const name = manualName ?? primaryName ?? fallbackActionName ?? "-";
  const repetitions = getActionRepetitions(action);
  return repetitions > 1 ? `${name} x${repetitions}` : name;
}

export function getStepStatus(step: StepLike | null | undefined, agentState?: AgentState | null): { label: string; tone: "success" | "warning" | "neutral" | "running" } {
  if (!step) {
    if (agentState?.running) {
      return { label: "运行中", tone: "running" };
    }
    if (agentState?.stopped) {
      return { label: "已停止", tone: "warning" };
    }
    if (agentState?.done) {
      return { label: "已完成", tone: "success" };
    }
    return { label: "待开始", tone: "neutral" };
  }

  const actionName = getActionName(step.action).toLowerCase();
  if (actionName === "done" || actionName === "end" || step.action_result.done) {
    return { label: "任务完成", tone: "success" };
  }
  if (step.action_result.success) {
    return { label: "success", tone: "success" };
  }
  const message = `${step.action_result.error || ""} ${step.action_result.message || ""}`.toLowerCase();
  if (message.includes("block")) {
    return { label: "blocked", tone: "warning" };
  }
  return { label: "failed", tone: "warning" };
}

export function getStepSummary(step: StepLike | null | undefined): string {
  if (!step) {
    return "模型尚未开始决策。";
  }

  const memory = getMemoryUpdate(step);
  if (memory.summary) {
    return memory.summary;
  }

  const situation = asText(step.thought?.situation_analysis);
  if (situation) {
    return situation;
  }

  return `执行动作：${getActionLabel(step.action, step.action_result.action_name)}`;
}

export function getFeedbackLabel(step: StepLike | null | undefined): string {
  if (!step) {
    return "-";
  }
  return asText(step.action_result.error) ?? asText(step.action_result.message) ?? "-";
}

export function getConfidenceLabel(action: HighLevelAction | null | undefined): string | null {
  return typeof action?.confidence === "number" ? action.confidence.toFixed(2) : null;
}

export function getInventoryLabel(holdingObjects: string[] | null | undefined): string {
  if (!holdingObjects || holdingObjects.length === 0) {
    return "空";
  }
  const [first] = holdingObjects;
  return first.split("|")[0] || first;
}

export function getStepImageSource(step: TrajectoryItem): string | null {
  if (step.robot_view) {
    return `data:image/png;base64,${step.robot_view}`;
  }

  const imagePath = step.action_result.image_paths[0];
  if (!imagePath) {
    return null;
  }

  const normalized = imagePath.replace(/\\/g, "/");
  return normalized.match(/^[A-Za-z]:\//) ? `file:///${normalized}` : normalized;
}
