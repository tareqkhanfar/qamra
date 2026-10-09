"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { nameCases } from "@/lib/arabicName";
import { companionAddOn, companionApi, companionImage, type Companion } from "@/lib/companion";
import type { Child, Line } from "@/lib/create";
import { money, type Catalog } from "@/lib/store";

/**
 * On the story step: the companion that goes into this book, and its price (the add-on is free in Magic and
 * +20₪ in Classic, from the catalog). The parent can change it, or add one when they skipped.
 */
export function CompanionSummary({
  child,
  line,
  catalog,
  companionId,
  onChange,
}: {
  child: Child;
  line: Line;
  catalog: Catalog | null;
  companionId: string | null;
  onChange: () => void;
}) {
  const t = useTranslations("companion.summary");
  const locale = useLocale();
  const [comp, setComp] = useState<Companion | null>(null);
  const offer = companionAddOn(catalog, line);

  useEffect(() => {
    if (!companionId) return;
    let alive = true;
    (async () => {
      const r = await companionApi.get(companionId);
      if (alive && r.ok) setComp(r.data);
    })();
    return () => {
      alive = false;
    };
  }, [companionId]);

  if (!offer) return null;
  const shown = companionId && comp?.id === companionId && comp.approved ? comp : null;
  const price = offer.free
    ? t("free")
    : offer.price
      ? `+${money(offer.price, catalog?.currency ?? "ILS", locale)}`
      : null;
  return (
    <div className="flex items-center gap-3 rounded-[20px] border-[1.5px] border-line bg-paper-raised p-2.5">
      <div className="flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-night-100">
        {shown ? (
          // eslint-disable-next-line @next/next/no-img-element -- private image through the API
          <img src={companionImage(shown.id)} alt="" className="max-h-full max-w-full object-contain" />
        ) : (
          <span aria-hidden="true" className="text-[26px]">
            ✎
          </span>
        )}
      </div>
      <div className="flex grow flex-col gap-0.5">
        <strong className="text-body">
          {shown ? t("with", { name: shown.name }) : t("none", { ...nameCases(child.name), gender: child.gender })}
        </strong>
        {shown && price && <span className="text-caption text-ink-muted">{price}</span>}
      </div>
      <button
        type="button"
        onClick={onChange}
        className="min-h-11 shrink-0 px-2 text-small font-semibold text-night-900 underline underline-offset-4"
      >
        {shown ? t("change") : t("add")}
      </button>
    </div>
  );
}
