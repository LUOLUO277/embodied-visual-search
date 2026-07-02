type Props = {
  image: string | null;
};

export function RobotView({ image }: Props) {
  return (
    <section className="panel viewer">
      <h2>Robot View</h2>
      {image ? <img src={image} alt="Robot first-person view" /> : <div className="empty">No image</div>}
    </section>
  );
}
