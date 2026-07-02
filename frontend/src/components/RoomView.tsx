type Props = {
  image: string | null;
};

export function RoomView({ image }: Props) {
  return (
    <section className="panel viewer">
      <h2>Room View</h2>
      {image ? <img src={image} alt="Third-party room view" /> : <div className="empty">No image</div>}
    </section>
  );
}
