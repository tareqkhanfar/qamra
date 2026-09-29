"use client";

import type { ReactNode } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Scene, fromArt, type SceneArt } from "@/components/art/Scene";
import { Link } from "@/i18n/navigation";

/** The back arrow of the designs: points right in Arabic, left in English. */
function Back({ label, href, onClick }: { label: string; href?: string; onClick?: () => void }) {
  const icon = (
    <svg
      className="size-[22px] ltr:-scale-x-100"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M5 12h14" />
      <path d="M13 6l6 6-6 6" />
    </svg>
  );
  const cls = "flex size-11 items-center justify-center text-night-900";
  return href ? (
    <Link href={href} aria-label={label} className={cls}>
      {icon}
    </Link>
  ) : (
    <button type="button" aria-label={label} onClick={onClick} className={cls}>
      {icon}
    </button>
  );
}

/** Header of the order screens (designs AddOns, Cart, Create10). */
export function FlowHeader({
  title,
  back,
  label,
  note,
  moon,
  progress,
}: {
  title: ReactNode;
  back: { label: string; href?: string; onClick?: () => void };
  label?: string;
  note?: string;
  moon?: number;
  progress?: number;
}) {
  if (!label) {
    return (
      <header className="flex h-[60px] items-center justify-between border-b border-line px-4">
        <Back {...back} />
        <strong className="text-[17px] text-ink">{title}</strong>
        <span className="w-11" />
      </header>
    );
  }
  return (
    <header className="flex flex-col gap-2.5 border-b border-line px-4 pt-1 pb-3.5">
      <div className="flex h-[52px] items-center justify-between">
        <Back {...back} />
        <strong className="truncate px-2 text-body text-ink">{title}</strong>
        <span className="w-11 shrink-0" />
      </div>
      <div className="flex justify-between text-caption">
        <strong className="text-night-900">{label}</strong>
        <span className="flex items-center gap-1.5 text-ink-muted">
          <MoonPhase p={moon ?? 0.9} className="size-[18px]" />
          {note}
        </span>
      </div>
      {progress !== undefined && (
        <div
          className="flex h-1.5 rounded-full bg-paper-sunk"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress * 100)}
          aria-label={note}
        >
          <div className="rounded-full bg-night-900" style={{ width: `${Math.round(progress * 100)}%` }} />
        </div>
      )}
    </header>
  );
}

/** The sticky bottom bar of the designs. */
export function BottomBar({ children, column = false }: { children: ReactNode; column?: boolean }) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-paper/[0.97] backdrop-blur-sm">
      <div
        className={`mx-auto flex max-w-[640px] px-4 pt-3 pb-[max(24px,env(safe-area-inset-bottom))] ${column ? "flex-col gap-1.5" : "items-center gap-3"}`}
      >
        {children}
      </div>
    </div>
  );
}

/** The amber call to action of the designs (a link or a button). */
export const ctaClass =
  "flex min-h-14 grow items-center justify-center gap-2 rounded-full bg-amber-500 px-5 text-[17px] font-bold text-night-950 transition hover:shadow-lamp active:bg-amber-600 disabled:cursor-not-allowed disabled:bg-paper-sunk disabled:text-ink-faint";

/** A book cover thumbnail with its dark spine, as in the designs. */
export function BookThumb({ art, hijab, size }: { art: SceneArt | null; hijab?: boolean; size: number }) {
  return (
    <div
      className="shrink-0 overflow-hidden rounded-[4px_10px_10px_4px] border-r-[5px] border-night-950 bg-night-900"
      style={{ width: size, height: size }}
    >
      {art && <Scene {...fromArt({ ...art, hijab: hijab ?? art.hijab })} kidScale={0.62} />}
    </div>
  );
}

const ICONS: Record<string, string> = {
  "hardcover-upgrade": "M4 5h12a3 3 0 0 1 3 3v11H7a3 3 0 0 1-3-3Z M4 16a3 3 0 0 1 3-3h12",
  "gift-box": "M4 10h16v10H4Z M3 7h18v3H3Z M12 7v13 M12 7c-2-4-6-3-5 0 M12 7c2-4 6-3 5 0",
  "extra-copy": "M8 4h11v14H8Z M5 7v13h11",
  "coloring-version": "M4 20l4-1 11-11-3-3L5 16Z M14 6l3 3",
  "cover-poster": "M5 3h14v18H5Z M8 16l3-4 2 3 2-2 2 3",
  "family-voice": "M12 3a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3Z M6 11a6 6 0 0 0 12 0 M12 17v4",
  express: "M13 3L5 13h6l-1 8 8-10h-6Z",
};
const STAR = "M12 3l2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.4 6.8 19.1l1-5.8L3.5 9.2l5.9-.8Z";

/** An add-on's picture in its 48 px tile (drawings are presentation; the add-on itself is admin data). */
export function AddOnIcon({ slug }: { slug: string }) {
  return (
    <span className="flex size-12 shrink-0 items-center justify-center rounded-[14px] bg-paper-sunk">
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#16204A"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d={ICONS[slug] ?? STAR} />
      </svg>
    </span>
  );
}

/** The square check of the designs (on: amber with ✓). */
export function CheckBox({ on, size = 26 }: { on: boolean; size?: number }) {
  return (
    <span
      aria-hidden="true"
      style={{ width: size, height: size }}
      className={`box-border flex shrink-0 items-center justify-center rounded-[8px] text-[14px] font-extrabold ${on ? "bg-amber-500 text-night-950" : "border-2 border-[#C9BCA3] bg-white text-transparent"}`}
    >
      ✓
    </span>
  );
}
