"use client";

import { useTranslations } from "next-intl";
import { VARIANTS, type ExampleVariant } from "@/lib/examples";

/** Girl / girl with hijab / boy: which published example the viewer shows. Looks without one are disabled. */
export function VariantSwitch({
  value,
  available,
  onChange,
  tone = "light",
}: {
  value: ExampleVariant;
  available: ExampleVariant[];
  onChange: (v: ExampleVariant) => void;
  tone?: "light" | "dark";
}) {
  const t = useTranslations("examples");
  return (
    <div
      role="radiogroup"
      aria-label={t("variant.label")}
      className={`inline-flex rounded-full p-1 ${tone === "dark" ? "bg-night-800" : "border border-line bg-paper-raised"}`}
    >
      {VARIANTS.map((v) => {
        const on = v === value;
        const ok = available.includes(v);
        return (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={on}
            aria-disabled={!ok}
            title={ok ? undefined : t("variant.other")}
            onClick={() => ok && onChange(v)}
            className={`min-h-11 rounded-full px-3.5 text-small font-semibold whitespace-nowrap transition ${
              on
                ? "bg-night-900 text-paper"
                : ok
                  ? tone === "dark"
                    ? "text-night-100 hover:text-paper"
                    : "text-night-900 hover:bg-paper-sunk"
                  : "cursor-not-allowed text-ink-faint"
            }`}
          >
            {t(`variant.${v}`)}
          </button>
        );
      })}
    </div>
  );
}
