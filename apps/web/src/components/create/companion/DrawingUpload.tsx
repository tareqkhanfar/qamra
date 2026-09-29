"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Drawing } from "@/components/art/Drawing";
import { Spinner } from "@/components/ui/Button";

/**
 * Design CompUpload: photograph the drawing (camera first, gallery as a fallback). Reusable: it only hands the
 * chosen file to `onFile` (the create flow uploads it; the kindergarten invite flow can do the same).
 * The phone's own camera opens through the file input, so the photo never leaves the device before the upload.
 */
export function DrawingUpload({
  back,
  onFile,
  busy,
  error,
}: {
  back: () => void;
  onFile: (file: File) => void;
  busy: boolean;
  error: string | null;
}) {
  const t = useTranslations("companion.upload");
  const tc = useTranslations("create");
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);
  const shown = useRef<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(
    () => () => {
      if (shown.current) URL.revokeObjectURL(shown.current);
    },
    [],
  );

  function picked(file: File | undefined) {
    if (!file) return;
    if (shown.current) URL.revokeObjectURL(shown.current);
    shown.current = URL.createObjectURL(file);
    setPreview(shown.current);
    onFile(file);
  }

  const tips = ["paper", "light", "shadow"] as const;
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[640px] flex-col bg-night-950 text-paper">
      <header className="flex h-[60px] items-center justify-between px-2">
        <button
          type="button"
          onClick={back}
          aria-label={tc("back")}
          className="flex size-11 items-center justify-center"
        >
          <svg className="size-[22px] rtl:-scale-x-100" viewBox="0 0 24 24" aria-hidden="true">
            <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5" />
              <path d="M11 6l-6 6 6 6" />
            </g>
          </svg>
        </button>
        <strong className="text-body">{t("title")}</strong>
        <span className="w-11" />
      </header>

      <div className="relative mx-4 flex h-[440px] items-center justify-center overflow-hidden rounded-[20px] bg-[repeating-linear-gradient(90deg,#7A6750_0_18px,#705E48_18px_36px)]">
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element -- a local preview of the parent's own photo
          <img src={preview} alt={t("preview")} className="max-h-full max-w-full object-contain" />
        ) : (
          <div className="w-[270px] -rotate-3 shadow-[0_10px_24px_rgba(0,0,0,0.35)]">
            <Drawing variant="blob" />
          </div>
        )}
        <svg className="pointer-events-none absolute inset-0 size-full" viewBox="0 0 358 440" aria-hidden="true">
          <path
            d="M34 70 V40 H64 M294 40 H324 V70 M324 370 V400 H294 M64 400 H34 V370"
            fill="none"
            stroke="#F2B33D"
            strokeWidth="5"
            strokeLinecap="round"
          />
        </svg>
        <span
          role="status"
          className="absolute inset-x-3.5 bottom-3.5 flex items-center gap-2 rounded-[14px] bg-night-950/85 px-3 py-2.5 text-small"
        >
          {busy ? <Spinner /> : <span className="size-2.5 rounded-full bg-[#7FD1A1]" aria-hidden="true" />}
          {busy ? t("cleaning") : t("frame")}
        </span>
      </div>

      <ul className="flex flex-wrap gap-2 p-4" aria-label={t("tipsLabel")}>
        {tips.map((tip) => (
          <li key={tip} className="flex items-center gap-1.5 rounded-full bg-night-800 px-3 py-2 text-caption">
            <span className="font-bold text-[#7FD1A1]" aria-hidden="true">
              ✓
            </span>
            {t(`tips.${tip}`)}
          </li>
        ))}
      </ul>
      {error && (
        <p role="alert" className="mx-4 rounded-2xl bg-danger-bg px-4 py-3 text-small text-danger">
          {error}
        </p>
      )}

      <div className="mt-auto flex items-center justify-between px-8 pt-2 pb-9">
        <button
          type="button"
          onClick={() => gallery.current?.click()}
          disabled={busy}
          aria-label={t("gallery")}
          className="flex size-[52px] items-center justify-center rounded-[14px] border-2 border-paper bg-night-800 disabled:opacity-40"
        >
          <svg className="size-6" viewBox="0 0 24 24" aria-hidden="true">
            <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <circle cx="9" cy="10" r="2" />
              <path d="M21 16l-5-5-9 9" />
            </g>
          </svg>
        </button>
        <button
          type="button"
          onClick={() => camera.current?.click()}
          disabled={busy}
          aria-label={t("shoot")}
          className="flex size-20 items-center justify-center rounded-full border-[5px] border-paper disabled:opacity-40"
        >
          <span className="size-[62px] rounded-full bg-amber-500" />
        </button>
        <span className="w-[52px] text-center text-[12px] leading-snug text-night-100">{t("hint")}</span>
      </div>
      <input
        ref={camera}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        tabIndex={-1}
        onChange={(e) => picked(e.target.files?.[0])}
      />
      <input
        ref={gallery}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        tabIndex={-1}
        onChange={(e) => picked(e.target.files?.[0])}
      />
    </div>
  );
}
