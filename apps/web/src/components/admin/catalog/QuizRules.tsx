"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";

type Ref = {
  slug: string;
  options: Record<string, string>;
  title_ar: string;
  title_en: string;
  why_ar: string;
  why_en: string;
};
type Rule = {
  goal: "gift" | "learn" | "family";
  age_min: number | null;
  age_max: number | null;
  pen: "yes" | "no" | null;
  product: Ref;
  alternative: Ref;
};
type Rules = { rules: Rule[]; saved: boolean };

const blankRef = (): Ref => ({ slug: "stories", options: {}, title_ar: "", title_en: "", why_ar: "", why_en: "" });
const optionsText = (o: Record<string, string>) =>
  Object.entries(o)
    .map(([k, v]) => `${k}=${v}`)
    .join(", ");
const parseOptions = (text: string): Record<string, string> =>
  Object.fromEntries(
    text
      .split(",")
      .map((p) => p.split("=").map((x) => x.trim()))
      .filter(([k, v]) => k && v),
  );
const field =
  "min-h-11 rounded-sm border-[1.5px] border-line bg-white px-3 text-small outline-none focus:border-night-900";

/** Admin → الكتالوج → «أسئلة الاختيار» (Addendum 9 §1.3): the quiz's rules, in order (permission: prices). */
export function QuizRules({ products }: { products: { slug: string; name: string }[] }) {
  const t = useTranslations("quiz.admin");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [data, setData] = useState<Rules | null>(null);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void (async () => {
      const r = await api<Rules>("/api/admin/quiz-rules");
      if (r.ok) setData(r.data);
      else setMessage({ tone: "error", text: errorText(r.error, locale, te("unknown")) });
    })();
  }, [locale, te]);

  if (!data) return message ? <Alert>{message.text}</Alert> : null;
  const rules = data.rules;
  const set = (next: Rule[]) => setData({ ...data, rules: next });
  const update = (i: number, patch: Partial<Rule>) => set(rules.map((r, n) => (n === i ? { ...r, ...patch } : r)));
  const move = (i: number, d: number) => {
    const next = [...rules];
    const [r] = next.splice(i, 1);
    next.splice(i + d, 0, r!);
    set(next);
  };

  async function save() {
    setBusy(true);
    setMessage(null);
    const r = await api<Rules>("/api/admin/quiz-rules", { method: "PUT", json: { rules } });
    setBusy(false);
    if (r.ok) {
      setData(r.data);
      setMessage({ tone: "success", text: t("saved") });
    } else {
      const gaps = (r.error?.details?.answers as { age: number; goal: string; pen: string | null }[] | undefined) ?? [];
      const detail = gaps.map((g) => `${t(`goals.${g.goal}`)} · ${g.age}${g.pen ? ` · ${t(`pens.${g.pen}`)}` : ""}`);
      setMessage({ tone: "error", text: [errorText(r.error, locale, te("unknown")), ...detail].join(" — ") });
    }
  }

  function refEditor(ref: Ref, onChange: (r: Ref) => void, label: string) {
    return (
      <fieldset className="flex flex-col gap-2 rounded-md border border-line p-3">
        <legend className="px-1 text-caption font-bold text-ink-muted">{label}</legend>
        <div className="flex flex-wrap gap-2">
          <select value={ref.slug} onChange={(e) => onChange({ ...ref, slug: e.target.value })} className={field}>
            <option value="stories">{t("stories")}</option>
            {products.map((p) => (
              <option key={p.slug} value={p.slug}>
                {p.name}
              </option>
            ))}
          </select>
          <input
            key={optionsText(ref.options)} // re-read after a move or a removal (the field is uncontrolled)
            aria-label={t("options")}
            placeholder={t("options")}
            defaultValue={optionsText(ref.options)}
            onBlur={(e) => onChange({ ...ref, options: parseOptions(e.target.value) })}
            className={`${field} w-44`}
            dir="ltr"
          />
        </div>
        <details>
          <summary className="min-h-11 cursor-pointer content-center text-caption font-semibold text-night-700">
            {t("titleAr")} · {t("whyAr")}
          </summary>
          <div className="grid gap-2 pt-1 sm:grid-cols-2">
            {(["title_ar", "why_ar", "title_en", "why_en"] as const).map((k) => (
              <input
                key={k}
                aria-label={t(
                  k === "title_ar" ? "titleAr" : k === "why_ar" ? "whyAr" : k === "title_en" ? "titleEn" : "whyEn",
                )}
                placeholder={t(
                  k === "title_ar" ? "titleAr" : k === "why_ar" ? "whyAr" : k === "title_en" ? "titleEn" : "whyEn",
                )}
                value={ref[k]}
                onChange={(e) => onChange({ ...ref, [k]: e.target.value })}
                dir={k.endsWith("_en") ? "ltr" : "rtl"}
                className={field}
              />
            ))}
          </div>
        </details>
      </fieldset>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-3xl text-small text-ink-muted">{t("intro")}</p>
      {!data.saved && <Alert tone="info">{t("seed")}</Alert>}
      {message && <Alert tone={message.tone}>{message.text}</Alert>}
      <ol className="flex flex-col gap-3">
        {rules.map((rule, i) => (
          <li key={i} className="flex flex-col gap-3 rounded-lg border border-line bg-paper-raised p-4">
            <div className="flex flex-wrap items-end gap-2">
              <strong className="me-2 text-small text-night-900">{t("rule", { n: i + 1 })}</strong>
              <label className="flex flex-col gap-1 text-caption text-ink-muted">
                {t("goal")}
                <select
                  value={rule.goal}
                  onChange={(e) => update(i, { goal: e.target.value as Rule["goal"] })}
                  className={field}
                >
                  {(["gift", "learn", "family"] as const).map((g) => (
                    <option key={g} value={g}>
                      {t(`goals.${g}`)}
                    </option>
                  ))}
                </select>
              </label>
              {(["age_min", "age_max"] as const).map((k) => (
                <label key={k} className="flex flex-col gap-1 text-caption text-ink-muted">
                  {t(k === "age_min" ? "ageMin" : "ageMax")}
                  <input
                    type="number"
                    min={2}
                    max={8}
                    value={rule[k] ?? ""}
                    onChange={(e) => update(i, { [k]: e.target.value === "" ? null : Number(e.target.value) })}
                    className={`${field} w-20`}
                    dir="ltr"
                  />
                </label>
              ))}
              <label className="flex flex-col gap-1 text-caption text-ink-muted">
                {t("pen")}
                <select
                  value={rule.pen ?? "any"}
                  onChange={(e) =>
                    update(i, { pen: e.target.value === "any" ? null : (e.target.value as "yes" | "no") })
                  }
                  className={field}
                >
                  {(["any", "yes", "no"] as const).map((p) => (
                    <option key={p} value={p}>
                      {t(`pens.${p}`)}
                    </option>
                  ))}
                </select>
              </label>
              <span className="ms-auto flex gap-1">
                <Button variant="ghost" size="sm" disabled={i === 0} onClick={() => move(i, -1)}>
                  {t("up")}
                </Button>
                <Button variant="ghost" size="sm" disabled={i === rules.length - 1} onClick={() => move(i, 1)}>
                  {t("down")}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => set(rules.filter((_, n) => n !== i))}>
                  {t("remove")}
                </Button>
              </span>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {refEditor(rule.product, (product) => update(i, { product }), t("product"))}
              {refEditor(rule.alternative, (alternative) => update(i, { alternative }), t("alternative"))}
            </div>
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          onClick={() =>
            set([
              ...rules,
              { goal: "gift", age_min: null, age_max: null, pen: null, product: blankRef(), alternative: blankRef() },
            ])
          }
        >
          {t("add")}
        </Button>
        <Button onClick={() => void save()} loading={busy}>
          {t("save")}
        </Button>
      </div>
    </div>
  );
}
