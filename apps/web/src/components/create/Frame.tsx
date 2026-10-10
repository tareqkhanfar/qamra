"use client";

import { useTranslations } from "next-intl";
import { createContext, useContext, type ReactNode } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Alert } from "@/components/ui/Alert";
import { Link } from "@/i18n/navigation";

/**
 * What the wizard tells every step's header: the product's title («دوسية ضحى», «كتاب ضحى») and the real
 * «الخطوة n من N» of this product's flow for this child (lib/flows.ts). The steps never count themselves.
 * `notice`: a short note the flow shows at the top of the step (e.g. the photo's new position was saved).
 */
export type FlowFrame = { title: string; n: number; total: number; close?: string; notice?: string };
export const FlowFrameContext = createContext<FlowFrame | null>(null);
export const useFlowFrame = () => useContext(FlowFrameContext);

/** «الخطوة n من N» with its moon (the header of Frame and the companion's SubFrame). */
export function StepCount({ n, total }: { n: number; total: number }) {
  const t = useTranslations("create");
  return (
    <span className="flex shrink-0 items-center gap-1.5 text-ink-muted">
      <MoonPhase p={total ? n / total : 0} className="size-[18px]" />
      {t("stepOf", { n, total })}
    </span>
  );
}

/**
 * One step of the create flow (design Create1–Create9): the header with the step count, then a sticky footer.
 * Inside the wizard the title and the count come from the flow (`FlowFrameContext`); `title`, `n` and `total`
 * are used only outside it.
 */
export function Frame({
  title,
  label,
  n,
  total,
  back,
  footer,
  children,
}: {
  title: string;
  label: string;
  n?: number;
  total?: number;
  back?: () => void;
  footer?: ReactNode;
  children: ReactNode;
}) {
  const t = useTranslations("create");
  const flow = useFlowFrame();
  const count = flow ?? (n && total ? { n, total } : null);
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-paper">
      <header className="flex flex-col gap-2.5 border-b border-line px-4 pt-1 pb-3.5">
        <div className="flex h-[52px] items-center justify-between">
          <Link
            href={flow?.close ?? "/account"}
            aria-label={t("close")}
            className="flex size-11 items-center justify-center"
          >
            <svg className="size-[22px]" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </Link>
          <strong className="truncate px-2 text-body text-night-900">{flow?.title ?? title}</strong>
          <span className="w-11 shrink-0" />
        </div>
        <div className="flex justify-between gap-3 text-caption">
          <strong className="text-night-900">{label}</strong>
          {count && <StepCount n={count.n} total={count.total} />}
        </div>
        {count && (
          <div
            className="flex h-1.5 rounded-full bg-paper-sunk"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={count.total}
            aria-valuenow={count.n}
            aria-label={t("stepOf", count)}
          >
            <div
              className="rounded-full bg-night-900 transition-[width]"
              style={{ width: `${Math.round((count.n / count.total) * 100)}%` }}
            />
          </div>
        )}
      </header>
      <main className="flex flex-1 flex-col gap-6 px-4 pt-6 pb-36">
        {flow?.notice && <Alert tone="success">{flow.notice}</Alert>}
        {children}
      </main>
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
