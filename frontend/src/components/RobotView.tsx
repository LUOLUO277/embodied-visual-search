type Props = {
  image: string | null;
  sceneName?: string;
  stepLabel?: string;
};

export function RobotView({ image, sceneName, stepLabel }: Props) {
  return (
    <section className="panel viewer hero-viewer">
      <div className="viewer-toolbar">
        <span className="viewer-title">机器人第一人称</span>
        <span className="viewer-chip">{stepLabel || "第 0 步"}</span>
      </div>
      <div className="viewer-stage">
        {image ? <img src={`data:image/png;base64,${image}`} alt="Robot first-person view" /> : <div className="empty">No image</div>}
      </div>
      <div className="viewer-status">状态：环境就绪 · {sceneName || "未加载场景"}</div>
    </section>
  );
}
