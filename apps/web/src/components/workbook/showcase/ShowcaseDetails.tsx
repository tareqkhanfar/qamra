"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";
import type { Line, PartCopy, ShowcaseCopy } from "./copy";

const ICONS: Record<string, ReactNode> = {
  topics: <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5zM4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5" />,
  skills: <path d="M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z" />,
  personal: (
    <path d="M12 21s-7.5-4.6-9.3-9.5C1.4 7.9 3.6 4.5 7 4.5c2 0 3.6 1.1 5 3 1.4-1.9 3-3 5-3 3.4 0 5.6 3.4 4.3 7-1.8 4.9-9.3 9.5-9.3 9.5z" />
  ),
  included: (
    <path d="M4 9h16v12H4zM2.5 5.5h19V9h-19zM12 5.5V21M12 5.5C10.5 2.5 7 2.5 7 4.3S10 5.5 12 5.5zm0 0c1.5-3 5-3 5-1.2s-3 1.2-5 1.2z" />
  ),
};

function Icon({ name }: { name: string }) {
  return (
    <svg
      className="size-[18px] shrink-0"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name]}
    </svg>
  );
}

function List({ name, title, items, say }: { name: string; title: string; items: Line[]; say: (l: Line) => string }) {
  if (!items.length) return null;
  return (
    <div className="flex flex-col gap-2">
      <h3 className="flex items-center gap-2 text-[16px] text-night-900">
        <span className="flex size-8 items-center justify-center rounded-full bg-amber-100 text-amber-700">
          <Icon name={name} />
        </span>
        {title}
      </h3>
      <ul className="flex flex-col gap-1.5 ps-1 text-[15px] leading-[1.6]">
        {items.map((item) => (
          <li key={item.en} className="flex items-start gap-2">
            <span aria-hidden="true" className="mt-[3px] text-[13px] font-extrabold text-success">
              ✓
            </span>
            <span>{say(item)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * What the picked part is about, from its content (components/workbook/showcase/copy.ts): one warm line, its
 * age, pages and weeks, what the child learns and gains, what is made for them and what else the book holds. A
 * set says what is in each of its books.
 */
export function ShowcaseDetails({
  copy,
  partName,
  title,
  className = "",
}: {
  copy: ShowcaseCopy;
  partName: (key: string) => string;
  title: string;
  className?: string;
}) {
  const t = useTranslations("workbookShowcase");
  const locale = useLocale();
  const say = (l: Line) => (locale === "ar" ? l.ar : l.en);
  const chip = "rounded-full px-3 py-1 text-caption font-semibold";
  const part: PartCopy | null = copy.kind === "part" ? copy.part : null;
  const pages = part ? part.pages : copy.kind === "set" ? copy.parts.reduce((n, p) => n + p.copy.pages, 0) : 0;
  const age = part ? part.age : copy.kind === "set" ? copy.set.age : null;
  return (
    <section
      aria-labelledby="about-part"
      className={`mx-4 flex flex-col gap-4 rounded-[20px] border border-line bg-paper-raised p-4 md:mx-0 md:p-5 ${className}`}
    >
      <div className="flex flex-col gap-2">
        <h2 id="about-part" className="text-[20px] leading-snug text-night-900" aria-live="polite">
          {title}
        </h2>
        <p className="border-s-4 border-amber-500 ps-3 text-[16px] leading-[1.75] text-night-900">
          {say(copy.kind === "part" ? copy.part.pitch : copy.set.pitch)}
        </p>
        <div className="flex flex-wrap gap-2">
          {age && <span className={`${chip} bg-night-100 text-night-900`}>{say(age)}</span>}
          {pages > 0 && <span className={`${chip} bg-paper-sunk text-night-900`}>{t("pages", { count: pages })}</span>}
          {part?.weeks ? (
            <span className={`${chip} bg-success-bg text-success`}>{t("weeks", { count: part.weeks })}</span>
          ) : null}
          {copy.kind === "set" && (
            <span className={`${chip} bg-success-bg text-success`}>{t("parts", { count: copy.parts.length })}</span>
          )}
        </div>
      </div>

      {part ? (
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-1 lg:grid-cols-2">
          <List name="topics" title={t("topics")} items={part.topics} say={say} />
          <List name="skills" title={t("skills")} items={part.skills} say={say} />
          <List name="personal" title={t("personal")} items={part.personal} say={say} />
          <List name="included" title={t("included")} items={part.included} say={say} />
        </div>
      ) : copy.kind === "set" ? (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <h3 className="text-[16px] text-night-900">{t("inEach")}</h3>
            <ol className="flex flex-col gap-2">
              {copy.parts.map((p) => (
                <li key={p.key} className="flex flex-col gap-0.5 rounded-[14px] bg-paper-sunk px-3 py-2.5">
                  <span className="flex flex-wrap items-baseline justify-between gap-x-3 text-[15px] font-bold text-night-900">
                    {partName(p.key)}
                    <span className="text-caption font-semibold text-ink-muted">
                      {t("pages", { count: p.copy.pages })}
                    </span>
                  </span>
                  <span className="text-[14px] leading-[1.6] text-ink-muted">{say(p.copy.short)}</span>
                </li>
              ))}
            </ol>
          </div>
          <List name="included" title={t("included")} items={copy.set.included} say={say} />
        </div>
      ) : null}
    </section>
  );
}
