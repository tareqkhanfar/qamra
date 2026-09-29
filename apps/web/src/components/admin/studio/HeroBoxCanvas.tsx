"use client";

import { useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import type { Box } from "@/lib/studio";

type Drag = { mode: "move" | "resize"; x: number; y: number; box: Box } | null;
const MIN = 0.04;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** Moves keep the size; resizes keep the corner; the box always stays inside the picture. */
function moved(b: Box, dx: number, dy: number): Box {
  return { ...b, x: clamp(b.x + dx, 0, 1 - b.w), y: clamp(b.y + dy, 0, 1 - b.h) };
}
function resized(b: Box, dw: number, dh: number): Box {
  return { ...b, w: clamp(b.w + dw, MIN, 1 - b.x), h: clamp(b.h + dh, MIN, 1 - b.y) };
}
const place = (b: Box) => ({
  left: `${b.x * 100}%`,
  top: `${b.y * 100}%`,
  width: `${b.w * 100}%`,
  height: `${b.h * 100}%`,
});

/**
 * A template page with its hero box (amber, draggable, resizable from its corner, arrow keys to nudge and
 * shift + arrows to resize) and its text box (dashed, where the renderer puts the words). Coordinates are
 * normalized to the picture (0–1 from its top-left corner), as the API stores them.
 */
export function HeroBoxCanvas({
  src,
  alt,
  box,
  textBox,
  editable,
  onChange,
  labels,
}: {
  src: string | null;
  alt: string;
  box: Box | null;
  textBox: Box | null;
  editable: boolean;
  onChange: (b: Box) => void;
  labels: { hero: string; text: string; missing: string; help: string };
}) {
  const frame = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<Drag>(null);

  function start(e: PointerEvent<HTMLElement>, mode: "move" | "resize") {
    if (!editable || !box) return;
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    setDrag({ mode, x: e.clientX, y: e.clientY, box });
  }

  function move(e: PointerEvent<HTMLElement>) {
    const rect = frame.current?.getBoundingClientRect();
    if (!drag || !rect) return;
    const dx = (e.clientX - drag.x) / rect.width;
    const dy = (e.clientY - drag.y) / rect.height;
    onChange(drag.mode === "move" ? moved(drag.box, dx, dy) : resized(drag.box, dx, dy));
  }

  function key(e: KeyboardEvent<HTMLDivElement>) {
    if (!editable || !box) return;
    const step = 0.01;
    const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key];
    if (!d) return;
    e.preventDefault();
    onChange(e.shiftKey ? resized(box, d[0], d[1]) : moved(box, d[0], d[1]));
  }

  const end = () => setDrag(null);
  if (!src) {
    return (
      <div className="flex aspect-square items-center justify-center rounded-lg border border-dashed border-line bg-paper-sunk p-6 text-center text-ink-muted">
        {labels.missing}
      </div>
    );
  }
  return (
    <figure className="flex flex-col gap-2">
      <div ref={frame} className="relative overflow-hidden rounded-lg bg-paper-sunk select-none" dir="ltr">
        {/* eslint-disable-next-line @next/next/no-img-element -- streamed from the admin API, private */}
        <img src={src} alt={alt} draggable={false} className="block h-auto w-full" />
        {textBox && (
          <div
            className="pointer-events-none absolute rounded-md border-2 border-dashed border-info bg-info/10"
            style={place(textBox)}
          >
            <span className="absolute start-1 top-1 rounded bg-info px-1.5 text-[11px] font-bold text-white">
              {labels.text}
            </span>
          </div>
        )}
        {box && (
          <div
            role="group"
            tabIndex={editable ? 0 : -1}
            aria-label={labels.hero}
            onKeyDown={key}
            onPointerDown={(e) => start(e, "move")}
            onPointerMove={move}
            onPointerUp={end}
            onPointerCancel={end}
            className={`absolute touch-none border-2 border-amber-500 bg-amber-500/15 outline-offset-2 focus-visible:outline-2 focus-visible:outline-night-900 ${editable ? "cursor-move" : ""}`}
            style={place(box)}
          >
            <span className="absolute start-0 top-0 rounded-br bg-amber-500 px-1.5 text-[11px] font-bold whitespace-nowrap text-night-950">
              {labels.hero}
            </span>
            {editable && (
              <span
                aria-hidden="true"
                onPointerDown={(e) => start(e, "resize")}
                className="absolute -right-3 -bottom-3 size-6 cursor-nwse-resize touch-none rounded-full border-2 border-white bg-amber-500 shadow-1"
              />
            )}
          </div>
        )}
      </div>
      {editable && box && <figcaption className="text-caption text-ink-muted">{labels.help}</figcaption>}
    </figure>
  );
}
