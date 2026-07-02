import type { ScenePayload } from "../api/client";

type Props = {
  scenes: ScenePayload | null;
  roomType: string;
  scene: string;
  task: string;
  loading: boolean;
  onRoomTypeChange: (value: string) => void;
  onSceneChange: (value: string) => void;
  onTaskChange: (value: string) => void;
  onLoad: () => void;
};

export function ScenePanel(props: Props) {
  const sceneOptions = props.scenes?.scenes_by_room[props.roomType] ?? [];

  return (
    <section className="panel">
      <h2>Scene Selection</h2>
      <label>
        Room Type
        <select value={props.roomType} onChange={(e) => props.onRoomTypeChange(e.target.value)}>
          {props.scenes?.room_types.map((room) => (
            <option key={room} value={room}>
              {room}
            </option>
          ))}
        </select>
      </label>

      <label>
        Scene
        <select value={props.scene} onChange={(e) => props.onSceneChange(e.target.value)}>
          {sceneOptions.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>

      <label>
        Task
        <input
          value={props.task}
          onChange={(e) => props.onTaskChange(e.target.value)}
          placeholder="Find the sofa"
        />
      </label>

      <button onClick={props.onLoad} disabled={props.loading || !props.scene}>
        {props.loading ? "Loading..." : "Load Scene"}
      </button>
    </section>
  );
}
