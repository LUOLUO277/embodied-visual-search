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

export type RoomHitCandidate = {
  object_id: string;
  score: number;
  reason: string;
};

export type RoomViewHit = {
  hit: boolean;
  pixel_x: number;
  pixel_y: number;
  normalized_x: number;
  normalized_y: number;
  object?: RoomObjectInfo | null;
  message: string;
  hit_reason: string;
  candidates: RoomHitCandidate[];
};

export type RoomObjectSelection = RoomViewHit & {
  room_view?: string | null;
  room_camera?: Observation["metadata"]["room_camera"] | null;
  target_snapshot?: string | null;
  target_snapshot_path?: string | null;
};

export type SelectedTarget = {
  image: string;
  objectType?: string | null;
  note?: string | null;
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
  phase?: string;
  situation_analysis?: string;
  spatial_reasoning?: string | null;
  memory_reasoning?: string | null;
  verification?: string | null;
  decision?: string;
  modes?: string[];
  brief?: string;
  task_planning?: string;
  self_reflection?: string;
};

export type MemoryUpdate = {
  checked?: string | null;
  ruled_out?: string | null;
  clue?: string | null;
  avoid?: string | null;
};

export type SearchMemorySnapshot = {
  summary: string;
  checked: string[];
  ruled_out: string[];
  avoid: string[];
  recent_clues: string[];
};

export type ObserveView = {
  label: "front" | "left" | "back" | "right" | string;
  relative_rotation: string;
  description?: string | null;
  image_base64?: string | null;
  image_path?: string | null;
};

export type HighLevelAction = {
  name?:
    | "observe"
    | "move forward"
    | "move back"
    | "move left"
    | "move right"
    | "rotate left"
    | "rotate right"
    | "look up"
    | "look down"
    | "navigate to"
    | "pickup"
    | "put in"
    | "toggle"
    | "open"
    | "close"
    | "end"
    | string;
  argument?: string | null;
  confidence?: number | null;
  repetitions?: number | null;
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
  observe_views?: ObserveView[];
  frame_available: boolean;
  legal_navigations: string[];
  legal_interactions: LegalInteraction[];
  metadata_summary: Record<string, unknown>;
};

export type TrajectoryItem = {
  step: number;
  scene: string;
  task: string;
  thought?: AgentThought;
  action?: HighLevelAction;
  action_result: AgentActionResult;
  raw_model_output: string;
  memory_update?: MemoryUpdate | null;
  search_memory?: SearchMemorySnapshot | null;
  visible_objects: VisibleObject[];
  seen_object_ids: string[];
  holding_objects: string[];
  agent_pose: Record<string, unknown>;
  robot_view: string;
  last_action_feedback: Record<string, unknown>;
};

export type AgentStepResponse = {
  step: number;
  thought?: AgentThought;
  action?: HighLevelAction;
  raw_model_output: string;
  memory_update?: MemoryUpdate | null;
  search_memory?: SearchMemorySnapshot | null;
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
  selected_target_image?: string | null;
  selected_target_type?: string | null;
  selected_target_note?: string | null;
  max_steps: number;
  current_step: number;
  last_error: string;
  last_step?: AgentStepResponse | null;
  search_memory?: SearchMemorySnapshot | null;
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

export type ManualActionMetadata = {
  name: string;
  display_name: string;
  requires_target: boolean;
  supports_repetitions: boolean;
};

export type ActionSpaceResponse = {
  actions: ManualActionMetadata[];
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
  getActionSpace: () => request<ActionSpaceResponse>("/api/agent/action-space"),
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
  resetAgent: (taskInstruction: string, maxSteps: number, selectedTarget?: SelectedTarget | null) =>
    request<AgentState>("/api/agent/reset", {
      method: "POST",
      body: JSON.stringify({
        task_instruction: taskInstruction,
        target_object: null,
        max_steps: maxSteps,
        target_reference_image: selectedTarget?.image ?? null,
        target_reference_type: null,
        target_reference_note:
          selectedTarget?.note ??
          (selectedTarget
            ? "The user selected this object from the room view. Use it only as a target reference image."
            : null),
      }),
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
  orbitRoomView: (deltaYaw: number, deltaPitch: number, deltaDistance = 0) =>
    request<Observation>("/api/camera/room/orbit", {
      method: "POST",
      body: JSON.stringify({ delta_yaw: deltaYaw, delta_pitch: deltaPitch, delta_distance: deltaDistance }),
    }),
  inspectRoomView: (x: number, y: number) =>
    request<RoomViewHit>("/api/camera/room/inspect", {
      method: "POST",
      body: JSON.stringify({ x, y }),
    }),
  selectRoomObject: (x: number, y: number) =>
    request<RoomObjectSelection>("/api/camera/room/select-object", {
      method: "POST",
      body: JSON.stringify({ x, y, focus: true, make_snapshot: true }),
    }),
};
