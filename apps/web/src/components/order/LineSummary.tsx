"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import type { FamilyFact, Part, Summary } from "@/lib/variantSummary";

/** The words of a summary's part: its message under `orderPath.line`, or its text. */
export function useSummaryText(): (part: Part) => string {
  const t = useTranslations("orderPath.line");
  return (p) => ("text" in p ? p.text : t.has(p.key) ? t(p.key, p.values) : (p.fallback ?? ""));
}

/**
 * A line as the cart, the checkout and the order page show it (lib/variantSummary.ts): the title with the child's
 * name as printed, the variant in one line, then one short line per fact (the English name, the family, the
 * story, the dedication).
 */
export function LineText({
  summary,
  qty = 1,
  extra = [],
  className = "",
  children,
}: {
  summary: Summary;
  qty?: number;
  extra?: (string | null)[]; // more details after the variant's (pages, a free digital copy…)
  className?: string;
  children?: ReactNode; // the line's state (preview ready, what it still needs)
}) {
  const text = useSummaryText();
  const details = [...summary.details.map(text), ...extra].filter(Boolean).join(" · ");
  return (
    <div className={`flex min-w-0 flex-col gap-0.5 ${className}`}>
      <strong className="text-body text-ink">
        {text(summary.title)}
        {qty > 1 && <span className="text-ink-muted"> × {qty}</span>}
      </strong>
      {details && <span className="text-caption text-ink-muted">{details}</span>}
      {summary.facts.map((f, i) => (
        <span key={i} className="text-caption text-ink">
          {text(f)}
        </span>
      ))}
      {summary.family && <Family family={summary.family} />}
      {children}
    </div>
  );
}

/** «مغامراتي مع عائلتي»: the family as the book prints it, or the neutral grown-up when no names were given. */
function Family({ family }: { family: FamilyFact }) {
  const t = useTranslations("orderPath.line.family");
  const ar = useLocale() === "ar";
  const comma = ar ? "، " : ", ";
  const who = family.members
    .map((m) => {
      const known = m.relation !== "other" && t.has(`relation.${m.relation}`);
      const relation = known ? t(`relation.${m.relation}`) : t("relation.other");
      if (!m.name) return relation;
      return known || !ar ? t("member", { relation, name: m.name }) : m.name; // «فرد من العائلة سامي» reads badly
    })
    .join(comma);
  return (
    <>
      <span className="text-caption text-ink">
        {who ? t("with", { name: family.name, members: who }) : t("alone", { name: family.name })}
      </span>
      {family.city && <span className="text-caption text-ink">{t("city", { city: family.city })}</span>}
    </>
  );
}
