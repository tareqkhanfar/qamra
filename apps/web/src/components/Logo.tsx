import { brandName } from "@/config/brand";

/** Logo option A «هلال على صفحة» (design/logo). The wordmark is live text until outlined files exist. */
export function MoonMark({ className = "size-9", tone = "light" }: { className?: string; tone?: "light" | "dark" }) {
  const ink = tone === "light" ? "#16204A" : "#FFFDF8";
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden="true">
      <path d="M21.32 5.01 A17 17 0 1 0 38.12 27.41 A14 14 0 0 1 21.32 5.01 Z" fill="#F2B33D" />
      <path
        d="M34 8 C34.6 11.2 35.8 12.4 39 13 C35.8 13.6 34.6 14.8 34 18 C33.4 14.8 32.2 13.6 29 13 C32.2 12.4 33.4 11.2 34 8 Z"
        fill={ink}
      />
      <path d="M6 44 Q15 39.5 24 43.5 Q33 39.5 42 44" fill="none" stroke={ink} strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({ locale }: { locale: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <MoonMark />
      <span className="font-display text-h3 font-extrabold text-night-900">{brandName(locale)}</span>
    </span>
  );
}
