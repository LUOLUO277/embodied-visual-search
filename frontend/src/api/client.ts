export type ScenePayload = {
  room_types: string[];
  scenes_by_room: Record<string, string[]>;
  all_scenes: string[];
};

export type VisibleObject = {
  objectId: string;
  objectType: string;
  name: string;
  visible: boolean;
  distance?: number | null;
  pickupable: boolean;
  receptacle: boolean;
  openable: boolean;
  isOpen?: boolean | null;
  toggleable: boolean;
  isToggled?: boolean | null;
  parentReceptacles: string[];
};

export type RoomObjectInfo = {
  object_id: string;
  object_type: string;
  name: string;
  distance?: number | null;
  position?: Record<string, number> | null;
  attributes: Record<string, string | number | boolean | null>;
};

export type RoomViewHit = {
  hit: boolean;
  pixel_x: number;
  pixel_y: number;
  normalized_x: number;
  normalized_y: number;
  object?: RoomObjectInfo | null;
  message: string;
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
    visible_objects: VisibleObject[];
    last_action: string;
    last_action_success: boolean;
    error_message: string;
    inventory_objects: string[];
    task?: string | null;
    room_camera?: {
      position: Record<string, number>;
      rotation: Record<string, number>;
      target: Record<string, number>;
      field_of_view: number;
      distance: number;
      yaw: number;
      pitch: number;
    } | null;
  };
};

export type AgentThought = {
  situation_analysis: string;
  spatial_reasoning: string;
  task_planning: string;
  self_reflection: string;
  verification: string;
};

export type HighLevelAction = {
  name: "observe" | "move forward" | "navigate to" | "pickup" | "put in" | "toggle" | "open" | "close" | "end";
  argument?: string | null;
  confidence?: number | null;
  raw_text?: string | null;
  raw_json?: Record<string, unknown> | null;
};

export type LegalInteraction = {
  action: string;
  object: string;
  objectType: string;
  objectId: string;
};

export type AgentActionResult = {
  success: boolean;
  action_name: string;
  argument?: string | null;
  normalized_action: string;
  selected_object_id?: string | null;
  selected_object_type?: string | null;
  message: string;
  error_type?: string | null;
  error?: string | null;
  executed: boolean;
  done: boolean;
  adapted_action?: Record<string, unknown> | null;
  image_paths: string[];
  frame_available: boolean;
  legal_navigations: string[];
  legal_interactions: LegalInteraction[];
  metadata_summary: Record<string, unknown>;
};

export type TrajectoryItem = {
  step: number;
  scene: string;
  task: string;
  thought: AgentThought;
  action: HighLevelAction;
  action_result: AgentActionResult;
  raw_model_output: string;
  visible_objects: VisibleObject[];
  seen_object_ids: string[];
  holding_objects: string[];
  agent_pose: Record<string, unknown>;
  robot_view: string;
  last_action_feedback: Record<string, unknown>;
};

export type AgentStepResponse = {
  step: number;
  thought: AgentThought;
  action: HighLevelAction;
  raw_model_output: string;
  action_result: AgentActionResult;
  robot_view: string | null;
  trajectory: TrajectoryItem[];
};

export type AgentState = {
  active: boolean;
  running: boolean;
  stopped: boolean;
  done: boolean;
  scene: string;
  task_instruction: string;
  target_object?: string | null;
  max_steps: number;
  current_step: number;
  last_error: string;
  last_step?: AgentStepResponse | null;
};

export type ModelSettings = {
  base_url: string;
  api_key?: string;
  model: string;
  temperature: number;
  max_tokens: number;
  timeout: number;
  vision_enabled: boolean;
};

export type ModelSettingsResponse = {
  base_url: string;
  api_key_set: boolean;
  api_key_masked: string;
  model: string;
  temperature: number;
  max_tokens: number;
  timeout: number;
  vision_enabled: boolean;
};

export type ModelTestResponse = {
  success: boolean;
  message: string;
  raw_response?: string | null;
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
  getTrajectory: () => request<{ items: TrajectoryItem[] }>("/api/trajectory"),
  getAgentState: () => request<AgentState>("/api/agent/state"),
  resetAgent: (taskInstruction: string, maxSteps: number) =>
    request<AgentState>("/api/agent/reset", {
      method: "POST",
      body: JSON.stringify({ task_instruction: taskInstruction, target_object: null, max_steps: maxSteps }),
    }),
  stepAgent: (execute = true) =>
    request<AgentStepResponse>("/api/agent/step", {
      method: "POST",
      body: JSON.stringify({ execute }),
    }),
  runAgent: (execute = true) =>
    request<AgentStepResponse[]>("/api/agent/run", {
      method: "POST",
      body: JSON.stringify({ execute }),
    }),
  stopAgent: () =>
    request<AgentState>("/api/agent/stop", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  getModelSettings: () => request<ModelSettingsResponse>("/api/settings/model"),
  saveModelSettings: (settings: ModelSettings) =>
    request<ModelSettingsResponse>("/api/settings/model", {
      method: "POST",
      body: JSON.stringify(settings),
    }),
  testModelSettings: (settings?: ModelSettings) =>
    request<ModelTestResponse>("/api/settings/model/test", {
      method: "POST",
      body: JSON.stringify(settings ?? {}),
    }),
  orbitRoomView: (deltaYaw: number, deltaPitch: number) =>
    request<Observation>("/api/camera/room/orbit", {
      method: "POST",
      body: JSON.stringify({ delta_yaw: deltaYaw, delta_pitch: deltaPitch }),
    }),
  inspectRoomView: (x: number, y: number) =>
    request<RoomViewHit>("/api/camera/room/inspect", {
      method: "POST",
      body: JSON.stringify({ x, y }),
    }),
};
