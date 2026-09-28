"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Link } from "@/i18n/navigation";
import { TOTAL_STEPS } from "@/lib/create";

/** One step of the create flow (design Create1–Create9): the header with the step count, then a sticky footer. */
export function Frame({
  title,
  label,
  n,
  back,
  footer,
  children,
}: {
  title: string;
  label: string;
  n: number;
  back?: () => void;
  footer?: ReactNode;
  children: ReactNode;
}) {
  const t = useTranslations("create");
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
      <header className="flex flex-col gap-2.5 border-b border-line px-4 pt-1 pb-3.5">
        <div className="flex h-[52px] items-center justify-between">
          <Link href="/account" aria-label={t("close")} className="flex size-11 items-center justify-center">
            <svg className="size-[22px]" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </Link>
          <strong className="text-body text-night-900">{title}</strong>
          <span className="w-11" />
        </div>
        <div className="flex justify-between text-caption">
          <strong className="text-night-900">{label}</strong>
          <span className="flex items-center gap-1.5 text-ink-muted">
            <MoonPhase p={n / TOTAL_STEPS} className="size-[18px]" />
            {t("stepOf", { n, total: TOTAL_STEPS })}
          </span>
        </div>
        <div
          className="flex h-1.5 rounded-full bg-paper-sunk"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={TOTAL_STEPS}
          aria-valuenow={n}
          aria-label={t("stepOf", { n, total: TOTAL_STEPS })}
        >
          <div className="rounded-full bg-night-900" style={{ width: `${Math.round((n / TOTAL_STEPS) * 100)}%` }} />
        </div>
      </header>
      <main className="flex flex-1 flex-col gap-6 px-4 pt-6 pb-36">{children}</main>
      {(back || footer) && (
        <div className="fixed inset-x-0 bottom-0 z-10 border-t border-line bg-paper/95 backdrop-blur-sm">
          <div className="mx-auto flex max-w-[640px] items-center gap-2 px-4 pt-3 pb-6">
            {back && (
              <button
                type="button"
                onClick={back}
                className="min-h-14 px-4 font-display text-body font-semibold text-night-900"
              >
                {t("back")}
              </button>
            )}
            {footer}
          </div>
        </div>
      )}
    </div>
  );
}

/** The step's heading block. */
export function Lead({ title, body }: { title: ReactNode; body?: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <h1 className="text-[26px] leading-snug text-night-900 md:text-h2">{title}</h1>
      {body && <p className="text-body text-ink-muted">{body}</p>}
    </div>
  );
}

/** A choice chip (ages, interests, redraw reasons). */
export function Chip({
  on,
  onClick,
  children,
  round = true,
  disabled,
}: {
  on: boolean;
  onClick: () => void;
  children: ReactNode;
  round?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      disabled={disabled}
      className={`min-h-11 min-w-12 px-4 text-small transition disabled:opacity-40 ${round ? "rounded-full" : "rounded-[14px] text-body"} ${on ? "border-2 border-night-900 bg-night-900 font-semibold text-paper" : "border-[1.5px] border-line bg-paper-raised text-ink"}`}
    >
      {children}
    </button>
  );
}

/** The selected-card check mark of the design. */
export function Check({ on }: { on: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`flex size-7 shrink-0 items-center justify-center rounded-full font-extrabold ${on ? "bg-amber-500 text-night-950" : "border-2 border-line text-transparent"}`}
    >
      ✓
    </span>
  );
}
