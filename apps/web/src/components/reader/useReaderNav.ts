"use client";

import { useCallback, useEffect, useRef, useState, type PointerEvent, type RefObject } from "react";

const SWIPE_PX = 48;

function reducedMotion(): boolean {
  if (typeof window === "undefined") return true;
  return (
    window.matchMedia("(prefers-reduced-motion: reduce)").matches || document.documentElement.dataset.motion === "off"
  );
}

/**
 * Page turning for the reader: buttons, keyboard and swipe, in the book's direction.
 * In an Arabic (RTL) book the next page is to the left: ArrowLeft and a swipe to the right turn forward.
 * The turn is a short 3D flip from the spine (Web Animations: no inline styles, so the CSP stays strict).
 */
export function useReaderNav(
  total: number,
  dir: "rtl" | "ltr",
  keysEnabled: boolean,
  pageRef: RefObject<HTMLElement | null>,
) {
  const [pos, setPos] = useState<{ index: number; step: 1 | -1 }>({ index: 0, step: 1 });
  const start = useRef<{ x: number; y: number } | null>(null);

  const go = useCallback(
    (step: 1 | -1) =>
      setPos((p) => {
        const index = Math.min(total - 1, Math.max(0, p.index + step));
        return index === p.index ? p : { index, step };
      }),
    [total],
  );
  const jump = useCallback(
    (to: number) => setPos((p) => (to === p.index ? p : { index: to, step: to > p.index ? 1 : -1 })),
    [],
  );

  useEffect(() => {
    const el = pageRef.current;
    if (!el || reducedMotion() || typeof el.animate !== "function") return;
    const forward = pos.step === 1;
    const spine = dir === "rtl" ? "right" : "left";
    const angle = (dir === "rtl" ? 1 : -1) * (forward ? 70 : -70);
    el.style.transformOrigin = forward ? `${spine} center` : `${spine === "right" ? "left" : "right"} center`;
    el.animate(
      [
        { transform: `perspective(1800px) rotateY(${angle}deg)`, opacity: 0.35 },
        { transform: "perspective(1800px) rotateY(0deg)", opacity: 1 },
      ],
      { duration: 420, easing: "cubic-bezier(0.2, 0.7, 0.2, 1)" },
    );
  }, [pos, dir, pageRef]);

  useEffect(() => {
    if (!keysEnabled) return;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
      const forwardKey = dir === "rtl" ? "ArrowLeft" : "ArrowRight";
      const backKey = dir === "rtl" ? "ArrowRight" : "ArrowLeft";
      if (e.key === forwardKey || e.key === "PageDown" || (e.key === " " && !e.shiftKey)) go(1);
      else if (e.key === backKey || e.key === "PageUp" || (e.key === " " && e.shiftKey)) go(-1);
      else if (e.key === "Home") jump(0);
      else if (e.key === "End") jump(total - 1);
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dir, go, jump, keysEnabled, total]);

  const swipe = {
    onPointerDown: (e: PointerEvent) => {
      start.current = { x: e.clientX, y: e.clientY };
    },
    onPointerUp: (e: PointerEvent) => {
      const s = start.current;
      start.current = null;
      if (!s) return;
      const dx = e.clientX - s.x;
      const dy = e.clientY - s.y;
      if (Math.abs(dx) < SWIPE_PX || Math.abs(dx) < Math.abs(dy) * 1.5) return;
      const forward = dir === "rtl" ? dx > 0 : dx < 0;
      go(forward ? 1 : -1);
    },
    onPointerCancel: () => {
      start.current = null;
    },
  };

  return { index: pos.index, go, jump, swipe };
}
