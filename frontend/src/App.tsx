import { useEffect, useRef, useState } from "react";
import {
  api,
  type AgentState,
  type AgentStepResponse,
  type Observation,
  type RoomViewHit,
  type ScenePayload,
  type TrajectoryItem,
} from "./api/client";
import { AgentPanel } from "./components/AgentPanel";
import { ManualControl } from "./components/ManualControl";
import { ModelSettingsPanel } from "./components/ModelSettingsPanel";
import { RobotView } from "./components/RobotView";
import { RoomView } from "./components/RoomView";
import { ScenePanel } from "./components/ScenePanel";
import { TrajectoryPanel } from "./components/TrajectoryPanel";

const EMPTY_ROOM_HIT: RoomViewHit = {
  hit: false,
  pixel_x: 0,
  pixel_y: 0,
  normalized_x: 0,
  normalized_y: 0,
  object: null,
  message: "",
};

function App() {
  const [scenes, setScenes] = useState<ScenePayload | null>(null);
  const [roomType, setRoomType] = useState("Kitchen");
  const [scene, setScene] = useState("");
  const [task, setTask] = useState("Find the sofa");
  const [taskInstruction, setTaskInstruction] = useState("寻找房间里纸箱子并拿起来");
  const [maxSteps, setMaxSteps] = useState(30);
  const [observation, setObservation] = useState<Observation | null>(null);
  const [trajectory, setTrajectory] = useState<TrajectoryItem[]>([]);
  const [agentState, setAgentState] = useState<AgentState | null>(null);
  const [latestStep, setLatestStep] = useState<AgentStepResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const stopRequestedRef = useRef(false);

  useEffect(() => {
    void bootstrap();
  }, []);

  async function bootstrap() {
    try {
      const scenePayload = await api.getScenes();
      setScenes(scenePayload);
      const defaultRoom = scenePayload.room_types[0];
      const defaultScene = scenePayload.scenes_by_room[defaultRoom][0];
      setRoomType(defaultRoom);
      setScene(defaultScene);
      setTrajectory((await api.getTrajectory()).items);
      try {
        setAgentState(await api.getAgentState());
      } catch {
        setAgentState(null);
      }
    } catch (err) {
      setError(String(err));
    }
  }

  function syncObservation(nextObservation: Observation) {
    setObservation(nextObservation);
    setError(nextObservation.metadata.error_message || "");
  }

  async function refreshTrajectory() {
    setTrajectory((await api.getTrajectory()).items);
  }

  async function refreshAgentState() {
    const nextState = await api.getAgentState();
    setAgentState(nextState);
    return nextState;
  }

  async function handleLoad() {
    try {
      setLoading(true);
      const result = await api.loadScene(scene, task);
      syncObservation(result);
      setLatestStep(null);
      await refreshTrajectory();
      await refreshAgentState();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleAction(action: string) {
    try {
      setLoading(true);
      const result = await api.doAction(action);
      syncObservation(result);
      await refreshTrajectory();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleAgentReset() {
    stopRequestedRef.current = false;
    const result = await api.resetAgent(taskInstruction, maxSteps);
    setAgentState(result);
    setLatestStep(null);
    await refreshTrajectory();
    return result;
  }

  async function handleAgentStart() {
    try {
      setLoading(true);
      stopRequestedRef.current = false;
      let state = await handleAgentReset();

      while (!stopRequestedRef.current && state.active && !state.done && state.current_step < state.max_steps) {
        const stepResult = await api.stepAgent(true);
        setLatestStep(stepResult);
        setTrajectory(stepResult.trajectory);
        if (stepResult.robot_view) {
          const nextObservation = await api.getObservation();
          syncObservation(nextObservation);
        }
        state = await refreshAgentState();
        if (stepResult.action_result.error_type === "parse_error" && !stepResult.action_result.success) {
          break;
        }
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleAgentResetOnly() {
    try {
      setLoading(true);
      await handleAgentReset();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleAgentStep() {
    try {
      setLoading(true);
      const result = await api.stepAgent(true);
      setLatestStep(result);
      if (result.robot_view) {
        const nextObservation = await api.getObservation();
        syncObservation(nextObservation);
      }
      setTrajectory(result.trajectory);
      await refreshAgentState();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleAgentStop() {
    try {
      stopRequestedRef.current = true;
      setAgentState(await api.stopAgent());
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleRoomOrbit(deltaYaw: number, deltaPitch: number) {
    if (!observation) {
      return;
    }
    try {
      const result = await api.orbitRoomView(deltaYaw, deltaPitch);
      syncObservation(result);
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleRoomInspect(x: number, y: number): Promise<RoomViewHit> {
    if (!observation?.room_view) {
      return EMPTY_ROOM_HIT;
    }
    try {
      return await api.inspectRoomView(x, y);
    } catch (err) {
      setError(String(err));
      return EMPTY_ROOM_HIT;
    }
  }

  function handleRoomTypeChange(nextRoomType: string) {
    setRoomType(nextRoomType);
    const nextScene = scenes?.scenes_by_room[nextRoomType]?.[0] ?? "";
    setScene(nextScene);
  }

  return (
    <div className="app-shell dashboard-shell">
      <header className="topbar">
        <div className="brand-block">
          <h1>具身视觉搜索</h1>
          <p>AI2-THOR × Claude</p>
        </div>
        <div className="topbar-actions">
          <span className="top-chip">轨迹管理 {trajectory.length}</span>
          <span className={`top-chip ${loading || agentState?.running ? "busy-chip" : "success-chip"}`}>{loading || agentState?.running ? "运行中" : "空闲"}</span>
        </div>
      </header>

      <main className="dashboard-layout">
        <section className="dashboard-main">
          <RobotView
            image={observation?.robot_view ?? null}
            sceneName={observation?.metadata.scene_name || scene || "-"}
            stepLabel={`第 ${agentState?.current_step ?? 0} 步`}
          />
          <RoomView
            image={observation?.room_view ?? null}
            camera={observation?.metadata.room_camera ?? null}
            disabled={!observation || loading}
            onInspect={handleRoomInspect}
            onOrbit={handleRoomOrbit}
          />
        </section>

        <aside className="dashboard-sidebar">
          <ScenePanel
            scenes={scenes}
            roomType={roomType}
            scene={scene}
            task={task}
            loading={loading}
            onRoomTypeChange={handleRoomTypeChange}
            onSceneChange={setScene}
            onTaskChange={setTask}
            onLoad={handleLoad}
          />
          <ModelSettingsPanel onStatus={setError} />
          <AgentPanel
            taskInstruction={taskInstruction}
            maxSteps={maxSteps}
            disabled={loading || !observation}
            agentState={agentState}
            latestStep={latestStep}
            onTaskInstructionChange={setTaskInstruction}
            onMaxStepsChange={setMaxSteps}
            onStart={handleAgentStart}
            onReset={handleAgentResetOnly}
            onStep={handleAgentStep}
            onStop={handleAgentStop}
          />
          <ManualControl disabled={loading || !observation} onAction={handleAction} />
          <TrajectoryPanel items={trajectory} />
        </aside>
      </main>

      {error ? <div className="error-banner">{error}</div> : null}
    </div>
  );
}

export default App;
