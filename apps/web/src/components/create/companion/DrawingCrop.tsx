"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRef, useState, type PointerEvent } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button, Spinner } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { companionApi, drawingImage, type Box, type Companion, type Rotation } from "@/lib/companion";
import { SubFrame } from "./SubFrame";

const FULL: Box = { x: 0, y: 0, w: 1, h: 1 };
const MIN = 0.1;
type Corner = "tl" | "tr" | "bl" | "br";
const CORNERS: Corner[] = ["tl", "tr", "bl", "br"];

/** Drag one corner; the opposite corner stays where it is. Fractions of the photo (0–1). */
function moved(box: Box, corner: Corner, px: number, py: number): Box {
  const x = Math.max(0, Math.min(1, px));
  const y = Math.max(0, Math.min(1, py));
  const left = corner.endsWith("l") ? Math.min(x, box.x + box.w - MIN) : box.x;
  const right = corner.endsWith("r") ? Math.max(x, box.x + MIN) : box.x + box.w;
  const top = corner.startsWith("t") ? Math.min(y, box.y + box.h - MIN) : box.y;
  const bottom = corner.startsWith("b") ? Math.max(y, box.y + MIN) : box.y + box.h;
  return { x: left, y: top, w: right - left, h: bottom - top };
}

/** Design CompCrop: the original or the cleaned drawing, 4 crop handles, rotate, and paper/shadow removal. */
export function DrawingCrop({
  companion,
  back,
  onChange,
  onDone,
}: {
  companion: Companion;
  back: () => void;
  onChange: (c: Companion) => void;
  onDone: () => void;
}) {
  const t = useTranslations("companion.crop");
  const te = useTranslations("errors");
  const locale = useLocale();
  const stage = useRef<HTMLDivElement>(null);
  const [view, setView] = useState<"cleaned" | "original">("cleaned");
  const [box, setBox] = useState<Box>(companion.box ?? FULL);
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function apply(next: { box?: Box | null; rotate?: Rotation; clean?: boolean }) {
    setBusy(true);
    setError(null);
    const r = await companionApi.crop(companion.id, {
      box: next.box !== undefined ? next.box : companion.box,
      rotate: next.rotate ?? companion.rotate,
      clean: next.clean ?? companion.clean,
    });
    setBusy(false);
    if (r.ok) {
      onChange(r.data);
      setVersion((v) => v + 1);
    } else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  function drag(corner: Corner) {
    return {
      onPointerDown: (e: PointerEvent<HTMLButtonElement>) => e.currentTarget.setPointerCapture(e.pointerId),
      onPointerMove: (e: PointerEvent<HTMLButtonElement>) => {
        if (!e.currentTarget.hasPointerCapture(e.pointerId) || !stage.current) return;
        const r = stage.current.getBoundingClientRect();
        setBox((b) => moved(b, corner, (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height));
      },
      onPointerUp: () => void apply({ box }),
    };
  }

  const canCrop = companion.original;
  return (
    <SubFrame
      title={t("title")}
      back={back}
      footer={
        <div className="flex items-center gap-2">
          <button type="button" onClick={back} className="min-h-14 px-4 font-display text-body font-semibold">
            {t("retake")}
          </button>
          <Button size="lg" className="grow" onClick={onDone} disabled={busy}>
            {t("ready")}
          </Button>
        </div>
      }
    >
      {canCrop && (
        <div role="tablist" aria-label={t("view")} className="grid grid-cols-2 rounded-full bg-paper-sunk p-1">
          {(["original", "cleaned"] as const).map((v) => (
            <button
              key={v}
              type="button"
              role="tab"
              aria-selected={view === v}
              onClick={() => setView(v)}
              className={`min-h-11 rounded-full text-body ${view === v ? "bg-paper-raised font-bold text-night-900 shadow-1" : "text-ink-muted"}`}
            >
              {t(v)}
            </button>
          ))}
        </div>
      )}
      <div className="relative flex h-[380px] items-center justify-center overflow-hidden rounded-[20px] bg-night-100 bg-[linear-gradient(45deg,#D8DDF0_25%,transparent_25%,transparent_75%,#D8DDF0_75%),linear-gradient(45deg,#D8DDF0_25%,transparent_25%,transparent_75%,#D8DDF0_75%)] bg-[length:24px_24px] bg-[position:0_0,12px_12px] p-6">
        <div ref={stage} className="relative inline-block max-h-full touch-none select-none">
          {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API, no-store */}
          <img
            src={drawingImage(companion.id, view, version)}
            alt={t(view === "original" ? "originalAlt" : "cleanedAlt")}
            draggable={false}
            className="block max-h-[332px] max-w-full"
          />
          {view === "original" && (
            <div
              aria-label={t("area")}
              className="absolute border-2 border-night-900 shadow-[0_0_0_999px_rgba(14,21,48,0.35)]"
              style={{
                left: `${box.x * 100}%`,
                top: `${box.y * 100}%`,
                width: `${box.w * 100}%`,
                height: `${box.h * 100}%`,
              }}
            >
              {CORNERS.map((c) => (
                <button
                  key={c}
                  type="button"
                  aria-label={t(`corner.${c}`)}
                  {...drag(c)}
                  className={`absolute flex size-11 items-center justify-center ${c.startsWith("t") ? "-top-[22px]" : "-bottom-[22px]"} ${c.endsWith("l") ? "-left-[22px]" : "-right-[22px]"}`}
                >
                  <span className="size-4 rounded-[4px] border-2 border-night-900 bg-amber-500" />
                </button>
              ))}
            </div>
          )}
        </div>
        {busy && (
          <span className="absolute inset-x-0 bottom-3 flex justify-center" role="status">
            <span className="flex items-center gap-2 rounded-full bg-paper-raised px-3 py-1.5 text-caption shadow-1">
              <Spinner /> {t("applying")}
            </span>
          </span>
        )}
      </div>
      <p className="text-center text-caption text-ink-muted">{canCrop ? t("hint") : t("gone")}</p>
      <div className="flex gap-2.5">
        <button
          type="button"
          disabled={!canCrop || busy}
          onClick={() => void apply({ rotate: ((companion.rotate + 90) % 360) as Rotation })}
          className="flex min-h-12 flex-1 items-center justify-center gap-1.5 rounded-[14px] border-[1.5px] border-line bg-paper-raised text-small font-semibold disabled:opacity-40"
        >
          <svg className="size-[18px]" viewBox="0 0 24 24" aria-hidden="true">
            <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 12a8 8 0 1 1-2.3-5.7" />
              <path d="M20 4v5h-5" />
            </g>
          </svg>
          {t("rotate")}
        </button>
        <label className="flex min-h-12 flex-[2] items-center justify-between gap-2 rounded-[14px] border-[1.5px] border-night-900 bg-night-100 px-3.5 text-small font-semibold">
          {t("clean")}
          <input
            type="checkbox"
            checked={companion.clean}
            disabled={!canCrop || busy}
            onChange={(e) => void apply({ clean: e.target.checked })}
            className="size-[22px] accent-night-900"
          />
        </label>
      </div>
      {error && <Alert>{error}</Alert>}
    </SubFrame>
  );
}
