import { useEffect, useState } from "react";
import { api, type Observation, type RoomViewHit, type ScenePayload, type TrajectoryItem } from "./api/client";
import { AgentPanel } from "./components/AgentPanel";
import { ManualControl } from "./components/ManualControl";
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
  const [observation, setObservation] = useState<Observation | null>(null);
  const [trajectory, setTrajectory] = useState<TrajectoryItem[]>([]);
  const [thought, setThought] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
    } catch (err) {
      setError(String(err));
    }
  }

  function syncObservation(nextObservation: Observation) {
    setObservation(nextObservation);
    setError(nextObservation.metadata.error_message || "");
  }

  async function refreshTrajectory() {
    const response = await api.getTrajectory();
    setTrajectory(response.items);
  }

  async function handleLoad() {
    try {
      setLoading(true);
      const result = await api.loadScene(scene, task);
      syncObservation(result);
      setThought("");
      await refreshTrajectory();
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

  async function handleAgentStep() {
    try {
      setLoading(true);
      const result = await api.agentStep(task);
      setThought(result.decision.thought);
      syncObservation(result.observation);
      await refreshTrajectory();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
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
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">AI2-THOR Online Interaction Prototype</p>
          <h1>Embodied Visual Search Agent V1</h1>
        </div>
        <div className="status-card">
          <p>Scene: {observation?.metadata.scene_name || scene || "-"}</p>
          <p>Task: {task || "-"}</p>
          <p>Last Success: {String(observation?.metadata.last_action_success ?? false)}</p>
        </div>
      </header>

      <main className="layout">
        <div className="sidebar">
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
          <ManualControl disabled={loading || !observation} onAction={handleAction} />
          <AgentPanel task={task} thought={thought} disabled={loading || !observation} onStep={handleAgentStep} />
        </div>

        <div className="content">
          <section className="view-grid">
            <RobotView image={observation?.robot_view ?? null} />
            <RoomView
              image={observation?.room_view ?? null}
              camera={observation?.metadata.room_camera ?? null}
              disabled={!observation || loading}
              onInspect={handleRoomInspect}
              onOrbit={handleRoomOrbit}
            />
          </section>

          <section className="panel metadata-panel">
            <h2>Metadata</h2>
            {observation ? (
              <>
                <p>Scene: {observation.metadata.scene_name}</p>
                <p>Pose: {JSON.stringify(observation.metadata.agent_pose)}</p>
                <p>Visible Objects: {observation.metadata.visible_objects.join(", ") || "-"}</p>
                <p>Room Camera: {observation.metadata.room_camera ? JSON.stringify(observation.metadata.room_camera.rotation) : "-"}</p>
                <p>Error: {observation.metadata.error_message || "-"}</p>
              </>
            ) : (
              <div className="empty">Load a scene first</div>
            )}
          </section>

          <TrajectoryPanel items={trajectory} />
        </div>
      </main>

      {error ? <div className="error-banner">{error}</div> : null}
    </div>
  );
}

export default App;
