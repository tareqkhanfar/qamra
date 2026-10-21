"use client";

import { useTranslations } from "next-intl";
import { useId, useState } from "react";
import { ArrowForward, Button } from "@/components/ui/Button";
import { nameCases } from "@/lib/arabicName";
import { characterImage, type Child } from "@/lib/create";
import { Frame, Lead } from "../Frame";

/**
 * «الغلاف» (2026-10-21): «دفاتر التلوين والرسم» put the child's character on the cover only when the parent wants
 * it. The name is printed either way. A child with a ready character: with it (the default) or without; a child
 * without one: a cover without a character (the default, the fast way) or a new drawing from a photo (the usual
 * consent, photo, style and character steps follow). `onDone(true)`: with the character.
 */
export function CoverStep({
  child,
  readyId,
  initial,
  back,
  onDone,
}: {
  child: Child;
  /** The approved character the book would reuse (null: none in a style this book takes). */
  readyId: string | null;
  /** The choice made before (the URL's `cover`), else null: the default. */
  initial: boolean | null;
  back: () => void;
  onDone: (withCharacter: boolean) => void;
}) {
  const t = useTranslations("create");
  const id = useId();
  const [value, setValue] = useState<boolean>(initial ?? !!readyId);
  const who = { ...nameCases(child.name), gender: child.gender };
  const ready = !!readyId;
  const options: { on: boolean; label: string; hint: string }[] = [
    {
      on: true,
      label: t(ready ? "activity.cover.withReady" : "activity.cover.draw", who),
      hint: t(ready ? "activity.cover.withReadyHint" : "activity.cover.drawHint", who),
    },
    {
      on: false,
      label: t(ready ? "activity.cover.without" : "activity.cover.plain"),
      hint: t(ready ? "activity.cover.withoutHint" : "activity.cover.plainHint", who),
    },
  ];
  if (!ready) options.reverse(); // the fast way first when nothing is drawn yet

  return (
    <Frame
      title={t("bookOf", who)}
      label={t("steps.cover")}
      back={back}
      footer={
        <Button onClick={() => onDone(value)} variant="primary" size="lg" className="grow">
          {t("continue")} <ArrowForward />
        </Button>
      }
    >
      <Lead title={t("activity.cover.title", who)} body={t("activity.cover.body", who)} />
      <fieldset className="flex flex-col gap-3">
        <legend className="sr-only">{t("activity.cover.title", who)}</legend>
        {options.map((o) => {
          const checked = value === o.on;
          return (
            <label
              key={String(o.on)}
              className={`flex cursor-pointer items-center gap-3 rounded-2xl p-4 ${checked ? "border-2 border-night-900 bg-night-100" : "border-[1.5px] border-line bg-paper-raised"}`}
            >
              <input
                type="radio"
                name={`${id}-cover`}
                checked={checked}
                onChange={() => setValue(o.on)}
                aria-describedby={`${id}-${String(o.on)}`}
                className="size-6 shrink-0 accent-night-900"
              />
              <span className="flex min-w-0 grow flex-col gap-1">
                <span className="text-body font-semibold text-night-900">{o.label}</span>
                <span id={`${id}-${String(o.on)}`} className="text-small text-ink-muted">
                  {o.hint}
                </span>
              </span>
              {o.on && readyId && (
                // eslint-disable-next-line @next/next/no-img-element -- private image through the API, no-store
                <img
                  src={characterImage(readyId)}
                  alt={t("activity.cover.alt", who)}
                  className="h-[72px] w-[96px] shrink-0 rounded-xl bg-white object-contain"
                />
              )}
            </label>
          );
        })}
      </fieldset>
      <p className="rounded-2xl bg-paper-sunk p-4 text-small text-ink">{t("activity.cover.note", who)}</p>
    </Frame>
  );
}
