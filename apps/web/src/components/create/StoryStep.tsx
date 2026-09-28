"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Scene, fromArt } from "@/components/art/Scene";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import type { ThemeCard } from "@/lib/catalog";
import { createApi, type Book, type Character, type Child, type Line } from "@/lib/create";
import { money, type Catalog } from "@/lib/store";
import { Check, Frame, Lead } from "./Frame";

/** Step 7 (design Create6): the story world, stories for the child's age first, and an optional dedication. */
export function StoryStep({
  child,
  character,
  line,
  themes,
  catalog,
  initial,
  back,
  onStarted,
}: {
  child: Child;
  character: Character;
  line: Line;
  themes: ThemeCard[];
  catalog: Catalog | null;
  initial: string | null;
  back: () => void;
  onStarted: (book: Book) => void;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const fits = (th: ThemeCard) => th.age_min <= child.age && child.age <= th.age_max;
  const list = themes.filter((th) => th.status === "available").sort((a, b) => Number(fits(b)) - Number(fits(a)));
  const [theme, setTheme] = useState<string | null>(
    initial && list.some((th) => th.slug === initial) ? initial : (list[0]?.slug ?? null),
  );
  const [dedication, setDedication] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const page = catalog?.addons.find((a) => a.slug === "dedication-page");

  async function start() {
    if (!theme) return;
    setBusy(true);
    setError(null);
    const r = await createApi.startBook({
      child_id: child.id,
      character_id: character.id,
      theme,
      line,
      dedication: dedication.trim() || undefined,
    });
    setBusy(false);
    if (r.ok) onStarted(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <Frame
      title={t("bookOf", { name: child.name })}
      label={t("steps.story")}
      n={7}
      back={back}
      footer={
        <Button onClick={start} loading={busy} size="lg" className="grow" disabled={!theme}>
          {t("story.cta")}
        </Button>
      }
    >
      <Lead title={t("story.title", { name: child.name, gender: child.gender })} body={t("story.body")} />
      <div className="flex flex-col gap-3" role="radiogroup" aria-label={t("steps.story")}>
        {list.map((th) => {
          const on = theme === th.slug;
          return (
            <button
              key={th.slug}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => setTheme(th.slug)}
              className={`flex items-center gap-3 rounded-[20px] bg-paper-raised p-2.5 text-start ${on ? "border-[3px] border-amber-500" : "border-[1.5px] border-line"}`}
            >
              <div className="w-[104px] shrink-0 overflow-hidden rounded-2xl">
                <Scene {...fromArt({ ...th.art, hijab: child.hijab })} ratio={1} kidScale={th.art.kid_scale ?? 0.72} />
              </div>
              <div className="flex grow flex-col gap-1">
                {fits(th) && (
                  <span className="self-start rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-700">
                    {t("story.suggested", { name: child.name })}
                  </span>
                )}
                <h2 className="text-[18px] leading-snug text-night-900">{th.title.replace("{name}", child.name)}</h2>
                <p className="text-caption text-ink-muted">
                  {th.tagline} · {t("story.pages", { pages: th.pages })}
                </p>
              </div>
              <Check on={on} />
            </button>
          );
        })}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="dedication" className="flex flex-wrap items-baseline justify-between gap-2">
          <span className="text-body font-semibold">
            {t("story.dedication")} <span className="font-normal text-ink-muted">{t("child.optional")}</span>
          </span>
          <span className="text-caption text-ink-muted">
            {line === "magic"
              ? t("story.dedicationFree")
              : page?.price
                ? t("story.dedicationPaid", { amount: money(page.price, catalog?.currency ?? "ILS", locale) })
                : null}
          </span>
        </label>
        <textarea
          id="dedication"
          rows={2}
          maxLength={120}
          value={dedication}
          placeholder={t("story.dedicationPlaceholder")}
          onChange={(e) => setDedication(e.target.value)}
          className="rounded-[14px] border-[1.5px] border-line bg-white px-4 py-3 text-body outline-none placeholder:text-ink-faint focus:border-night-900 focus:ring-4 focus:ring-night-100"
        />
      </div>
      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
