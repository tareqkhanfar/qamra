"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { ExampleImage } from "@/components/book/ExampleImage";
import { LineCards, LineChecklist } from "@/components/story/Choices";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import type { ThemeCard } from "@/lib/catalog";
import { classicStyles, classicVariant } from "@/lib/classic";
import type { Child, Line } from "@/lib/create";
import { pickExample, storyPages, variantOf, type Example } from "@/lib/examples";
import type { Catalog } from "@/lib/store";
import { LINES, offer, type Offer } from "@/lib/story";
import { Frame, Lead } from "./Frame";

/**
 * Step 4 (Addendum 9, as on the story page): Classic («الأكثر طلباً») and Magic («الأفخم») side by side, with
 * real pages of a published example in the child's look, the chosen line's checklist, and Classic suggested
 * first wherever a Classic template exists for this child.
 */
export function LineStep({
  child,
  catalog,
  themes,
  theme,
  initial,
  back,
  onDone,
}: {
  child: Child;
  catalog: Catalog | null;
  themes: ThemeCard[];
  theme: string | null;
  initial: Line | null;
  back: () => void;
  onDone: (line: Line) => void;
}) {
  const t = useTranslations("create");
  const tv = useTranslations("examples.variant");
  const locale = useLocale();
  const [examples, setExamples] = useState<Example[]>([]);
  useEffect(() => {
    let alive = true;
    void (async () => {
      let r = await api<Example[]>(`/api/examples?lang=${locale}`);
      if (r.ok && !r.data.length && locale !== "ar") r = await api<Example[]>("/api/examples?lang=ar");
      if (alive && r.ok) setExamples(r.data);
    })();
    return () => {
      alive = false;
    };
  }, [locale]);

  // Classic needs a live template for this child's look (in the chosen story, else in any); older APIs don't say
  const known = themes.some((th) => th.classic !== undefined);
  const classicOk = !known || classicStyles(themes, classicVariant(child), theme).size > 0;
  const offers = LINES.map((l) => offer(catalog, l))
    .filter((o): o is Offer => o !== null)
    .map((o) => (o.line === "classic" ? { ...o, available: o.available && classicOk } : o));
  const recommended: Line = offers.some((o) => o.line === "classic" && o.available) ? "classic" : "magic";
  const [picked, setPicked] = useState<Line | null>(initial);
  const line = offers.some((o) => o.line === picked && o.available) ? (picked as Line) : recommended;

  const look = variantOf(child);
  const example = pickExample(examples, theme ?? examples[0]?.theme, look);
  const pages = storyPages(example, 6);
  const strip = storyPages(example, 3, 1);

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
      <Lead title={t("line.title", { name: child.name })} body={t("line.lead")} />
      <LineCards
        offers={offers}
        value={line}
        onChange={setPicked}
        currency={catalog?.currency ?? "ILS"}
        pages={{ classic: pages[0], magic: pages[3] ?? pages[1] }}
      />
      <LineChecklist line={line} catalog={catalog} />
      {example && strip.length > 0 && (
        <section aria-labelledby="line-pages" className="flex flex-col gap-2">
          <h2 id="line-pages" className="text-body font-semibold text-night-900">
            {t("line.realPages", { look: tv(example.variant) })}
          </h2>
          <div className="grid grid-cols-3 gap-2">
            {strip.map((p) => (
              <div key={p.beat} className="relative aspect-square overflow-hidden rounded-xl bg-paper-sunk">
                <ExampleImage
                  page={p}
                  alt={p.text ?? ""}
                  sizes="120px"
                  className="absolute inset-0 size-full object-cover"
                />
              </div>
            ))}
          </div>
          <p className="text-caption text-ink-muted">
            {line === "classic"
              ? t("line.classicPages", { name: child.name })
              : t("line.magicPages", { name: child.name })}
          </p>
        </section>
      )}
    </Frame>
  );
}
