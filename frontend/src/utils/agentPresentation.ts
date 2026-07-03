import type {
  AgentState,
  AgentStepResponse,
  AgentThought,
  HighLevelAction,
  MemoryUpdate,
  SearchMemorySnapshot,
  TrajectoryItem,
} from "../api/client";

type StepLike = AgentStepResponse | TrajectoryItem;

type ThoughtSection = {
  key: string;
  label: string;
  value: string | null;
};

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

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
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
  const direct = isRecord(step.memory_update) ? step.memory_update : null;
  const rawJson = parseRawJson(step);
  const rawMemoryUpdate = isRecord(rawJson?.memory_update) ? rawJson.memory_update : {};
  return {
    checked: asText(direct?.checked) ?? asText(rawMemoryUpdate.checked) ?? asText(rawMemoryUpdate.searched_area) ?? asText(rawMemoryUpdate.observed_area) ?? asText(rawMemoryUpdate.negative_finding),
    ruled_out: asText(direct?.ruled_out) ?? asText(rawMemoryUpdate.ruled_out) ?? asText(rawMemoryUpdate.negative_finding),
    clue: asText(direct?.clue) ?? asText(rawMemoryUpdate.clue) ?? asText(rawMemoryUpdate.positive_clue) ?? asText(rawMemoryUpdate.current_hypothesis),
    avoid: asText(direct?.avoid) ?? asText(rawMemoryUpdate.avoid) ?? asText(rawMemoryUpdate.negative_finding),
  };
}

export function getThoughtPhase(thought: AgentThought | null | undefined): string {
  const phase = asText(thought?.phase);
  if (phase) {
    return phase;
  }
  const modes = Array.isArray(thought?.modes) ? thought.modes : [];
  if (modes.includes("self_reflection")) {
    return "recovery";
  }
  return "visual_search";
}

export function getThoughtSituation(thought: AgentThought | null | undefined): string {
  return (
    asText(thought?.situation_analysis)
    ?? asText(thought?.brief)
    ?? asText(thought?.situation_analysis)
    ?? ""
  );
}

export function getThoughtDecision(thought: AgentThought | null | undefined): string {
  return asText(thought?.decision) ?? asText(thought?.brief) ?? asText(thought?.task_planning) ?? "";
}

export function getThoughtVerification(thought: AgentThought | null | undefined): string | null {
  return asText(thought?.verification);
}

export function getThoughtSections(thought: AgentThought | null | undefined): ThoughtSection[] {
  return [
    { key: "situation_analysis", label: "Situation Analysis", value: getThoughtSituation(thought) || null },
    { key: "spatial_reasoning", label: "Spatial Reasoning", value: asText(thought?.spatial_reasoning) },
    { key: "memory_reasoning", label: "Memory Reasoning", value: asText(thought?.memory_reasoning) ?? (getThoughtPhase(thought) === "recovery" ? asText(thought?.self_reflection) : null) },
    { key: "verification", label: "Verification", value: getThoughtVerification(thought) },
    { key: "decision", label: "Decision", value: getThoughtDecision(thought) || null },
  ];
}

export function getSearchMemory(step: StepLike | null | undefined, agentState?: AgentState | null): SearchMemorySnapshot | null {
  const candidate = step?.search_memory ?? agentState?.search_memory;
  if (!candidate) {
    return null;
  }
  return {
    summary: asText(candidate.summary) ?? "Search has not started yet.",
    checked: asStringArray(candidate.checked),
    ruled_out: asStringArray(candidate.ruled_out),
    avoid: asStringArray(candidate.avoid),
    recent_clues: asStringArray(candidate.recent_clues),
  };
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

  const decision = getThoughtDecision(step.thought);
  if (decision) {
    return decision;
  }

  const situation = getThoughtSituation(step.thought);
  if (situation) {
    return situation;
  }

  const memory = getMemoryUpdate(step);
  if (memory.clue) {
    return memory.clue;
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
