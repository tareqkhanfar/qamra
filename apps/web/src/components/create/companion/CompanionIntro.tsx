"use client";

import { useLocale, useTranslations } from "next-intl";
import { Companion as CompanionArt } from "@/components/art/Companion";
import { Drawing } from "@/components/art/Drawing";
import { Button } from "@/components/ui/Button";
import { brandName } from "@/config/brand";
import { nameCases } from "@/lib/arabicName";
import { companionImage, type MyCompanion } from "@/lib/companion";
import type { Child } from "@/lib/create";
import { money, type Currency } from "@/lib/store";
import { Check, Frame } from "../Frame";
import { COMPANION_STEP } from "./SubFrame";

/** Design CompIntro: what the companion is, the child's companions from earlier books, and a clear skip. */
export function CompanionIntro({
  child,
  price,
  currency,
  mine,
  chosen,
  onPick,
  back,
  onStart,
  onUse,
  onSkip,
}: {
  child: Child;
  price: string | null; // null: included in this book (Magic)
  currency: Currency;
  mine: MyCompanion[];
  chosen: string | null;
  onPick: (id: string | null) => void;
  back: () => void;
  onStart: () => void;
  onUse: (id: string) => void;
  onSkip: () => void;
}) {
  const t = useTranslations("companion.intro");
  const tc = useTranslations("create");
  const locale = useLocale();
  const who = { ...nameCases(child.name), gender: child.gender };
  const picked = mine.find((c) => c.id === chosen) ?? null;
  const steps = ["one", "two", "three"] as const;

  return (
    <Frame
      title={tc("bookOf", who)}
      label={t("label", { gender: child.gender })}
      n={COMPANION_STEP}
      back={back}
      footer={
        <div className="flex grow flex-col gap-1.5">
          {picked ? (
            <Button variant="primary" size="lg" onClick={() => onUse(picked.id)}>
              {t("use", nameCases(picked.name))}
            </Button>
          ) : (
            <Button variant="primary" size="lg" onClick={onStart}>
              {t("start", who)}
            </Button>
          )}
          <Button variant="ghost" size="md" onClick={onSkip} className="no-underline">
            {t("skip")}
          </Button>
        </div>
      }
    >
      <section className="relative flex flex-col gap-4 overflow-hidden rounded-[28px] bg-night-900 px-[18px] py-[22px] text-paper">
        <span className="self-start rounded-full bg-amber-500 px-2.5 py-1 text-caption font-bold text-night-950">
          {t("badge", { brand: brandName(locale) })}
        </span>
        <h1 className="text-[30px] leading-tight text-paper">{t("title", who)}</h1>
        <div className="flex items-center justify-between">
          <figure className="flex flex-col items-center gap-1.5">
            <div className="w-[120px] rotate-[4deg] shadow-[0_6px_16px_rgba(0,0,0,0.35)]">
              <Drawing variant="cat" />
            </div>
            <figcaption className="text-caption text-night-100">{t("exampleDrawing")}</figcaption>
          </figure>
          <svg className="h-[30px] w-14 rtl:-scale-x-100" viewBox="0 0 56 30" fill="none" aria-hidden="true">
            <path d="M4 15 H48" stroke="#F2B33D" strokeWidth="3" strokeDasharray="2 7" strokeLinecap="round" />
            <path
              d="M40 6 L50 15 L40 24"
              stroke="#F2B33D"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <figure className="flex flex-col items-center gap-1.5">
            <div className="flex size-[130px] items-center justify-center rounded-[20px] bg-night-800">
              <CompanionArt variant="cat" pose="wave" className="block w-[120px]" />
            </div>
            <figcaption className="text-caption text-night-100">{t("exampleCompanion")}</figcaption>
          </figure>
        </div>
      </section>
      <ol className="flex flex-col gap-2.5">
        {steps.map((s, i) => (
          <li key={s} className="flex items-start gap-3">
            <span className="flex size-[30px] shrink-0 items-center justify-center rounded-[10px] bg-amber-100 font-bold text-amber-700">
              {i + 1}
            </span>
            <p className="text-[15px] leading-relaxed">{t(`steps.${s}`, who)}</p>
          </li>
        ))}
      </ol>
      <p className="text-caption leading-relaxed text-ink-muted">
        {price === null ? t("free") : t("paid", { amount: money(price, currency, locale) })}
      </p>
      {mine.length > 0 && (
        <section className="flex flex-col gap-2.5" aria-labelledby="my-companions">
          <h2 id="my-companions" className="text-[18px] text-night-900">
            {t("mine", who)}
          </h2>
          <div role="radiogroup" aria-labelledby="my-companions" className="grid grid-cols-2 gap-3">
            {mine.map((c) => {
              const on = c.id === chosen;
              return (
                <button
                  key={c.id}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  onClick={() => onPick(on ? null : c.id)}
                  className={`flex flex-col gap-2 rounded-[22px] bg-paper-raised p-2.5 text-start ${on ? "border-[3px] border-amber-500" : "border border-line"}`}
                >
                  <div className="flex h-[120px] items-center justify-center overflow-hidden rounded-2xl bg-night-100">
                    {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API */}
                    <img src={companionImage(c.id)} alt="" className="max-h-full max-w-full object-contain" />
                  </div>
                  <span className="flex items-center justify-between gap-2">
                    <strong className="font-display text-[18px] text-night-900">{c.name}</strong>
                    <Check on={on} />
                  </span>
                </button>
              );
            })}
          </div>
        </section>
      )}
      <div aria-hidden="true" className="h-12" /> {/* room above the taller footer (primary + skip) */}
    </Frame>
  );
}
