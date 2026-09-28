"use client";

import { useId, useState, type InputHTMLAttributes } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  label: string;
  hint?: string;
  error?: string;
  /** Mark invalid without a per-field message (the form shows one summary alert). */
  invalid?: boolean;
  /** Latin-only visible values (email, phone): typed LTR, still aligned with the RTL form. */
  ltr?: boolean;
  revealLabels?: { show: string; hide: string };
};

export function TextField({
  label,
  hint,
  error,
  invalid,
  ltr,
  revealLabels,
  type = "text",
  className = "",
  ...rest
}: Props) {
  const id = useId();
  const [revealed, setRevealed] = useState(false);
  const isPassword = type === "password";
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(" ") || undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-small text-ink font-semibold">
        {label}
      </label>
      <div className="relative">
        <input
          {...rest}
          id={id}
          type={isPassword && revealed ? "text" : type}
          dir={ltr ? "ltr" : undefined}
          aria-invalid={error || invalid ? true : undefined}
          aria-describedby={describedBy}
          className={[
            "bg-paper-raised text-body text-ink min-h-[52px] w-full rounded-sm border px-4 transition outline-none",
            "placeholder:text-ink-faint focus:border-amber-500 focus:ring-4 focus:ring-amber-100",
            ltr ? "rtl:text-right" : "",
            isPassword ? "pe-14" : "",
            error || invalid ? "border-danger focus:border-danger focus:ring-danger-bg" : "border-line",
            className,
          ].join(" ")}
        />
        {isPassword && revealLabels && (
          <button
            type="button"
            onClick={() => setRevealed((v) => !v)}
            aria-label={revealed ? revealLabels.hide : revealLabels.show}
            aria-pressed={revealed}
            className="text-ink-muted hover:text-ink absolute inset-y-0 end-1 my-auto inline-flex size-11 items-center justify-center rounded-full"
          >
            <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
              <path
                d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              />
              <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="2" />
              {revealed && <path d="M4 20 20 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />}
            </svg>
          </button>
        )}
      </div>
      {hint && !error && (
        <p id={`${id}-hint`} className="text-caption text-ink-muted font-medium">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-caption text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
