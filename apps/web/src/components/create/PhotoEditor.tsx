"use client";

import { useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import {
  FRAME,
  fromCrop,
  layout,
  maxZoom,
  OVAL,
  pan,
  rotateView,
  toCrop,
  viewAt,
  zoomOf,
  zoomTo,
  type PhotoCrop,
  type Size,
  type View,
} from "@/lib/photoCrop";

const KEY_STEP = 0.03; // an arrow key moves the photo 3% of the frame (Shift: three times more)
const ZOOM_STEP = 0.1;
const ARROWS: Record<string, [number, number]> = {
  ArrowLeft: [-1, 0],
  ArrowRight: [1, 0],
  ArrowUp: [0, -1],
  ArrowDown: [0, 1],
};

/**
 * The photo frame of the photo step (design Create3) and its face-guide oval. `editable`: the parent drags the
 * photo (mouse or finger), pinches or uses the slider to zoom (1×–3×, less for a small photo), turns it a
 * quarter, resets it; on a keyboard, the arrows move it and + / − zoom. The photo always covers the frame
 * (lib/photoCrop.ts). `crop` is the framing shown (null: centred, unzoomed); every change comes back through
 * `onChange` as the API stores it. `children` sit over the photo (the guide's label, «تغيير الصورة»).
 */
export function PhotoEditor({
  src,
  crop,
  editable,
  onChange,
  onNatural,
  placeholder,
  children,
}: {
  src: string | null; // an object URL of the photo (picked on this device, or the kept original)
  crop: PhotoCrop | null;
  editable: boolean;
  onChange: (crop: PhotoCrop) => void;
  onNatural?: (size: Size) => void; // the photo's size once it is loaded
  placeholder?: ReactNode; // shown while there is no photo
  children?: ReactNode;
}) {
  const t = useTranslations("create.photo.editor");
  const frameRef = useRef<HTMLDivElement>(null);
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const live = useRef<View | null>(null); // the view during a drag, ahead of the next render
  const [loaded, setLoaded] = useState<{ src: string; size: Size } | null>(null);
  const [frame, setFrame] = useState<Size>(FRAME);
  const hint = useId();

  useEffect(() => {
    const el = frameRef.current;
    if (!el) return;
    const observer = new ResizeObserver(() =>
      setFrame({ w: el.clientWidth || FRAME.w, h: el.clientHeight || FRAME.h }),
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const natural = loaded && loaded.src === src ? loaded.size : null;
  const view = natural ? (crop ? fromCrop(crop) : viewAt(natural, 0)) : null;
  const zoom = view && natural ? zoomOf(view, natural) : 1;
  const limit = view && natural ? maxZoom(natural, view.rotate) : 1;
  const box = view && natural ? layout(view, natural, frame) : null;
  const active = editable && !!view && !!natural;

  function emit(next: View) {
    live.current = next;
    onChange(toCrop(next));
  }

  function down(e: PointerEvent<HTMLDivElement>) {
    // a button over the photo («تغيير الصورة») keeps its click: no capture from there
    if (!active || (e.target as HTMLElement).closest("button")) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    live.current = view;
  }

  function move(e: PointerEvent<HTMLDivElement>) {
    const map = pointers.current;
    const last = map.get(e.pointerId);
    const current = live.current;
    if (!active || !last || !current || !natural) return;
    const now = { x: e.clientX, y: e.clientY };
    map.set(e.pointerId, now);
    const other = [...map.entries()].find(([id]) => id !== e.pointerId)?.[1];
    if (!other) {
      emit(pan(current, now.x - last.x, now.y - last.y, frame));
      return;
    }
    // two fingers: zoom around their middle by how far apart they moved, and follow the middle
    const before = Math.hypot(last.x - other.x, last.y - other.y);
    const after = Math.hypot(now.x - other.x, now.y - other.y);
    const rect = e.currentTarget.getBoundingClientRect();
    const at = {
      x: ((now.x + other.x) / 2 - rect.left) / rect.width,
      y: ((now.y + other.y) / 2 - rect.top) / rect.height,
    };
    const zoomed = before > 0 ? zoomTo(current, zoomOf(current, natural) * (after / before), natural, at) : current;
    emit(pan(zoomed, (now.x - last.x) / 2, (now.y - last.y) / 2, frame));
  }

  function up(e: PointerEvent<HTMLDivElement>) {
    pointers.current.delete(e.pointerId);
    if (!pointers.current.size) live.current = null;
  }

  function key(e: KeyboardEvent<HTMLDivElement>) {
    if (!active || !view || !natural) return;
    const arrow = ARROWS[e.key];
    const step = KEY_STEP * (e.shiftKey ? 3 : 1);
    let next: View | null = null;
    if (arrow) next = pan(view, arrow[0] * step * frame.w, arrow[1] * step * frame.h, frame);
    else if (e.key === "+" || e.key === "=") next = zoomTo(view, zoom + ZOOM_STEP, natural);
    else if (e.key === "-" || e.key === "_") next = zoomTo(view, zoom - ZOOM_STEP, natural);
    if (!next) return;
    e.preventDefault();
    emit(next);
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        ref={frameRef}
        tabIndex={active ? 0 : undefined}
        aria-label={active ? t("area") : undefined}
        aria-describedby={active ? hint : undefined}
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerCancel={up}
        onKeyDown={key}
        className={`relative mx-auto aspect-[358/340] w-full max-w-[420px] overflow-hidden rounded-3xl bg-[#D9D3C7] outline-offset-4 select-none focus-visible:outline-2 focus-visible:outline-night-900 ${active ? "cursor-grab touch-none active:cursor-grabbing" : ""}`}
      >
        {!src && <div className="absolute inset-0 flex items-end justify-center">{placeholder}</div>}
        {src && (
          // eslint-disable-next-line @next/next/no-img-element -- the child's photo from this device or the API (no-store), never public
          <img
            src={src}
            alt=""
            draggable={false}
            onLoad={(e) => {
              const size = { w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight };
              setLoaded({ src, size });
              onNatural?.(size);
            }}
            className="pointer-events-none absolute max-w-none origin-center"
            style={
              box
                ? {
                    left: box.left,
                    top: box.top,
                    width: box.width,
                    height: box.height,
                    transform: box.rotate ? `rotate(${box.rotate}deg)` : undefined,
                  }
                : { opacity: 0 }
            }
          />
        )}
        <svg
          viewBox={`0 0 ${FRAME.w} ${FRAME.h}`}
          className="pointer-events-none absolute inset-0 size-full"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          {active && (
            // the frame outside the oval, dimmed while the parent places the face
            <path
              fillRule="evenodd"
              fill="rgba(14,21,48,0.35)"
              d={`M0 0H${FRAME.w}V${FRAME.h}H0Z M${OVAL.cx - OVAL.rx} ${OVAL.cy}a${OVAL.rx} ${OVAL.ry} 0 1 0 ${2 * OVAL.rx} 0a${OVAL.rx} ${OVAL.ry} 0 1 0 ${-2 * OVAL.rx} 0Z`}
            />
          )}
          <ellipse
            cx={OVAL.cx}
            cy={OVAL.cy}
            rx={OVAL.rx}
            ry={OVAL.ry}
            fill="none"
            stroke="#FFFDF8"
            strokeWidth="3"
            strokeDasharray="10 8"
          />
        </svg>
        {children}
      </div>

      {active && view && natural && (
        <>
          <p id={hint} className="text-center text-small text-ink-muted">
            {t("hint")}
          </p>
          {/* in RTL the slider grows to the left, so − stays at its small end and + at its big end */}
          <div className="mx-auto flex w-full max-w-[420px] items-center gap-1.5">
            <Round
              label={t("zoomOut")}
              onClick={() => emit(zoomTo(view, zoom - ZOOM_STEP, natural))}
              disabled={zoom <= 1.001}
            >
              <path d="M6 12h12" />
            </Round>
            <input
              type="range"
              min={1}
              max={Math.max(1, limit)}
              step={0.01}
              value={Math.min(zoom, limit)}
              disabled={limit <= 1.001}
              onChange={(e) => emit(zoomTo(view, Number(e.target.value), natural))}
              aria-label={t("zoom")}
              className="h-11 min-w-0 grow accent-night-900 disabled:opacity-40"
            />
            <Round
              label={t("zoomIn")}
              onClick={() => emit(zoomTo(view, zoom + ZOOM_STEP, natural))}
              disabled={zoom >= limit - 0.001}
            >
              <path d="M6 12h12M12 6v12" />
            </Round>
            <Round label={t("rotate")} onClick={() => emit(rotateView(view, natural))}>
              <path d="M20 12a8 8 0 1 1-2.3-5.7" />
              <path d="M20 4v5h-5" />
            </Round>
            <Round label={t("reset")} onClick={() => emit(viewAt(natural, 0))}>
              <path d="M4 12a8 8 0 1 0 2.3-5.7" />
              <path d="M4 4v5h5" />
            </Round>
          </div>
        </>
      )}
    </div>
  );
}

/** A round 44 px icon button of the editor's controls. */
function Round({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      disabled={disabled}
      className="flex size-11 shrink-0 items-center justify-center rounded-full border-[1.5px] border-line bg-paper-raised text-night-900 disabled:opacity-40"
    >
      <svg className="size-5" viewBox="0 0 24 24" aria-hidden="true">
        <g fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          {children}
        </g>
      </svg>
    </button>
  );
}
