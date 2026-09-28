"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Kid } from "@/components/art/Kid";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { createApi, type Character, type Child, type Line } from "@/lib/create";
import { money, type Catalog } from "@/lib/store";
import { Check, Frame, Lead } from "./Frame";

/** How each style's card hints at its look until real sample images are uploaded in the admin. */
const LOOK: Record<string, { bg: string; fx: string }> = {
  watercolor: {
    bg: "bg-[radial-gradient(circle_at_30%_30%,#CBC1EA_0,transparent_45%),radial-gradient(circle_at_70%_60%,#FCEFD2_0,transparent_50%),#F3EAD8]",
    fx: "saturate-[0.85]",
  },
  cartoon: { bg: "bg-[#E4E8F7]", fx: "saturate-[1.3] contrast-[1.1]" },
  "3d": {
    bg: "bg-[radial-gradient(circle_at_50%_35%,#FFFDF8_0,#DDEFE3_70%)]",
    fx: "drop-shadow-[0_8px_0_rgba(22,32,74,0.18)]",
  },
  "semi-realistic": { bg: "bg-[#F3EAD8]", fx: "saturate-[0.9] contrast-[1.05]" },
  coloring: { bg: "bg-white", fx: "grayscale contrast-[1.6]" },
};

/** Step 5 (design Create4): the art style, then the character is drawn right away. */
export function StyleStep({
  child,
  line,
  catalog,
  initial,
  back,
  onDrawing,
}: {
  child: Child;
  line: Line;
  catalog: Catalog | null;
  initial: string | null;
  back: () => void;
  onDrawing: (c: Character) => void;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const styles = (catalog?.styles ?? []).filter((s) => s.lines.includes(line));
  const [style, setStyle] = useState<string>(
    initial && styles.some((s) => s.slug === initial) ? initial : (styles[0]?.slug ?? "watercolor"),
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function draw() {
    setBusy(true);
    setError(null);
    const r = await createApi.draw(child.id, style);
    setBusy(false);
    if (r.ok) onDrawing(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <Frame
      title={t("bookOf", { name: child.name })}
      label={t("steps.style")}
      n={5}
      back={back}
      footer={
        <Button onClick={draw} loading={busy} size="lg" className="grow" disabled={!styles.length}>
          {t("style.cta", { name: child.name })}
        </Button>
      }
    >
      <Lead title={t("style.title", { name: child.name })} body={t("style.body")} />
      <div className="flex flex-col gap-3" role="radiogroup" aria-label={t("steps.style")}>
        {styles.map((s, i) => {
          const on = style === s.slug;
          const look = LOOK[s.slug] ?? LOOK.watercolor;
          const extra = Number(s.price_modifier) > 0;
          return (
            <button
              key={s.slug}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => setStyle(s.slug)}
              className={`relative flex gap-3.5 rounded-3xl bg-paper-raised p-3 text-start transition ${on ? "border-[3px] border-amber-500 shadow-[0_8px_24px_rgba(242,179,61,0.25)]" : "border-[1.5px] border-line"}`}
            >
              <div
                className={`flex h-[150px] w-[120px] shrink-0 items-end justify-center overflow-hidden rounded-2xl ${look.bg}`}
              >
                {s.sample_images[0] ? (
                  // eslint-disable-next-line @next/next/no-img-element -- admin-uploaded sample art
                  <img src={s.sample_images[0]} alt="" className="size-full object-cover" />
                ) : (
                  <div className={look.fx}>
                    <Kid
                      hijab={child.hijab}
                      hijabColor="#E9826B"
                      outfit="#F2B33D"
                      pose="wave"
                      className="h-auto w-[112px]"
                    />
                  </div>
                )}
              </div>
              <div className="flex grow flex-col gap-1.5 py-1">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-[20px] text-night-900">{locale === "ar" ? s.name_ar : s.name_en}</h2>
                  <Check on={on} />
                </div>
                <p className="text-small text-ink-muted">
                  {t.has(`style.desc.${s.slug}`) ? t(`style.desc.${s.slug}`) : ""}
                </p>
                <div className="mt-auto flex flex-wrap gap-1.5">
                  {i === 0 && (
                    <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-caption font-bold text-amber-700">
                      {t("style.popular")}
                    </span>
                  )}
                  {extra && (
                    <span className="rounded-full bg-paper-sunk px-2.5 py-0.5 text-caption font-semibold">
                      {t("style.extra", { amount: money(s.price_modifier, catalog?.currency ?? "ILS", locale) })}
                    </span>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
