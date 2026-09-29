"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { companionApi, drawingImage, optionImage, type Companion } from "@/lib/companion";
import type { Child } from "@/lib/create";
import { Check } from "../Frame";
import { SubFrame } from "./SubFrame";

const FREE_REDRAWS = 3;
const STAGES = ["bg-night-100", "bg-amber-100"];

/** Design CompChoose: 2 options, each beside the child's drawing; «هذا نونو!» or a new drawing (3 free). */
export function CompanionChoose({
  child,
  companion,
  back,
  onRedraw,
  onChosen,
  redrawError = null,
}: {
  child: Child;
  companion: Companion;
  back: () => void;
  onRedraw: () => void;
  onChosen: (c: Companion) => void;
  redrawError?: string | null; // a redraw the server refused (limits, network)
}) {
  const t = useTranslations("companion.choose");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [option, setOption] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const left = Math.min(FREE_REDRAWS, companion.redraws_left);
  const options = Array.from({ length: companion.options }, (_, n) => n);
  const version = companion.redraws_left; // a redraw brings new pictures under the same address

  async function choose() {
    setBusy(true);
    setError(null);
    const r = await companionApi.choose(companion.id, option);
    setBusy(false);
    if (r.ok) onChosen(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <SubFrame
      title={t("title", { name: companion.name })}
      back={back}
      footer={
        <>
          <Button variant="primary" size="lg" onClick={choose} loading={busy}>
            {t("cta", { name: companion.name })}
          </Button>
          <Button variant="secondary" size="md" onClick={onRedraw} disabled={!left || busy}>
            {left ? t("redraw", { left, total: FREE_REDRAWS }) : t("noRedraws")}
          </Button>
        </>
      }
    >
      <p className="text-body leading-relaxed text-ink-muted">
        {t("body", { name: companion.name, child: child.name, gender: child.gender })}
      </p>
      <div role="radiogroup" aria-label={t("title", { name: companion.name })} className="flex flex-col gap-3.5">
        {options.map((n) => {
          const on = option === n;
          return (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => setOption(n)}
              className={`relative flex flex-col gap-2 rounded-3xl bg-paper-raised p-3.5 text-start ${on ? "border-[3px] border-amber-500 shadow-lamp" : "border-[1.5px] border-line"}`}
            >
              <div className="flex items-center gap-2.5">
                <figure className="flex shrink-0 flex-col items-center gap-1">
                  <div className="w-24 overflow-hidden rounded-lg border border-line bg-white">
                    {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API */}
                    <img src={drawingImage(companion.id, "cleaned")} alt="" className="block w-full" />
                  </div>
                  <figcaption className="text-caption text-ink-muted">
                    {t("drawing", { gender: child.gender })}
                  </figcaption>
                </figure>
                <svg className="size-6 shrink-0 text-amber-700 rtl:-scale-x-100" viewBox="0 0 24 24" aria-hidden="true">
                  <g fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14" />
                    <path d="M13 6l6 6-6 6" />
                  </g>
                </svg>
                <div
                  className={`flex h-[180px] grow items-center justify-center overflow-hidden rounded-[18px] ${STAGES[n % 2]}`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API */}
                  <img
                    src={optionImage(companion.id, n, version)}
                    alt={t("optionAlt", { n: n + 1, name: companion.name })}
                    className="max-h-full max-w-full object-contain"
                  />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <strong className="text-body">{t(`option${n % 2}`)}</strong>
                <Check on={on} />
              </div>
            </button>
          );
        })}
      </div>
      {(error ?? redrawError) && <Alert>{error ?? redrawError}</Alert>}
    </SubFrame>
  );
}
