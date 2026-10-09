"use client";

import { useTranslations } from "next-intl";
import { ArrowForward, Button } from "@/components/ui/Button";
import {
  MAX_MEMBERS,
  RELATIONS,
  type Family,
  type FamilyMember,
  type Relation,
} from "@/components/workbook/FamilyDetails";
import { nameCases } from "@/lib/arabicName";
import type { Child } from "@/lib/create";
import { arabic, Hint } from "../EditChild";
import { Frame, Lead } from "../Frame";

/** The relations drawn with a head-scarf when the parent asks (the same list as FamilyDetails, which keeps it private). */
const SCARF: readonly Relation[] = ["mother", "grandmother", "maternal-aunt", "paternal-aunt", "sister", "other"];

const field = "min-h-12 w-full min-w-0 rounded-[12px] border-[1.5px] border-line bg-white px-3 text-body text-ink";

/**
 * «مغامراتي مع عائلتي» only (§c.7): who is in the child's family, as the book will name them. The family name,
 * the city and up to six members, each with why it is asked; all optional, and the step can be skipped (the
 * missions then say «أحد الكبار»). First names and relations only, never photos.
 */
export function FamilyStep({
  child,
  value,
  onChange,
  back,
  onDone,
  onSkip,
}: {
  child: Child;
  value: Family;
  onChange: (family: Family) => void;
  back: () => void;
  onDone: () => void;
  onSkip: () => void;
}) {
  const t = useTranslations("create");
  const tf = useTranslations("workbook.family");
  const set = (patch: Partial<Family>) => onChange({ ...value, ...patch });
  const setMember = (i: number, patch: Partial<FamilyMember>) =>
    set({ members: value.members.map((m, k) => (k === i ? { ...m, ...patch } : m)) });

  return (
    <Frame
      title={t("bookOf", nameCases(child.name))}
      label={t("steps.family")}
      back={back}
      footer={
        <Button onClick={onDone} size="lg" className="grow">
          {t("continue")} <ArrowForward />
        </Button>
      }
    >
      <Lead title={t("activity.family.title", nameCases(child.name))} body={t("activity.family.body")} />

      <div className="flex flex-col gap-1.5">
        <label htmlFor="family-name" className="text-body font-semibold">
          {t("activity.family.name")}
        </label>
        <Hint id="family-name-hint">
          {t.rich("activity.family.nameHint", { ...nameCases(child.name), ar: arabic })}
        </Hint>
        <input
          id="family-name"
          className={`${field} min-h-14 text-body-l`}
          maxLength={30}
          autoComplete="off"
          aria-describedby="family-name-hint"
          value={value.name}
          onChange={(e) => set({ name: e.target.value })}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="family-city" className="text-body font-semibold">
          {t("activity.family.city")}
        </label>
        <Hint id="family-city-hint">{t("activity.family.cityHint")}</Hint>
        <input
          id="family-city"
          className={`${field} min-h-14 text-body-l`}
          maxLength={30}
          autoComplete="off"
          aria-describedby="family-city-hint"
          value={value.city}
          onChange={(e) => set({ city: e.target.value })}
        />
      </div>

      <fieldset className="flex min-w-0 flex-col gap-3">
        <legend className="mb-1 text-body font-semibold">{t("activity.family.members")}</legend>
        {value.members.map((m, i) => (
          <fieldset
            key={i}
            className="flex min-w-0 flex-wrap items-end gap-2 rounded-[16px] border border-line bg-paper-raised p-3"
          >
            <legend className="sr-only">{tf("member", { n: i + 1 })}</legend>
            <label className="flex min-w-[8rem] grow flex-col gap-1 text-small font-semibold text-night-900">
              {tf("relation")}
              <select
                className={field}
                value={m.relation}
                onChange={(e) => setMember(i, { relation: e.target.value as Relation | "" })}
              >
                <option value="">{tf("choose")}</option>
                {RELATIONS.map((r) => (
                  <option key={r} value={r}>
                    {tf(`relations.${r}`)}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex min-w-[8rem] grow flex-col gap-1 text-small font-semibold text-night-900">
              {tf("firstName")}
              <input
                className={field}
                maxLength={20}
                autoComplete="off"
                value={m.name}
                onChange={(e) => setMember(i, { name: e.target.value })}
              />
            </label>
            {m.relation === "other" && (
              <label className="flex flex-col gap-1 text-small font-semibold text-night-900">
                {tf("age")}
                <select
                  className={field}
                  value={m.adult ? "adult" : "child"}
                  onChange={(e) => setMember(i, { adult: e.target.value === "adult" })}
                >
                  <option value="adult">{tf("adult")}</option>
                  <option value="child">{tf("child")}</option>
                </select>
              </label>
            )}
            {SCARF.includes(m.relation as Relation) && (
              <label className="flex min-h-11 items-center gap-2 text-small text-night-900">
                <input
                  type="checkbox"
                  className="size-5 accent-night-900"
                  checked={m.scarf}
                  onChange={(e) => setMember(i, { scarf: e.target.checked })}
                />
                {tf("scarf")}
              </label>
            )}
            <button
              type="button"
              aria-label={`${tf("remove")}: ${tf("member", { n: i + 1 })}`}
              onClick={() => set({ members: value.members.filter((_, k) => k !== i) })}
              className="min-h-11 min-w-11 rounded-full text-small font-bold text-night-900 hover:bg-paper-sunk"
            >
              ✕
            </button>
          </fieldset>
        ))}
        {value.members.length < MAX_MEMBERS && (
          <button
            type="button"
            onClick={() => set({ members: [...value.members, { relation: "", name: "", adult: true, scarf: false }] })}
            className="min-h-11 self-start rounded-full border-[1.5px] border-line px-4 text-small font-bold text-night-900 hover:border-night-500"
          >
            + {tf("add")}
          </button>
        )}
        <Hint>{tf("privacy")}</Hint>
      </fieldset>

      <div className="flex flex-col items-start gap-1 border-t border-dashed border-line pt-4">
        <button
          type="button"
          onClick={onSkip}
          className="min-h-11 font-display text-body font-bold text-night-900 underline underline-offset-4"
        >
          {t("activity.family.skip")}
        </button>
        <Hint>{t.rich("activity.family.skipHint", { ar: arabic })}</Hint>
      </div>
    </Frame>
  );
}
