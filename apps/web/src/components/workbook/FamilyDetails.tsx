"use client";

import { useTranslations } from "next-intl";

/** The relations the book knows (the API's `RELATIONS`): the word it prints and the figure it draws. */
export const RELATIONS = [
  "mother",
  "father",
  "grandmother",
  "grandfather",
  "maternal-aunt",
  "paternal-aunt",
  "maternal-uncle",
  "paternal-uncle",
  "brother",
  "sister",
  "baby",
  "other",
] as const;
export type Relation = (typeof RELATIONS)[number];
const SCARF: readonly Relation[] = ["mother", "grandmother", "maternal-aunt", "paternal-aunt", "sister", "other"];
export const MAX_MEMBERS = 6; // A7 §7: what the book's pages hold

export type FamilyMember = { relation: Relation | ""; name: string; adult: boolean; scarf: boolean };
export type Family = { name: string; city: string; members: FamilyMember[] };
export const emptyFamily = (): Family => ({ name: "", city: "", members: [] });

/** What `POST /api/shop/workbooks/cart` gets as `family`, or undefined when the parent skipped it. */
export function familyPayload(f: Family) {
  const members = f.members
    .filter((m) => m.relation)
    .map((m) => ({
      relation: m.relation,
      name: m.name.trim(),
      ...(m.relation === "other" ? { adult: m.adult } : {}),
      scarf: SCARF.includes(m.relation as Relation) && m.scarf,
    }));
  if (!f.name.trim() && !f.city.trim() && !members.length) return undefined;
  return { name: f.name.trim(), city: f.city.trim(), members };
}

const field = "min-h-11 rounded-[12px] border-[1.5px] border-line bg-paper px-3 text-body text-ink";

/**
 * «مغامراتي مع عائلتي»: who is in the child's family, as the book will name them (A7 §7). Optional and
 * friendly: first names and relations only, never photos; skipped, the book has one neutral grown-up.
 */
export function FamilyDetails({ value, onChange }: { value: Family; onChange: (f: Family) => void }) {
  const t = useTranslations("workbook.family");
  const set = (patch: Partial<Family>) => onChange({ ...value, ...patch });
  const setMember = (i: number, patch: Partial<FamilyMember>) =>
    set({ members: value.members.map((m, k) => (k === i ? { ...m, ...patch } : m)) });
  return (
    <details className="rounded-[18px] border-[1.5px] border-line bg-paper-raised p-3">
      <summary className="min-h-11 cursor-pointer content-center font-bold text-night-900">{t("title")}</summary>
      <div className="mt-2 flex flex-col gap-3">
        <p className="text-small text-ink">{t("hint")}</p>
        <label className="flex flex-col gap-1 text-small font-semibold text-night-900">
          {t("name")}
          <input className={field} maxLength={30} value={value.name} onChange={(e) => set({ name: e.target.value })} />
        </label>
        <label className="flex flex-col gap-1 text-small font-semibold text-night-900">
          {t("city")}
          <input className={field} maxLength={30} value={value.city} onChange={(e) => set({ city: e.target.value })} />
        </label>
        {value.members.map((m, i) => (
          <fieldset key={i} className="flex flex-wrap items-end gap-2 rounded-[14px] bg-paper p-2">
            <legend className="sr-only">{t("member", { n: i + 1 })}</legend>
            <label className="flex min-w-[8rem] grow flex-col gap-1 text-small font-semibold text-night-900">
              {t("relation")}
              <select
                className={field}
                value={m.relation}
                onChange={(e) => setMember(i, { relation: e.target.value as Relation | "" })}
              >
                <option value="">{t("choose")}</option>
                {RELATIONS.map((r) => (
                  <option key={r} value={r}>
                    {t(`relations.${r}`)}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex min-w-[8rem] grow flex-col gap-1 text-small font-semibold text-night-900">
              {t("firstName")}
              <input
                className={field}
                maxLength={20}
                value={m.name}
                onChange={(e) => setMember(i, { name: e.target.value })}
              />
            </label>
            {m.relation === "other" && (
              <label className="flex flex-col gap-1 text-small font-semibold text-night-900">
                {t("age")}
                <select
                  className={field}
                  value={m.adult ? "adult" : "child"}
                  onChange={(e) => setMember(i, { adult: e.target.value === "adult" })}
                >
                  <option value="adult">{t("adult")}</option>
                  <option value="child">{t("child")}</option>
                </select>
              </label>
            )}
            {SCARF.includes(m.relation as Relation) && (
              <label className="flex min-h-11 items-center gap-2 text-small text-night-900">
                <input type="checkbox" checked={m.scarf} onChange={(e) => setMember(i, { scarf: e.target.checked })} />
                {t("scarf")}
              </label>
            )}
            <button
              type="button"
              aria-label={t("remove")}
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
            + {t("add")}
          </button>
        )}
        <p className="text-caption text-ink-faint">{t("privacy")}</p>
      </div>
    </details>
  );
}
