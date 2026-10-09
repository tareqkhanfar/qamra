"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";
import { nameCases } from "@/lib/arabicName";
import type { Child } from "@/lib/create";
import { LIMITS, type CustomBrief, type FamilyMember } from "@/lib/customStory";
import { Chip } from "./Frame";

const OCCASIONS = ["birthday", "eid", "sibling", "school", "trip", "other"] as const;
const ROLES = ["mom", "dad", "grandma", "grandpa", "aunt", "uncle", "sister", "brother"] as const;
const input =
  "w-full rounded-[14px] border-[1.5px] bg-white px-4 text-body outline-none placeholder:text-ink-faint focus:border-night-900 focus:ring-4 focus:ring-night-100";

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-body font-semibold">{label}</span>
      {children}
      {hint && <span className={`text-caption ${error ? "text-danger" : "text-ink-muted"}`}>{hint}</span>}
    </div>
  );
}

/**
 * «حكاية خاصة» (Magic): a short guided brief. Family members are optional and named in the family's own words:
 * the form never assumes a mother and a father. The server checks the lengths and screens the words again.
 */
export function CustomStoryForm({
  child,
  value,
  onChange,
  bad,
}: {
  child: Child;
  value: CustomBrief;
  onChange: (b: CustomBrief) => void;
  bad: string[]; // fields the server sent back
}) {
  const t = useTranslations("customStory");
  const who = { ...nameCases(child.name), gender: child.gender };
  const set = (patch: Partial<CustomBrief>) => onChange({ ...value, ...patch });
  const border = (field: string) => (bad.includes(field) ? "border-danger" : "border-line");
  const person = (i: number, patch: Partial<FamilyMember>) =>
    set({ family: value.family.map((m, j) => (j === i ? { ...m, ...patch } : m)) });

  return (
    <section className="flex flex-col gap-5 rounded-3xl border border-line bg-paper-raised p-4" aria-label={t("title")}>
      <p className="text-small leading-relaxed text-ink-muted">{t("intro", who)}</p>
      <Field
        label={t("occasion")}
        error={bad.includes("occasion")}
        hint={bad.includes("occasion") ? t("fix") : undefined}
      >
        <div className="flex flex-wrap gap-2">
          {OCCASIONS.map((o) => (
            <Chip
              key={o}
              on={value.occasion === t(`occasions.${o}`)}
              onClick={() => set({ occasion: o === "other" ? "" : t(`occasions.${o}`) })}
            >
              {t(`occasions.${o}`)}
            </Chip>
          ))}
        </div>
        <input
          value={value.occasion}
          maxLength={LIMITS.short}
          onChange={(e) => set({ occasion: e.target.value })}
          placeholder={t("occasionPlaceholder")}
          aria-label={t("occasion")}
          className={`min-h-12 ${input} ${border("occasion")}`}
        />
      </Field>
      <Field label={t("place")} error={bad.includes("place")} hint={bad.includes("place") ? t("fix") : t("placeHint")}>
        <input
          value={value.place}
          maxLength={LIMITS.short}
          onChange={(e) => set({ place: e.target.value })}
          placeholder={t("placePlaceholder")}
          aria-label={t("place")}
          className={`min-h-12 ${input} ${border("place")}`}
        />
      </Field>
      <Field
        label={t("loves", who)}
        error={bad.includes("loves")}
        hint={bad.includes("loves") ? t("fix") : t("lovesHint")}
      >
        {value.loves.map((love, i) => (
          <input
            key={i}
            value={love}
            maxLength={LIMITS.short}
            onChange={(e) =>
              set({ loves: value.loves.map((x, j) => (j === i ? e.target.value : x)) as CustomBrief["loves"] })
            }
            placeholder={t(`lovesPlaceholder.${i}`)}
            aria-label={t("loveN", { n: i + 1 })}
            className={`min-h-12 ${input} ${border("loves")}`}
          />
        ))}
      </Field>
      <Field
        label={t("wish")}
        error={bad.includes("wish")}
        hint={bad.includes("wish") ? t("fix") : `${value.wish.length}/${LIMITS.wish}`}
      >
        <textarea
          rows={2}
          value={value.wish}
          maxLength={LIMITS.wish}
          onChange={(e) => set({ wish: e.target.value })}
          placeholder={t("wishPlaceholder", who)}
          aria-label={t("wish")}
          className={`py-3 ${input} ${border("wish")}`}
        />
      </Field>
      <Field
        label={t("family")}
        error={bad.includes("family")}
        hint={bad.includes("family") ? t("fix") : t("familyHint")}
      >
        {value.family.map((m, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              value={m.role}
              maxLength={LIMITS.role}
              list="qamra-family-roles"
              onChange={(e) => person(i, { role: e.target.value })}
              placeholder={t("rolePlaceholder")}
              aria-label={t("role", { n: i + 1 })}
              className={`min-h-12 flex-1 ${input} ${border("family")}`}
            />
            <input
              value={m.name}
              maxLength={LIMITS.name}
              onChange={(e) => person(i, { name: e.target.value })}
              placeholder={t("namePlaceholder")}
              aria-label={t("personName", { n: i + 1 })}
              className={`min-h-12 flex-1 ${input} ${border("family")}`}
            />
            <button
              type="button"
              aria-label={t("remove", { n: i + 1 })}
              onClick={() => set({ family: value.family.filter((_, j) => j !== i) })}
              className="flex size-11 shrink-0 items-center justify-center rounded-full text-ink-muted hover:bg-paper-sunk"
            >
              ✕
            </button>
          </div>
        ))}
        <datalist id="qamra-family-roles">
          {ROLES.map((r) => (
            <option key={r} value={t(`roles.${r}`)} />
          ))}
        </datalist>
        {value.family.length < LIMITS.family && (
          <button
            type="button"
            onClick={() => set({ family: [...value.family, { role: "", name: "" }] })}
            className="min-h-11 self-start rounded-full border-[1.5px] border-dashed border-amber-700 px-4 text-small font-semibold text-amber-700"
          >
            + {t("addPerson")}
          </button>
        )}
      </Field>
    </section>
  );
}
