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
    <section className="panel side-panel">
      <div className="panel-title-row">
        <h2>房间设定</h2>
      </div>
      <label>
        房型
        <select value={props.roomType} onChange={(e) => props.onRoomTypeChange(e.target.value)}>
          {props.scenes?.room_types.map((room) => (
            <option key={room} value={room}>
              {room}
            </option>
          ))}
        </select>
      </label>

      <label>
        场景
        <select value={props.scene} onChange={(e) => props.onSceneChange(e.target.value)}>
          {sceneOptions.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>

      <label>
        场景任务描述
        <input value={props.task} onChange={(e) => props.onTaskChange(e.target.value)} placeholder="Find the sofa" />
      </label>

      <button onClick={props.onLoad} disabled={props.loading || !props.scene}>
        {props.loading ? "加载中..." : "载入场景"}
      </button>
    </section>
  );
}
