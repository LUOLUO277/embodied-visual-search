import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type AgentState,
  type AgentStepResponse,
  type ManualActionMetadata,
  type Observation,
  type RoomObjectSelection,
  type RoomViewHit,
  type ScenePayload,
  type SelectedTarget,
  type TrajectoryItem,
} from "./api/client";
import { AgentPanel } from "./components/AgentPanel";
import { LatestDecisionCard } from "./components/LatestDecisionCard";
import { ManualControl } from "./components/ManualControl";
import { ModelSettingsPanel } from "./components/ModelSettingsPanel";
import { RobotView } from "./components/RobotView";
import { RoomView } from "./components/RoomView";
import { ScenePanel } from "./components/ScenePanel";
import { TrajectoryTimelinePage } from "./components/TrajectoryTimelinePage";

const EMPTY_ROOM_HIT: RoomViewHit = {
  hit: false,
  pixel_x: 0,
  pixel_y: 0,
  normalized_x: 0,
  normalized_y: 0,
  object: null,
  message: "",
  hit_reason: "",
  candidates: [],
};

function buildTargetPromptPreview(taskInstruction: string, hasSelectedTarget: boolean): string | null {
  if (!hasSelectedTarget) {
    return null;
  }
  return `User instruction: ${taskInstruction}\nThe target object is shown in the attached target reference image. Find the matching object from the current first-person robot view and complete the instruction using visible object refs only.`;
}

