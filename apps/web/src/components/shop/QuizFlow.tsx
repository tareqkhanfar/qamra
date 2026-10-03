"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Alert } from "@/components/ui/Alert";
import { Link } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { pickHref, quizApi, type QuizAnswer, type QuizPick } from "@/lib/shop";
import { money } from "@/lib/store";

type Step = "age" | "goal" | "pen" | "result";
const AGES = [3, 4, 5, 6] as const; // 3 = "3 or younger", 6 = "6–7"
const GOALS = ["gift", "learn", "family", "faith"] as const;
const PENS = ["yes", "no"] as const;
const STEP_N: Record<Step, number> = { age: 0, goal: 1, pen: 2, result: 3 };

/**
 * «أي كتاب يناسب طفلي؟» (Addendum 9, design Quiz): age → goal → (for learning) holding a pen → the
 * recommendation and an alternative. The rules live in the database (Admin → الكتالوج); the API applies them.
 * The goal «تعليم ديني» shows only while «قلبي يعرف الله» has a volume on sale (`faith`, Addendum 10 §9).
 */
export function QuizFlow({ faith = false }: { faith?: boolean }) {
  const t = useTranslations("quiz");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [step, setStep] = useState<Step>("age");
  const [age, setAge] = useState<number>(5);
  const [answer, setAnswer] = useState<QuizAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function finish(g: (typeof GOALS)[number], pen: (typeof PENS)[number] | null) {
    setBusy(true);
    setError(null);
    const r = await quizApi.answer(age, g, pen);
    setBusy(false);
    if (!r.ok) {
      setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
      return;
    }
    setAnswer(r.data);
    setStep("result");
    window.scrollTo({ top: 0 });
  }

  const name = (p: QuizPick) => (locale === "ar" ? p.name_ar : p.name_en);
  const why = (p: QuizPick) => (locale === "ar" ? p.why_ar : p.why_en);
  const price = (p: QuizPick) =>
    p.from_price === null ? "" : t("from", { price: money(p.from_price, p.currency, locale) });
  const option =
    "flex min-h-16 w-full items-center justify-between gap-3 rounded-[18px] border-[1.5px] border-line bg-paper-raised px-5 text-start text-[18px] font-semibold text-night-900 transition hover:border-night-500 disabled:opacity-60";
  const back = (to: Step) => (
    <button
      type="button"
      onClick={() => setStep(to)}
      className="min-h-11 self-start px-2 text-[15px] font-semibold text-night-900"
    >
      {t("back")}
    </button>
  );

  return (
    <div className="mx-auto flex min-h-dvh max-w-[560px] flex-col">
      <header className="flex flex-col gap-2.5 border-b border-line px-4 pt-1 pb-3.5">
        <div className="flex h-[52px] items-center justify-between">
          <Link
            href="/shop"
            aria-label={t("close")}
            className="flex size-11 items-center justify-center text-night-900"
          >
            <svg
              className="size-[22px]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </Link>
          <strong className="text-body">{t("title")}</strong>
          <span className="w-11" />
        </div>
        <div className="flex items-center justify-between text-caption">
          <strong className="text-night-900">{t(`steps.${step}`)}</strong>
          <MoonPhase p={[0.15, 0.45, 0.7, 1][STEP_N[step]] ?? 1} className="size-[22px]" />
        </div>
      </header>
      <main className="flex flex-col gap-3.5 px-4 py-6">
        {error && <Alert>{error}</Alert>}
        {step === "age" && (
          <>
            <h1 className="text-[28px] text-night-900">{t("age.title")}</h1>
            {AGES.map((a) => (
              <button
                key={a}
                type="button"
                className={option}
                onClick={() => {
                  setAge(a);
                  setStep("goal");
                }}
              >
                {t(`age.${a}`)}
                <svg
                  className="size-5 shrink-0 text-amber-700 ltr:-scale-x-100"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M19 12H5" />
                  <path d="M11 6l-6 6 6 6" />
                </svg>
              </button>
            ))}
          </>
        )}
        {step === "goal" && (
          <>
            <h1 className="text-[28px] text-night-900">{t("goal.title")}</h1>
            {GOALS.filter((g) => g !== "faith" || faith).map((g) => (
              <button
                key={g}
                type="button"
                disabled={busy}
                className={`${option} min-h-[76px] flex-col items-start justify-center gap-0.5 py-3`}
                onClick={() => {
                  if (g === "learn") setStep("pen");
                  else void finish(g, null);
                }}
              >
                <strong className="text-[18px]">{t(`goal.${g}.label`)}</strong>
                <span className="text-small font-normal text-ink-muted">{t(`goal.${g}.hint`)}</span>
              </button>
            ))}
            {back("age")}
          </>
        )}
        {step === "pen" && (
          <>
            <h1 className="text-[28px] text-night-900">{t("pen.title")}</h1>
            <p className="text-[15px] text-ink-muted">{t("pen.body")}</p>
            {PENS.map((p) => (
              <button key={p} type="button" disabled={busy} className={option} onClick={() => void finish("learn", p)}>
                {t(`pen.${p}`)}
              </button>
            ))}
            {back("goal")}
          </>
        )}
        {step === "result" && answer && (
          <>
            <span className="self-start rounded-full bg-success-bg px-3 py-1.5 text-caption font-bold text-success">
              {t("result.badge")}
            </span>
            <div className="flex flex-col gap-2.5 rounded-[24px] bg-night-900 p-5 text-paper">
              <h1 className="text-[26px] leading-snug text-paper">{name(answer.product)}</h1>
              <p className="text-body leading-[1.7] text-night-100">{why(answer.product)}</p>
              <strong className="font-display text-[24px] text-amber-300">{price(answer.product)}</strong>
              {pickHref(answer.product) ? (
                <Link
                  href={pickHref(answer.product)!}
                  className="flex min-h-14 items-center justify-center rounded-full bg-amber-500 text-[17px] font-bold text-night-950"
                >
                  {t("result.see")}
                </Link>
              ) : (
                <Link
                  href="/shop"
                  className="flex min-h-14 items-center justify-center rounded-full bg-amber-500 text-[17px] font-bold text-night-950"
                >
                  {t("result.browse")}
                </Link>
              )}
            </div>
            <div className="flex flex-col gap-1 rounded-[20px] border border-line bg-paper-raised p-4">
              <span className="text-caption text-ink-muted">{t("result.also")}</span>
              {pickHref(answer.alternative) ? (
                <Link
                  href={pickHref(answer.alternative)!}
                  className="text-[17px] font-bold text-night-900 underline-offset-4 hover:underline"
                >
                  {name(answer.alternative)}
                </Link>
              ) : (
                <strong className="text-[17px] text-night-900">{name(answer.alternative)}</strong>
              )}
              <span className="text-small text-ink-muted">{why(answer.alternative)}</span>
            </div>
            <button
              type="button"
              onClick={() => {
                setAnswer(null);
                setStep("age");
              }}
              className="min-h-11 self-start px-2 text-[15px] font-bold text-amber-700 underline"
            >
              {t("result.restart")}
            </button>
          </>
        )}
      </main>
    </div>
  );
}
