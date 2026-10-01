import type { ReactNode } from "react";
import { Link } from "@/i18n/navigation";

/** Small layout pieces the public pages share (home, activity books, pricing, how it works). */

export const SECTION = "mx-auto w-full max-w-[1440px] px-4 md:px-10 xl:px-24";

export function Eyebrow({ children, dark }: { children: ReactNode; dark?: boolean }) {
  return <span className={`text-[15px] font-bold ${dark ? "text-amber-300" : "text-amber-700"}`}>{children}</span>;
}

export function Arrow({ className = "size-4" }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={`inline-block shrink-0 align-[-0.15em] rtl:-scale-x-100 ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M5 12h14" />
      <path d="M13 6l6 6-6 6" />
    </svg>
  );
}

/** Section title with an optional eyebrow, lead and a "see all" link at the end. */
export function SectionHead({
  eyebrow,
  title,
  lead,
  more,
  center,
  dark,
  id,
}: {
  eyebrow?: string;
  title: string;
  lead?: string;
  more?: { href: string; label: string };
  center?: boolean;
  dark?: boolean;
  id?: string;
}) {
  return (
    <div
      className={`flex flex-wrap items-end justify-between gap-x-3 gap-y-1 ${center ? "md:justify-center md:text-center" : ""}`}
    >
      <div className={`flex flex-col gap-2 ${center ? "md:items-center" : ""}`}>
        {eyebrow && <Eyebrow dark={dark}>{eyebrow}</Eyebrow>}
        <h2 id={id} className={`text-[26px] leading-tight md:text-[40px] ${dark ? "text-paper" : "text-night-900"}`}>
          {title}
        </h2>
        {lead && (
          <p className={`max-w-[640px] text-[15px] md:text-[17px] ${dark ? "text-night-100" : "text-ink-muted"}`}>
            {lead}
          </p>
        )}
      </div>
      {more && (
        <Link
          href={more.href}
          className={`flex min-h-11 shrink-0 items-center gap-1 font-bold ${dark ? "text-amber-300" : "text-amber-700"}`}
        >
          {more.label} <Arrow />
        </Link>
      )}
    </div>
  );
}

export type Step = { title: string; body: string };

/** Numbered steps as cards; `visuals[i]` (optional) sits above the words. */
export function Steps({ steps, visuals = [], dark }: { steps: Step[]; visuals?: ReactNode[]; dark?: boolean }) {
  const cols = steps.length >= 5 ? "lg:grid-cols-5" : steps.length === 4 ? "lg:grid-cols-4" : "md:grid-cols-3";
  return (
    <ol className={`grid gap-4 sm:grid-cols-2 ${cols} md:gap-6`}>
      {steps.map((s, i) => (
        <li
          key={s.title}
          data-reveal
          style={{ "--d": `${i * 100}ms` } as React.CSSProperties}
          className={`flex flex-col overflow-hidden rounded-[20px] ${dark ? "bg-night-800" : "border border-line bg-paper-raised"}`}
        >
          {visuals[i] && (
            <div className="relative flex aspect-[16/10] items-center justify-center overflow-hidden bg-paper-sunk">
              {visuals[i]}
            </div>
          )}
          <div className="flex flex-col gap-1.5 p-5">
            <span
              className={`flex size-10 items-center justify-center rounded-[12px] font-display text-xl font-extrabold ${dark ? "bg-amber-500 text-night-950" : "bg-night-900 text-amber-500"}`}
            >
              {i + 1}
            </span>
            <h3 className={`text-[19px] md:text-[21px] ${dark ? "text-paper" : "text-night-900"}`}>{s.title}</h3>
            <p className={`text-[15px] leading-[1.7] ${dark ? "text-ink-dark-muted" : "text-ink-muted"}`}>{s.body}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

export type QA = { q: string; a: string };

export function Faq({ items, openFirst = true }: { items: QA[]; openFirst?: boolean }) {
  return (
    <div className="flex flex-col gap-3">
      {items.map((f, i) => (
        <details
          key={f.q}
          open={openFirst && i === 0}
          className="group rounded-lg border border-line bg-paper-raised px-4 md:px-6"
        >
          <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-3 text-body font-bold text-night-900 md:min-h-[60px] md:text-[18px] [&::-webkit-details-marker]:hidden">
            {f.q}
            <svg
              className="size-5 shrink-0 text-amber-700 transition group-open:rotate-180"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </summary>
          <p className="pb-4 text-[15px] leading-[1.75] text-ink-muted md:pb-5 md:text-body">{f.a}</p>
        </details>
      ))}
    </div>
  );
}

/** The closing band: one title, one line, the two things a parent can do next. */
export function CtaBand({
  title,
  body,
  primary,
  secondary,
}: {
  title: string;
  body: string;
  primary: { href: string; label: string };
  secondary: { href: string; label: string };
}) {
  return (
    <section className="mx-4 flex flex-col items-center gap-4 rounded-[24px] bg-night-900 px-6 py-10 text-center text-paper md:mx-10 md:rounded-[32px] md:py-14 xl:mx-24 2xl:mx-auto 2xl:max-w-[1248px]">
      <h2 className="text-[28px] leading-tight md:text-[40px]">{title}</h2>
      <p className="max-w-[560px] text-[15px] text-night-100 md:text-body-l">{body}</p>
      <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
        <Link
          href={primary.href}
          className="flex min-h-14 items-center justify-center rounded-full bg-amber-500 px-8 text-[17px] font-bold text-night-950"
        >
          {primary.label}
        </Link>
        <Link
          href={secondary.href}
          className="flex min-h-14 items-center justify-center rounded-full border-2 border-night-500 px-8 text-[17px] font-semibold text-paper hover:bg-night-800"
        >
          {secondary.label}
        </Link>
      </div>
    </section>
  );
}