function App() {
  const [scenes, setScenes] = useState<ScenePayload | null>(null);
  const [actionSpace, setActionSpace] = useState<ManualActionMetadata[]>([]);
  const [roomType, setRoomType] = useState("Kitchen");
  const [scene, setScene] = useState("");
  const [taskInstruction, setTaskInstruction] = useState("寻找房间里的纸箱子并拿起来");
  const [maxSteps, setMaxSteps] = useState(20);
  const [observation, setObservation] = useState<Observation | null>(null);
  const [trajectory, setTrajectory] = useState<TrajectoryItem[]>([]);
  const [agentState, setAgentState] = useState<AgentState | null>(null);
  const [latestStep, setLatestStep] = useState<AgentStepResponse | null>(null);
  const [selectedTarget, setSelectedTarget] = useState<SelectedTarget | null>(null);
  const [loading, setLoading] = useState(false);
  const [agentLoopRunning, setAgentLoopRunning] = useState(false);
  const [error, setError] = useState("");
  const [viewMode, setViewMode] = useState<"main" | "trajectory">("main");
  const stopRequestedRef = useRef(false);
  const runLoopActiveRef = useRef(false);

  useEffect(() => {
    void bootstrap();
  }, []);

  const isAgentRunning = agentLoopRunning || Boolean(agentState?.running);
  const sidebarDisabled = loading || isAgentRunning;
  const latestDecision = useMemo<AgentStepResponse | TrajectoryItem | null>(() => {
    if (latestStep) {
      return latestStep;
    }
    return trajectory[trajectory.length - 1] ?? agentState?.last_step ?? null;
  }, [agentState?.last_step, latestStep, trajectory]);
  const targetPromptPreview = useMemo(
    () => buildTargetPromptPreview(taskInstruction, Boolean(selectedTarget)),
    [selectedTarget, taskInstruction],
  );

  async function bootstrap() {
    try {
      const [scenePayload, actionSpacePayload, trajectoryPayload] = await Promise.all([
        api.getScenes(),
        api.getActionSpace(),
        api.getTrajectory(),
      ]);
      setScenes(scenePayload);
      setActionSpace(actionSpacePayload.actions);
      const defaultRoom = scenePayload.room_types[0];
      const defaultScene = scenePayload.scenes_by_room[defaultRoom][0];
      setRoomType(defaultRoom);
      setScene(defaultScene);
      setTrajectory(trajectoryPayload.items);
      try {
        const state = await api.getAgentState();
        setAgentState(state);
        if (state.selected_target_image) {
          setSelectedTarget({
            image: state.selected_target_image,
            objectType: state.selected_target_type,
            note: state.selected_target_note,
          });
        }
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
    if (nextState.selected_target_image) {
      setSelectedTarget({
        image: nextState.selected_target_image,
        objectType: nextState.selected_target_type,
        note: nextState.selected_target_note,
      });
    }
    return nextState;
  }

  async function handleLoad() {
    try {
      setLoading(true);
      const result = await api.loadScene(scene, taskInstruction);
      syncObservation(result);
      setSelectedTarget(null);
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
    if (!action) {
      return;
    }
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
    const result = await api.resetAgent(taskInstruction, maxSteps, selectedTarget);
    setAgentState(result);
    setLatestStep(null);
    await refreshTrajectory();
    return result;
  }

  async function handleAgentStart() {
    if (runLoopActiveRef.current || !observation) {
      return;
    }

    runLoopActiveRef.current = true;
    stopRequestedRef.current = false;
    setAgentLoopRunning(true);
    try {
      setLoading(true);
      let state = await handleAgentReset();
      setLoading(false);

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
      runLoopActiveRef.current = false;
      stopRequestedRef.current = false;
      setAgentLoopRunning(false);
      setLoading(false);
      try {
        await refreshAgentState();
      } catch {
        // Keep the last known state if the refresh fails.
      }
    }
  }

  async function handleAgentStop() {
    try {
      stopRequestedRef.current = true;
      const state = await api.stopAgent();
      setAgentState(state);
      setAgentLoopRunning(false);
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleToggleRun() {
    if (isAgentRunning) {
      await handleAgentStop();
      return;
    }
    await handleAgentStart();
  }

  async function handleRoomOrbit(deltaYaw: number, deltaPitch: number, deltaDistance = 0) {
    if (!observation) {
      return;
    }
    try {
      const result = await api.orbitRoomView(deltaYaw, deltaPitch, deltaDistance);
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

  async function handleRoomSelect(x: number, y: number): Promise<RoomObjectSelection> {
    if (!observation?.room_view) {
      return { ...EMPTY_ROOM_HIT, message: "Room view unavailable." };
    }
    try {
      const result = await api.selectRoomObject(x, y);
      if (result.room_view) {
        setObservation((current) => {
          if (!current) {
            return current;
          }
          return {
            ...current,
            room_view: result.room_view ?? current.room_view,
            metadata: {
              ...current.metadata,
              room_camera: result.room_camera ?? current.metadata.room_camera,
            },
          };
        });
      }
      if (result.hit && result.target_snapshot) {
        setSelectedTarget({
          image: result.target_snapshot,
          objectType: result.object?.object_type,
          note: "The user selected this object from the room view. Use it only as a visual target reference.",
        });
      }
      return result;
    } catch (err) {
      setError(String(err));
      return { ...EMPTY_ROOM_HIT, message: "未选中物体。" };
    }
  }

  function handleRoomTypeChange(nextRoomType: string) {
    setRoomType(nextRoomType);
    const nextScene = scenes?.scenes_by_room[nextRoomType]?.[0] ?? "";
    setScene(nextScene);
  }

  function handleClearTarget() {
    setSelectedTarget(null);
  }

  return (
    <div className="app-shell dashboard-shell">
      <header className="topbar">
        <div className="brand-block">
          <h1>具身视觉搜索</h1>
          <p>AI2-THOR</p>
        </div>
        <div className="topbar-actions">
          <span className="top-chip">轨迹 {trajectory.length}</span>
          <span className={`top-chip ${isAgentRunning ? "busy-chip" : "success-chip"}`}>{isAgentRunning ? "运行中" : "空闲"}</span>
        </div>
      </header>

      {viewMode === "trajectory" ? (
        <TrajectoryTimelinePage items={trajectory} onBack={() => setViewMode("main")} />
      ) : (
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
              disabled={!observation || sidebarDisabled}
              onInspect={handleRoomInspect}
              onOrbit={handleRoomOrbit}
              onSelect={handleRoomSelect}
            />
          </section>

          <aside className="dashboard-sidebar">
            <ScenePanel
              scenes={scenes}
              roomType={roomType}
              scene={scene}
              loading={loading || isAgentRunning}
              onRoomTypeChange={handleRoomTypeChange}
              onSceneChange={setScene}
              onLoad={handleLoad}
            />
            <ModelSettingsPanel onStatus={setError} />
            <AgentPanel
              taskInstruction={taskInstruction}
              maxSteps={maxSteps}
              disabled={loading || !observation}
              running={isAgentRunning}
              currentStep={agentState?.current_step ?? 0}
              selectedTarget={selectedTarget}
              targetPromptPreview={targetPromptPreview}
              onTaskInstructionChange={setTaskInstruction}
              onMaxStepsChange={setMaxSteps}
              onToggleRun={handleToggleRun}
              onClearTarget={handleClearTarget}
            />
            <ManualControl disabled={sidebarDisabled || !observation} observation={observation} actions={actionSpace} onAction={handleAction} />
            <LatestDecisionCard latestStep={latestDecision} agentState={agentState} onOpenTrajectory={() => setViewMode("trajectory")} />
          </aside>
        </main>
      )}

      {error ? <div className="error-banner">{error}</div> : null}
    </div>
  );
}

export default App;
