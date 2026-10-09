"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { accusativeName } from "@/lib/arabicName";
import {
  COMPANION_TYPES,
  companionApi,
  drawingImage,
  TRAITS,
  type Companion,
  type CompanionType,
  type Trait,
} from "@/lib/companion";
import type { Child } from "@/lib/create";
import { SubFrame } from "./SubFrame";

/** Design CompName: the companion's name (the child knows it), what it is, and its nature (optional). */
export function CompanionName({
  child,
  companion,
  style,
  back,
  onDrawing,
}: {
  child: Child;
  companion: Companion;
  style: string | null;
  back: () => void;
  onDrawing: (c: Companion) => void;
}) {
  const t = useTranslations("companion.name");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [name, setName] = useState(companion.name);
  const [type, setType] = useState<CompanionType>(companion.type);
  const [other, setOther] = useState(companion.type_other ?? "");
  const [traits, setTraits] = useState<Trait[]>(companion.traits);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const who = { name: child.name, nameAcc: accusativeName(child.name), gender: child.gender };
  const shownName = name.trim() || t("placeholder");

  async function draw() {
    setBusy(true);
    setError(null);
    const r = await companionApi.draw(companion.id, {
      name: name.trim(),
      type,
      type_other: type === "other" ? other.trim() || undefined : undefined,
      traits,
      style: style ?? undefined,
    });
    setBusy(false);
    if (r.ok) onDrawing(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  const big = (on: boolean) =>
    `min-h-14 rounded-2xl text-body ${on ? "border-2 border-night-900 bg-night-100 font-bold text-night-900" : "border-[1.5px] border-line bg-paper-raised text-ink"}`;
  return (
    <SubFrame
      title={t("title")}
      back={back}
      footer={
        <Button variant="primary" size="lg" onClick={draw} loading={busy} disabled={!name.trim()}>
          {t("cta", { name: shownName })}
        </Button>
      }
    >
      <div className="flex justify-center pt-1">
        <div className="w-[170px] -rotate-3 overflow-hidden rounded-md bg-white shadow-[0_8px_20px_rgba(22,32,74,0.18)]">
          {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API, no-store */}
          <img src={drawingImage(companion.id, "cleaned")} alt={t("drawingAlt", who)} className="block w-full" />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="comp-name" className="text-body font-semibold">
          {t("label")}
        </label>
        <input
          id="comp-name"
          value={name}
          maxLength={30}
          autoComplete="off"
          onChange={(e) => setName(e.target.value)}
          placeholder={t("placeholder")}
          className="min-h-14 rounded-[14px] border-[1.5px] border-night-900 bg-white px-4 text-[18px] outline-none focus:ring-4 focus:ring-amber-100"
        />
        <span className="text-caption text-ink-muted">{t("ask", who)}</span>
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-body font-semibold">{t("typeLabel")}</legend>
        <div className="grid grid-cols-2 gap-2.5">
          {COMPANION_TYPES.map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={type === value}
              onClick={() => setType(value)}
              className={big(type === value)}
            >
              {t(`types.${value}`)}
            </button>
          ))}
        </div>
        {type === "other" && (
          <input
            aria-label={t("otherLabel")}
            value={other}
            maxLength={30}
            onChange={(e) => setOther(e.target.value)}
            placeholder={t("otherPlaceholder")}
            className="min-h-12 rounded-[14px] border-[1.5px] border-line bg-white px-4 text-body outline-none focus:border-night-900"
          />
        )}
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-body font-semibold">
          {t("traitsLabel")} <span className="font-normal text-ink-muted">{t("optional")}</span>
        </legend>
        <div className="flex flex-wrap gap-2">
          {TRAITS.map((trait) => {
            const on = traits.includes(trait);
            return (
              <button
                key={trait}
                type="button"
                aria-pressed={on}
                onClick={() => setTraits((l) => (on ? l.filter((x) => x !== trait) : [...l, trait]))}
                className={`min-h-11 rounded-full px-4 text-[15px] ${on ? "border-[1.5px] border-night-900 bg-night-900 font-semibold text-paper" : "border-[1.5px] border-line bg-paper-raised text-ink"}`}
              >
                {t(`traits.${trait}`)}
              </button>
            );
          })}
        </div>
      </fieldset>
      {error && <Alert>{error}</Alert>}
    </SubFrame>
  );
}
