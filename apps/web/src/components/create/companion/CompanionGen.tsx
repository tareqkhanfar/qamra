"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Button } from "@/components/ui/Button";
import { companionApi, drawingImage, type Companion } from "@/lib/companion";
import type { Child } from "@/lib/create";

const POLL_MS = 3000;
const TURN_MS = 1800;
const PHASES = [0.2, 0.35, 0.5, 0.65, 0.8, 0.95];

/** Design CompGen: the moon waxes while the 2 options are drawn; a failed drawing says why, gently. */
export function CompanionGen({
  child,
  companion,
  onChange,
  onRetry,
  onNewDrawing,
  onSkip,
  retryError = null,
}: {
  child: Child;
  companion: Companion;
  onChange: (c: Companion) => void;
  onRetry: () => void;
  onNewDrawing: () => void;
  onSkip: () => void;
  retryError?: string | null; // a retry the server refused (limits, network)
}) {
  const t = useTranslations("companion.gen");
  const locale = useLocale();
  const [i, setI] = useState(0);
  const failed = companion.status === "failed";
  const messages = t.raw("messages") as string[];

  useEffect(() => {
    if (failed) return;
    const turn = setInterval(() => setI((n) => n + 1), TURN_MS);
    const poll = setInterval(async () => {
      const r = await companionApi.get(companion.id);
      if (r.ok && r.data.status !== "generating") onChange(r.data);
    }, POLL_MS);
    return () => {
      clearInterval(turn);
      clearInterval(poll);
    };
  }, [failed, companion.id, onChange]);

  const rejected = companion.error?.code === "drawing_rejected";
  const reason = companion.error ? (locale === "ar" ? companion.error.ar : companion.error.en) : t("failed");
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col items-center gap-6 bg-night-900 px-4 pt-6 pb-8 text-paper">
      <div className="flex w-full justify-start">
        <button
          type="button"
          onClick={onSkip}
          className="min-h-11 font-semibold text-night-100 underline-offset-4 hover:underline"
        >
          {t("skip")}
        </button>
      </div>
      <div className="relative mt-2 flex size-[300px] items-center justify-center">
        <div className="absolute inset-0 rounded-full bg-[radial-gradient(circle,rgba(242,179,61,0.35),transparent_65%)] motion-safe:animate-pulse" />
        <MoonPhase p={failed ? 0.1 : PHASES[i % PHASES.length]} lit="#FCEFD2" dark="#22306A" className="size-[260px]" />
        <div className="absolute -bottom-1.5 -left-1.5 w-[110px] -rotate-6 overflow-hidden rounded-md bg-white shadow-[0_8px_20px_rgba(0,0,0,0.35)]">
          {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API, no-store */}
          <img src={drawingImage(companion.id, "cleaned")} alt="" className="block w-full" />
        </div>
      </div>
      <div role="status" aria-live="polite" className="flex flex-col items-center gap-2.5 text-center">
        <h1 className="text-[30px] text-paper">{failed ? t("failedTitle") : t("title", { name: companion.name })}</h1>
        {failed ? (
          <p className="max-w-sm text-body text-night-100">{retryError ?? reason}</p>
        ) : (
          <>
            <p className="min-h-7 font-display text-[19px] font-semibold text-amber-300">
              {messages[i % messages.length].replace("{child}", child.name)}
            </p>
            <p className="text-small text-night-100">{t("closer", { name: companion.name })}</p>
          </>
        )}
      </div>
      {failed ? (
        <div className="mt-auto flex w-full flex-col gap-2">
          {!rejected && (
            <Button variant="primary" size="lg" onClick={onRetry}>
              {t("retry")}
            </Button>
          )}
          <Button
            variant={rejected ? "primary" : "secondary"}
            size="lg"
            onClick={onNewDrawing}
            className={rejected ? "" : "border-paper text-paper hover:bg-night-800"}
          >
            {t("newDrawing")}
          </Button>
        </div>
      ) : (
        <div className="mt-auto flex w-full items-center gap-3 rounded-[20px] bg-night-800 p-4">
          <svg className="size-6 shrink-0 text-amber-300" viewBox="0 0 24 24" aria-hidden="true">
            <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 2" />
            </g>
          </svg>
          <p className="text-small leading-relaxed text-night-100">{t("time")}</p>
        </div>
      )}
    </div>
  );
}
