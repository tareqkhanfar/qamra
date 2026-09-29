"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { TOTAL_STEPS } from "@/lib/create";

/** The companion step's own screens are sub-steps of step 6 (design CompCrop, CompName, CompChoose): a compact
 * header with back, the screen's title and the step count, then a sticky footer. */
export const COMPANION_STEP = 6;

export function SubFrame({
  title,
  back,
  footer,
  children,
}: {
  title: string;
  back: () => void;
  footer?: ReactNode;
  children: ReactNode;
}) {
  const t = useTranslations("create");
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
      <header className="flex h-[60px] items-center gap-2 border-b border-line px-2">
        <button
          type="button"
          onClick={back}
          aria-label={t("back")}
          className="flex size-11 shrink-0 items-center justify-center text-night-900"
        >
          <svg className="size-[22px] rtl:-scale-x-100" viewBox="0 0 24 24" aria-hidden="true">
            <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5" />
              <path d="M11 6l-6 6 6 6" />
            </g>
          </svg>
        </button>
        <h1 className="grow text-[20px] leading-tight text-night-900">{title}</h1>
        <span className="flex shrink-0 items-center gap-1.5 pe-2 text-caption text-ink-muted">
          <MoonPhase p={COMPANION_STEP / TOTAL_STEPS} className="size-[18px]" />
          {t("stepOf", { n: COMPANION_STEP, total: TOTAL_STEPS })}
        </span>
      </header>
      <main className="flex flex-1 flex-col gap-4 px-4 pt-4 pb-40">{children}</main>
      {footer && (
        <div className="fixed inset-x-0 bottom-0 z-10 border-t border-line bg-paper/95 backdrop-blur-sm">
          <div className="mx-auto flex max-w-[640px] flex-col gap-2 px-4 pt-3 pb-6">{footer}</div>
        </div>
      )}
    </div>
  );
}
