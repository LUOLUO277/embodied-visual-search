import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import type { Observation, RoomObjectSelection, RoomViewHit } from "../api/client";

type Props = {
  image: string | null;
  camera: Observation["metadata"]["room_camera"] | null;
  disabled: boolean;
  onInspect: (x: number, y: number) => Promise<RoomViewHit>;
  onOrbit: (deltaYaw: number, deltaPitch: number, deltaDistance?: number) => Promise<void>;
  onSelect: (x: number, y: number) => Promise<RoomObjectSelection>;
};

type PointerPosition = {
  x: number;
  y: number;
};

type ContentRect = {
  left: number;
  top: number;
  width: number;
  height: number;
};

const ORBIT_YAW_SENSITIVITY = -0.15;
const ORBIT_PITCH_SENSITIVITY = 0.09;
const DRAG_THRESHOLD = 6;
const KEYBOARD_YAW_STEP = 12;

export function RoomView({ image, camera, disabled, onInspect, onOrbit, onSelect }: Props) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const inspectTimerRef = useRef<number | null>(null);
  const inspectRequestRef = useRef(0);
  const orbitInFlightRef = useRef(false);
  const rafRef = useRef<number | null>(null);
  const orbitDeltaRef = useRef({ x: 0, y: 0, distance: 0 });
  const pointerDownRef = useRef<PointerPosition | null>(null);
  const lastPointerRef = useRef<PointerPosition | null>(null);
  const [hover, setHover] = useState<PointerPosition | null>(null);
  const [hit, setHit] = useState<RoomViewHit | null>(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    return () => {
      if (inspectTimerRef.current) {
        window.clearTimeout(inspectTimerRef.current);
      }
      if (rafRef.current) {
        window.cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  useEffect(() => {
    setHit(null);
    setHover(null);
    setDragging(false);
    pointerDownRef.current = null;
    lastPointerRef.current = null;
    orbitDeltaRef.current = { x: 0, y: 0, distance: 0 };
  }, [image]);

  function getImageContentRect(): ContentRect | null {
    const imageElement = imageRef.current;
    if (!imageElement) {
      return null;
    }

    const rect = imageElement.getBoundingClientRect();
    const naturalWidth = imageElement.naturalWidth;
    const naturalHeight = imageElement.naturalHeight;
    if (rect.width <= 0 || rect.height <= 0 || naturalWidth <= 0 || naturalHeight <= 0) {
      return null;
    }

    const elementAspect = rect.width / rect.height;
    const imageAspect = naturalWidth / naturalHeight;

    if (imageAspect > elementAspect) {
      const contentHeight = rect.width / imageAspect;
      const verticalPadding = (rect.height - contentHeight) / 2;
      return { left: rect.left, top: rect.top + verticalPadding, width: rect.width, height: contentHeight };
    }

    const contentWidth = rect.height * imageAspect;
    const horizontalPadding = (rect.width - contentWidth) / 2;
    return { left: rect.left + horizontalPadding, top: rect.top, width: contentWidth, height: rect.height };
  }

  function getNormalizedPosition(clientX: number, clientY: number): PointerPosition | null {
    const contentRect = getImageContentRect();
    if (!contentRect || contentRect.width <= 0 || contentRect.height <= 0) {
      return null;
    }

    const relativeX = (clientX - contentRect.left) / contentRect.width;
    const relativeY = (clientY - contentRect.top) / contentRect.height;
    if (relativeX < 0 || relativeX > 1 || relativeY < 0 || relativeY > 1) {
      return null;
    }

    return {
      x: Math.min(1, Math.max(0, relativeX)),
      y: Math.min(1, Math.max(0, relativeY)),
    };
  }

  function toOverlayStyle(position: PointerPosition | null) {
    const contentRect = getImageContentRect();
    const viewport = viewportRef.current;
    if (!position || !contentRect || !viewport) {
      return undefined;
    }

    const viewportRect = viewport.getBoundingClientRect();
    return {
      left: `${((contentRect.left - viewportRect.left + position.x * contentRect.width) / viewportRect.width) * 100}%`,
      top: `${((contentRect.top - viewportRect.top + position.y * contentRect.height) / viewportRect.height) * 100}%`,
    };
  }

  function cancelInspect() {
    inspectRequestRef.current += 1;
    if (inspectTimerRef.current) {
      window.clearTimeout(inspectTimerRef.current);
      inspectTimerRef.current = null;
    }
  }

  function queueInspect(nextHover: PointerPosition) {
    cancelInspect();
    const requestId = ++inspectRequestRef.current;
    inspectTimerRef.current = window.setTimeout(async () => {
      const nextHit = await onInspect(nextHover.x, nextHover.y);
      if (requestId === inspectRequestRef.current) {
        setHit(nextHit);
      }
    }, 120);
  }

  async function flushOrbit() {
    if (orbitInFlightRef.current) {
      return;
    }

    const { x, y, distance } = orbitDeltaRef.current;
    if (x === 0 && y === 0 && distance === 0) {
      return;
    }

    orbitInFlightRef.current = true;
    orbitDeltaRef.current = { x: 0, y: 0, distance: 0 };
    try {
      await onOrbit(x * ORBIT_YAW_SENSITIVITY, y * ORBIT_PITCH_SENSITIVITY, distance);
    } finally {
      orbitInFlightRef.current = false;
      if (orbitDeltaRef.current.x !== 0 || orbitDeltaRef.current.y !== 0 || orbitDeltaRef.current.distance !== 0) {
        void flushOrbit();
      }
    }
  }

  function requestOrbitFlush() {
    if (rafRef.current != null) {
      return;
    }
    rafRef.current = window.requestAnimationFrame(() => {
      rafRef.current = null;
      void flushOrbit();
    });
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    if (!image || disabled || event.button !== 0) {
      return;
    }
    const point = { x: event.clientX, y: event.clientY };
    pointerDownRef.current = point;
    lastPointerRef.current = point;
    setDragging(false);
    setHit(null);
    cancelInspect();
    event.currentTarget.focus();
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!image) {
      return;
    }

    const nextHover = getNormalizedPosition(event.clientX, event.clientY);
    if (nextHover) {
      setHover(nextHover);
    } else if (!dragging) {
      setHover(null);
      setHit(null);
    }

    if (!pointerDownRef.current || !lastPointerRef.current || disabled) {
      if (nextHover && !dragging) {
        queueInspect(nextHover);
      }
      return;
    }

    const movedX = event.clientX - pointerDownRef.current.x;
    const movedY = event.clientY - pointerDownRef.current.y;
    if (!dragging && Math.hypot(movedX, movedY) >= DRAG_THRESHOLD) {
      setDragging(true);
    }
    if (!dragging && nextHover) {
      return;
    }

    const deltaX = event.clientX - lastPointerRef.current.x;
    const deltaY = event.clientY - lastPointerRef.current.y;
    lastPointerRef.current = { x: event.clientX, y: event.clientY };
    orbitDeltaRef.current = {
      ...orbitDeltaRef.current,
      x: orbitDeltaRef.current.x + deltaX,
      y: orbitDeltaRef.current.y + deltaY,
    };
    requestOrbitFlush();
  }

  async function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
    const normalized = getNormalizedPosition(event.clientX, event.clientY);
    const wasDragging = dragging;
    pointerDownRef.current = null;
    lastPointerRef.current = null;
    setDragging(false);
    event.currentTarget.releasePointerCapture(event.pointerId);

    if (!normalized || disabled || wasDragging) {
      if (normalized) {
        queueInspect(normalized);
      }
      return;
    }

    const selection = await onSelect(normalized.x, normalized.y);
    setHit(selection);
  }

  function handlePointerLeave() {
    pointerDownRef.current = null;
    lastPointerRef.current = null;
    setDragging(false);
    setHover(null);
    setHit(null);
    cancelInspect();
  }

  async function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (!image || disabled) {
      return;
    }
    if (event.key.toLowerCase() === "q") {
      event.preventDefault();
      cancelInspect();
      await onOrbit(-KEYBOARD_YAW_STEP, 0, 0);
      return;
    }
    if (event.key.toLowerCase() === "e") {
      event.preventDefault();
      cancelInspect();
      await onOrbit(KEYBOARD_YAW_STEP, 0, 0);
    }
  }

  const haloStyle = toOverlayStyle(hover);
  const tooltipAnchor = hover ?? (hit?.hit ? { x: hit.normalized_x, y: hit.normalized_y } : null);
  const tooltipStyle = toOverlayStyle(tooltipAnchor);
  const tooltipClassName = tooltipAnchor
    ? `room-view-tooltip${tooltipAnchor.x > 0.72 ? " is-flipped-x" : ""}${tooltipAnchor.y > 0.72 ? " is-flipped-y" : ""}`
    : "room-view-tooltip";

  return (
    <section className="panel viewer room-viewer observer-panel">
      <div className="viewer-toolbar">
        <span className="viewer-title">观察视角</span>
        <span className="viewer-helper">左键拖拽旋转 · Q/E 键旋转 · 点击选择目标</span>
      </div>
      {image ? (
        <div
          ref={viewportRef}
          className={`interactive-room-view${dragging ? " is-dragging" : ""}${disabled ? " is-disabled" : ""}`}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerLeave}
          onKeyDown={(event) => void handleKeyDown(event)}
          tabIndex={disabled ? -1 : 0}
        >
          <img ref={imageRef} src={`data:image/png;base64,${image}`} alt="Interactive room view" draggable={false} />
          {hover && haloStyle ? <div className="room-view-halo" style={haloStyle} /> : null}
          {!dragging && hit?.hit && hit.object && tooltipStyle ? (
            <div className={tooltipClassName} style={tooltipStyle}>
              <strong>
                {hit.object.object_type}
                {hit.object.distance != null ? ` | ${hit.object.distance.toFixed(2)}m` : ""}
              </strong>
              <span>{hit.object.name}</span>
              {Object.entries(hit.object.attributes)
                .slice(0, 4)
                .map(([key, value]) => (
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
          ? `Yaw ${camera.yaw.toFixed(1)} deg | Pitch ${camera.pitch.toFixed(1)} deg | Distance ${camera.distance.toFixed(2)} m`
          : "Load a scene to activate room view."}
      </div>
    </section>
  );
}
