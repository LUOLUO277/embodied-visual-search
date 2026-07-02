export type ScenePayload = {
  room_types: string[];
  scenes_by_room: Record<string, string[]>;
  all_scenes: string[];
};

export type Observation = {
  robot_view: string;
  room_view: string | null;
  metadata: {
    scene_name: string;
    agent_pose: {
      position: Record<string, number>;
      rotation: Record<string, number>;
      camera_horizon: number;
    };
    visible_objects: string[];
    last_action_success: boolean;
    error_message: string;
    task?: string | null;
  };
};

export type TrajectoryItem = {
  step: number;
  scene: string;
  task: string;
  thought: string;
  action: string;
  success: boolean;
  error_message: string;
  visible_objects: string[];
  agent_pose: Record<string, unknown>;
};

export type AgentStepResponse = {
  decision: {
    thought: string;
    action: string;
  };
  observation: Observation;
  trajectory: TrajectoryItem;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getScenes: () => request<ScenePayload>("/api/scenes"),
  loadScene: (scene: string, task: string) =>
    request<Observation>("/api/env/load", {
      method: "POST",
      body: JSON.stringify({ scene, task }),
    }),
  getObservation: () => request<Observation>("/api/env/observation"),
  doAction: (action: string, thought?: string) =>
    request<Observation>("/api/env/action", {
      method: "POST",
      body: JSON.stringify({ action, thought }),
    }),
  agentStep: (task: string) =>
    request<AgentStepResponse>("/api/agent/step", {
      method: "POST",
      body: JSON.stringify({ task }),
    }),
  getTrajectory: () => request<{ items: TrajectoryItem[] }>("/api/trajectory"),
};
