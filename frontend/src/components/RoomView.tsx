import { useEffect, useRef, useState, type PointerEvent } from "react";
import type { Observation, RoomViewHit } from "../api/client";

type Props = {
  image: string | null;
  camera: Observation["metadata"]["room_camera"] | null;
  disabled: boolean;
  onInspect: (x: number, y: number) => Promise<RoomViewHit>;
  onOrbit: (deltaYaw: number, deltaPitch: number) => Promise<void>;
};

type PointerPosition = {
  x: number;
  y: number;
};

const ORBIT_YAW_SENSITIVITY = -0.28;
const ORBIT_PITCH_SENSITIVITY = 0.18;

export function RoomView({ image, camera, disabled, onInspect, onOrbit }: Props) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const inspectTimerRef = useRef<number | null>(null);
  const inspectRequestRef = useRef(0);
  const orbitInFlightRef = useRef(false);
  const orbitDeltaRef = useRef({ x: 0, y: 0 });
  const dragOriginRef = useRef<PointerPosition | null>(null);
  const [hover, setHover] = useState<PointerPosition | null>(null);
  const [hit, setHit] = useState<RoomViewHit | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    return () => {
      if (inspectTimerRef.current) {
        window.clearTimeout(inspectTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    setHit(null);
    setHover(null);
    setDragging(false);
    dragOriginRef.current = null;
    orbitDeltaRef.current = { x: 0, y: 0 };
  }, [image]);

  function getNormalizedPosition(clientX: number, clientY: number): PointerPosition | null {
    const viewport = viewportRef.current;
    if (!viewport) {
      return null;
    }

    const rect = viewport.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return null;
    }

    return {
      x: Math.min(1, Math.max(0, (clientX - rect.left) / rect.width)),
      y: Math.min(1, Math.max(0, (clientY - rect.top) / rect.height)),
    };
  }

  function queueInspect(nextHover: PointerPosition) {
    if (inspectTimerRef.current) {
      window.clearTimeout(inspectTimerRef.current);
    }

    const requestId = ++inspectRequestRef.current;
    inspectTimerRef.current = window.setTimeout(async () => {
      const nextHit = await onInspect(nextHover.x, nextHover.y);
      if (requestId === inspectRequestRef.current) {
        setHit(nextHit);
      }
    }, 90);
  }

  async function flushOrbit() {
    if (orbitInFlightRef.current) {
      return;
    }

    const { x, y } = orbitDeltaRef.current;
    if (x === 0 && y === 0) {
      return;
    }

    orbitInFlightRef.current = true;
    orbitDeltaRef.current = { x: 0, y: 0 };
    try {
      await onOrbit(x * ORBIT_YAW_SENSITIVITY, y * ORBIT_PITCH_SENSITIVITY);
    } finally {
      orbitInFlightRef.current = false;
      if (orbitDeltaRef.current.x !== 0 || orbitDeltaRef.current.y !== 0) {
        void flushOrbit();
      }
    }
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    if (!image || disabled) {
      return;
    }

    dragOriginRef.current = { x: event.clientX, y: event.clientY };
    setDragging(true);
    setHit(null);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!image) {
      return;
    }

    const nextHover = getNormalizedPosition(event.clientX, event.clientY);
    if (nextHover) {
      setHover(nextHover);
    }

    if (!dragOriginRef.current || disabled) {
      if (nextHover) {
        queueInspect(nextHover);
      }
      return;
    }

    const deltaX = event.clientX - dragOriginRef.current.x;
    const deltaY = event.clientY - dragOriginRef.current.y;
    dragOriginRef.current = { x: event.clientX, y: event.clientY };
    orbitDeltaRef.current = {
      x: orbitDeltaRef.current.x + deltaX,
      y: orbitDeltaRef.current.y + deltaY,
    };
    void flushOrbit();
  }

  function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
    dragOriginRef.current = null;
    setDragging(false);
    event.currentTarget.releasePointerCapture(event.pointerId);
  }

  function handlePointerLeave() {
    dragOriginRef.current = null;
    setDragging(false);
    setHover(null);
    setHit(null);
    inspectRequestRef.current += 1;
    if (inspectTimerRef.current) {
      window.clearTimeout(inspectTimerRef.current);
    }
  }

  const haloStyle = hover
    ? {
        left: `${hover.x * 100}%`,
        top: `${hover.y * 100}%`,
      }
    : undefined;
  const tooltipClassName = hover
    ? `room-view-tooltip${hover.x > 0.72 ? " is-flipped-x" : ""}${hover.y > 0.72 ? " is-flipped-y" : ""}`
    : "room-view-tooltip";

  return (
    <section className="panel viewer room-viewer observer-panel">
      <div className="viewer-toolbar">
        <span className="viewer-title">观察视角</span>
        <span className="viewer-helper">左拖旋转 · 悬停检查</span>
      </div>
      {image ? (
        <div
          ref={viewportRef}
          className={`interactive-room-view${dragging ? " is-dragging" : ""}${disabled ? " is-disabled" : ""}`}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerLeave}
        >
          <img src={`data:image/png;base64,${image}`} alt="Interactive room view" draggable={false} />
          {hover ? <div className="room-view-halo" style={haloStyle} /> : null}
          {hit?.hit && hit.object ? (
            <div className={tooltipClassName} style={haloStyle}>
              <strong>
                {hit.object.object_type}
                {hit.object.distance != null ? ` | ${hit.object.distance.toFixed(2)}m` : ""}
              </strong>
              <span>{hit.object.object_id}</span>
              {Object.entries(hit.object.attributes).slice(0, 4).map(([key, value]) => (
                <span key={key}>
                  {key}: {String(value)}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="empty">No image</div>
      )}
      <div className="room-view-footer muted observer-footer">
        {camera
          ? `Yaw ${camera.yaw.toFixed(1)} deg | Pitch ${camera.pitch.toFixed(1)} deg | FOV ${camera.field_of_view.toFixed(0)} deg`
          : "Load a scene to activate room view."}
      </div>
    </section>
  );
}
