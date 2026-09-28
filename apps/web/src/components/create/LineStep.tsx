"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { Child, Line } from "@/lib/create";
import { money, type Catalog } from "@/lib/store";
import { Check, Frame, Lead } from "./Frame";

const PRODUCT: Record<Line, string> = { classic: "classic-book", magic: "magic-book" };

/** Step 4 (Addendum 4 §7): Classic and Magic side by side, Magic suggested gently. */
export function LineStep({
  child,
  catalog,
  initial,
  back,
  onDone,
}: {
  child: Child;
  catalog: Catalog | null;
  initial: Line | null;
  back: () => void;
  onDone: (line: Line) => void;
}) {
  const t = useTranslations("create");
  const tc = useTranslations("store.compare");
  const tf = useTranslations("store.formats");
  const locale = useLocale();
  const [line, setLine] = useState<Line>(initial ?? "magic");
  const currency = catalog?.currency ?? "ILS";

  return (
    <Frame
      title={t("bookOf", { name: child.name })}
      label={t("steps.line")}
      n={4}
      back={back}
      footer={
        <Button onClick={() => onDone(line)} size="lg" className="grow">
          {t("continue")}
        </Button>
      }
    >
      <Lead title={t("line.title", { name: child.name })} body={t("line.body")} />
      <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label={tc("title")}>
        {(["magic", "classic"] as const).map((value) => {
          const p = catalog?.products.find((x) => x.slug === PRODUCT[value]);
          const on = line === value;
          const best = value === "magic";
          return (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => setLine(value)}
              className={`relative flex flex-col gap-3 rounded-3xl p-4 text-start transition ${best ? "bg-night-900 text-paper" : "bg-paper-raised text-ink"} ${on ? "ring-[3px] ring-amber-500" : best ? "" : "border-[1.5px] border-line"}`}
            >
              {best && (
                <span className="absolute end-4 -top-2.5 rounded-full bg-amber-500 px-2.5 py-0.5 text-caption font-bold text-night-950">
                  {tc("best")}
                </span>
              )}
              <div className="flex items-center justify-between gap-2">
                <strong className={`font-display text-[20px] ${best ? "text-amber-300" : "text-night-900"}`}>
                  {locale === "ar" ? p?.name_ar : p?.name_en}
                </strong>
                <Check on={on} />
              </div>
              <p className={`text-small ${best ? "text-night-100" : "text-ink-muted"}`}>{tc(`${value}.tagline`)}</p>
              <ul className="flex flex-col gap-1.5 text-small">
                {(tc.raw(`${value}.points`) as string[]).map((point) => (
                  <li key={point} className="flex items-start gap-2">
                    <span aria-hidden="true" className={best ? "text-amber-300" : "text-success"}>
                      ✓
                    </span>
                    {point}
                  </li>
                ))}
              </ul>
              <div className="mt-auto flex flex-wrap gap-1.5 text-caption">
                {p?.variants.map((v) => (
                  <span
                    key={v.sku}
                    className={`rounded-full px-2.5 py-1 ${best ? "bg-night-800 text-night-100" : "bg-paper-sunk"}`}
                  >
                    {tf(v.options.format)} · {v.price ? money(v.price, currency, locale) : "—"}
                  </span>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    </Frame>
  );
}
