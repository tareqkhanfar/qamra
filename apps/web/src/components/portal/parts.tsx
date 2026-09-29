"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import type { Progress, Stage } from "@/lib/portal";

/** approved · photo · consent · waiting, as one bar (design PortalDashboard). */
export function StageBar({ stages }: { stages: Record<Stage, number> }) {
  const t = useTranslations("portal");
  const total = Math.max(
    1,
    Object.values(stages).reduce((a, b) => a + b, 0),
  );
  const seg = (n: number, color: string) => (
    <div className={color} style={{ width: `${Math.round((n / total) * 100)}%` }} />
  );
  const waiting = stages.not_invited + stages.invited;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex h-2.5 overflow-hidden rounded-full bg-paper-sunk">
        {seg(stages.approved, "bg-success")}
        {seg(stages.photo, "bg-lav-300")}
        {seg(stages.consent, "bg-night-500")}
      </div>
      <div className="flex flex-wrap gap-x-3.5 gap-y-1 text-caption text-ink-muted">
        <span>{t("stageShort.approved", { n: stages.approved })}</span>
        <span>{t("stageShort.photo", { n: stages.photo })}</span>
        <span>{t("stageShort.consent", { n: stages.consent })}</span>
        <span>{t("stageShort.waiting", { n: waiting })}</span>
      </div>
    </div>
  );
}

const CHIP: Record<string, string> = {
  not_invited: "bg-danger-bg text-danger",
  invited: "bg-amber-100 text-amber-700",
  consent: "bg-night-100 text-night-900",
  photo: "bg-lav-300/40 text-lav-700",
  approved: "bg-success-bg text-success",
  ready: "bg-amber-100 text-amber-700",
  drawing: "bg-night-100 text-night-900",
  waiting: "bg-paper-sunk text-ink-muted",
  failed: "bg-danger-bg text-danger",
};

export function Chip({ tone, children }: { tone: string; children: ReactNode }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-caption font-bold whitespace-nowrap ${CHIP[tone] ?? CHIP.waiting}`}
    >
      {children}
    </span>
  );
}

/** The four steps a parent goes through, as dots (design PortalInvite / ClassReady). */
export function Steps({ on, label }: { on: boolean[]; label: string }) {
  return (
    <div className="flex gap-1" role="img" aria-label={label}>
      {on.map((x, i) => (
        <span key={i} className={`h-2 w-7 rounded-full ${x ? "bg-night-900" : "bg-line"}`} />
      ))}
    </div>
  );
}

/** Batch progress (design PortalBatch): pictures, covers, then the print files. */
export function BatchProgress({ progress }: { progress: Progress }) {
  const t = useTranslations("portal");
  const parts = (["pages", "covers", "files"] as const).map((k) => ({ k, ...(progress[k] ?? { done: 0, total: 0 }) }));
  const done = parts.reduce((a, p) => a + p.done, 0);
  const total = Math.max(
    1,
    parts.reduce((a, p) => a + p.total, 0),
  );
  return (
    <section role="status" className="flex flex-col gap-3 rounded-lg border border-line bg-paper-raised p-4">
      <strong className="text-body">{t(`progress.${progress.stage ?? "queued"}`)}</strong>
      <div className="flex h-2.5 overflow-hidden rounded-full bg-paper-sunk">
        <div className="bg-amber-500 transition-all" style={{ width: `${Math.round((done / total) * 100)}%` }} />
      </div>
      <div className="flex flex-wrap gap-4 text-caption text-ink-muted">
        {parts.map((p) => (
          <span key={p.k}>{t(`progress.${p.k}Count`, { done: p.done, total: p.total })}</span>
        ))}
      </div>
    </section>
  );
}
