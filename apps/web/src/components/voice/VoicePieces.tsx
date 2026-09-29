"use client";

import { useState } from "react";

export function Icon({ d, className = "size-5", fill = false }: { d: string; className?: string; fill?: boolean }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill={fill ? "currentColor" : "none"}
      stroke={fill ? "none" : "currentColor"}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}

export const ICONS = {
  close: "M6 6l12 12M18 6L6 18",
  again: "M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5",
  play: "M8 5v14l11-7z",
  pause: "M7 5h3v14H7zM14 5h3v14h-3z",
  mic: "M12 3a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3ZM6 11a6 6 0 0 0 12 0M12 17v4",
  trash: "M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3",
  back: "M5 12h14M13 6l6 6-6 6",
};

/** One dot per page: recorded (green), this page (amber), still to record. */
export function Dots({ done, current, label }: { done: boolean[]; current: number; label: string }) {
  return (
    <div className="flex gap-[3px] px-2" role="img" aria-label={label}>
      {done.map((ok, i) => (
        <span
          key={i}
          className={`h-1.5 flex-1 rounded-full ${i === current ? "bg-amber-500" : ok ? "bg-success" : "bg-line"}`}
        />
      ))}
    </div>
  );
}

/** Live input level while recording (decorative: the timer next to it is the accessible part). */
export function Wave({ levels, bars }: { levels: number[]; bars: number }) {
  const padded = [...levels, ...Array(Math.max(0, bars - levels.length)).fill(-1)];
  return (
    <div aria-hidden="true" className="flex h-12 items-center gap-[3px]">
      {padded.map((v, i) => (
        <span
          key={i}
          className={`flex-1 rounded-[3px] ${v < 0 ? "bg-line-dark" : "bg-amber-500"}`}
          style={{ height: v < 0 ? 4 : Math.max(6, Math.round(v * 44)) }}
        />
      ))}
    </div>
  );
}

type ChipsProps = {
  voices: string[];
  active: string;
  onPick: (voice: string) => void;
  labels: { legend: string; other: string; name: string; placeholder: string; add: string };
};

/** «من يقرأ؟»: the family's voices, plus any name they type (never assumed). */
export function VoiceChips({ voices, active, onPick, labels }: ChipsProps) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const chip = (on: boolean) =>
    `min-h-11 rounded-full px-4 text-[15px] ${on ? "border-[1.5px] border-night-900 bg-night-900 font-bold text-paper" : "border-[1.5px] border-line bg-paper-raised text-ink"}`;
  const add = () => {
    const clean = name.trim().replace(/\s+/g, " ").slice(0, 30);
    if (clean) onPick(clean);
    setAdding(false);
    setName("");
  };
  return (
    <fieldset className="flex flex-col gap-1.5">
      <legend className="mb-1.5 text-small font-semibold">{labels.legend}</legend>
      <div className="flex flex-wrap gap-2">
        {voices.map((v) => (
          <button
            key={v}
            type="button"
            aria-pressed={v === active}
            onClick={() => onPick(v)}
            className={chip(v === active)}
          >
            {v}
          </button>
        ))}
        {!adding && (
          <button type="button" onClick={() => setAdding(true)} className={chip(false)}>
            {labels.other}
          </button>
        )}
      </div>
      {adding && (
        <div className="mt-1 flex gap-2">
          <label className="sr-only" htmlFor="voice-name">
            {labels.name}
          </label>
          <input
            id="voice-name"
            autoFocus
            maxLength={30}
            value={name}
            placeholder={labels.placeholder}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && add()}
            className="min-h-11 min-w-0 grow rounded-full border-[1.5px] border-line bg-paper-raised px-4 text-body"
          />
          <button type="button" onClick={add} className={chip(true)}>
            {labels.add}
          </button>
        </div>
      )}
    </fieldset>
  );
}
