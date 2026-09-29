"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { readerApi, SHARE_DAYS, shareUrl, type Share } from "@/lib/reader";

type Props = {
  bookId: string;
  share: Share | null;
  onChange: (share: Share | null) => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

/**
 * The owner's share link: a private address that opens this book only (no account, no other data).
 * One link at a time; a new link or «إيقاف» turns the previous one off at once.
 */
export function SharePanel({ bookId, share, onChange, open, onOpenChange }: Props) {
  const t = useTranslations("reader.share");
  const te = useTranslations("errors");
  const locale = useLocale();
  const dialog = useRef<HTMLDialogElement>(null);
  const [days, setDays] = useState<(typeof SHARE_DAYS)[number]>(30);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const url = share ? shareUrl(share.token, locale) : "";

  useEffect(() => {
    const el = dialog.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  const create = async () => {
    setBusy(true);
    setError(null);
    const r = await readerApi.share(bookId, days);
    setBusy(false);
    if (!r.ok) return setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    setCopied(false);
    onChange(r.data);
  };
  const revoke = async () => {
    if (!share || !window.confirm(t("revokeConfirm"))) return;
    setBusy(true);
    const r = await readerApi.revoke(bookId, share.id);
    setBusy(false);
    if (!r.ok) return setError(errorText(r.error, locale, te("unknown")));
    onChange(null);
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  const native = async () => {
    try {
      await navigator.share?.({ title: t("title"), url });
    } catch {}
  };
  const until = share?.expires_at
    ? new Date(share.expires_at).toLocaleDateString(locale === "ar" ? "ar" : "en-GB")
    : "";

  return (
    <dialog
      ref={dialog}
      onClose={() => onOpenChange(false)}
      aria-labelledby="share-title"
      className="m-auto w-[calc(100%-32px)] max-w-md rounded-xl bg-paper-raised p-0 text-ink backdrop:bg-night-950/70"
    >
      <div className="flex flex-col gap-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <h2 id="share-title" className="text-h3 text-night-900">
            {t("title")}
          </h2>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            aria-label={t("close")}
            className="flex size-11 shrink-0 items-center justify-center rounded-full bg-paper-sunk text-night-900"
          >
            <svg
              className="size-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        <p className="text-small text-ink-muted">{t("privacy")}</p>
        {error && <Alert>{error}</Alert>}
        {share ? (
          <>
            <label className="flex flex-col gap-1.5">
              <span className="text-small font-semibold">{t("link")}</span>
              <input
                readOnly
                dir="ltr"
                value={url}
                onFocus={(e) => e.currentTarget.select()}
                className="min-h-12 w-full rounded-md border border-line bg-paper px-3 text-small"
              />
            </label>
            <p className="text-caption text-ink-muted">{t("until", { date: until })}</p>
            <div className="flex flex-wrap gap-2">
              <Button variant="primary" size="sm" onClick={copy}>
                {copied ? t("copied") : t("copy")}
              </Button>
              {typeof navigator !== "undefined" && "share" in navigator && (
                <Button variant="secondary" size="sm" onClick={native}>
                  {t("send")}
                </Button>
              )}
            </div>
            <div className="flex flex-wrap gap-2 border-t border-line pt-3">
              <Button variant="ghost" size="sm" onClick={create} loading={busy}>
                {t("renew")}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-danger hover:text-danger"
                onClick={revoke}
                disabled={busy}
              >
                {t("revoke")}
              </Button>
            </div>
          </>
        ) : (
          <>
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-1 text-small font-semibold">{t("validFor")}</legend>
              <div className="flex flex-wrap gap-2">
                {SHARE_DAYS.map((d) => (
                  <label
                    key={d}
                    className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-full border-2 px-4 text-small font-semibold ${days === d ? "border-night-900 bg-night-100" : "border-line"}`}
                  >
                    <input
                      type="radio"
                      name="share-days"
                      className="sr-only"
                      checked={days === d}
                      onChange={() => setDays(d)}
                    />
                    {t(`days.${d}`)}
                  </label>
                ))}
              </div>
            </fieldset>
            <Button variant="primary" onClick={create} loading={busy}>
              {t("create")}
            </Button>
          </>
        )}
      </div>
    </dialog>
  );
}
