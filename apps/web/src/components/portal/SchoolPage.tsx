"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText, type ApiErrorBody } from "@/lib/api";
import { portalApi, portalFiles, type ClassBook } from "@/lib/portal";

const MESSAGE_MAX = 220;

/** The school page of the class book (design PortalClass): logo, the class photo, the teacher's message. */
export function SchoolPage({
  classId,
  book,
  message,
  setMessage,
  locked,
  hasLogo,
  onBook,
  onLogo,
}: {
  classId: string;
  book: ClassBook;
  message: string;
  setMessage: (m: string) => void;
  locked: boolean;
  hasLogo: boolean;
  onBook: (b: ClassBook) => void;
  onLogo: () => Promise<void>;
}) {
  const t = useTranslations("portal.setup");
  const te = useTranslations("errors");
  const locale = useLocale();
  const photo = useRef<HTMLInputElement>(null);
  const logo = useRef<HTMLInputElement>(null);
  const [permission, setPermission] = useState(false);
  const [busy, setBusy] = useState<"photo" | "logo" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stamp, setStamp] = useState(0); // refreshes the private previews after an upload

  async function upload(kind: "photo" | "logo", file: File | undefined) {
    if (!file) return;
    setBusy(kind);
    setError(null);
    const fail = (e: ApiErrorBody | null, status: number) =>
      setError(errorText(e, locale, status === 0 ? te("network") : te("unknown")));
    if (kind === "photo") {
      const r = await portalApi.classPhoto(classId, file, permission);
      if (r.ok) onBook(r.data);
      else fail(r.error, r.status);
    } else {
      const r = await portalApi.logo(file);
      if (r.ok) await onLogo();
      else fail(r.error, r.status);
    }
    setBusy(null);
    setStamp((n) => n + 1);
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-h3 text-night-900">{t("schoolPage")}</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex flex-col gap-2 rounded-lg border border-line bg-paper-raised p-4">
          <strong>{t("logo")}</strong>
          <span className="text-caption text-ink-muted">{t("logoHint")}</span>
          {hasLogo && (
            // eslint-disable-next-line @next/next/no-img-element -- private, through the API
            <img
              src={`${portalFiles.logo}?v=${stamp}`}
              alt={t("logo")}
              className="h-16 w-auto self-start object-contain"
            />
          )}
          <input
            ref={logo}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            aria-label={t("logo")}
            onChange={(e) => void upload("logo", e.target.files?.[0])}
          />
          <Button
            variant="secondary"
            size="sm"
            className="self-start"
            loading={busy === "logo"}
            onClick={() => logo.current?.click()}
          >
            {hasLogo ? t("replace") : t("upload")}
          </Button>
        </div>
        <div className="flex flex-col gap-2 rounded-lg border border-line bg-paper-raised p-4">
          <strong>{t("classPhoto")}</strong>
          <span className="text-caption text-ink-muted">{t("classPhotoHint")}</span>
          {book.class_photo && (
            // eslint-disable-next-line @next/next/no-img-element -- private, through the API
            <img
              src={`${portalFiles.classPhoto(classId)}?v=${stamp}`}
              alt={t("classPhoto")}
              className="aspect-video w-full rounded-md object-cover"
            />
          )}
          <label className="flex items-start gap-2 text-small">
            <input
              type="checkbox"
              checked={permission}
              onChange={(e) => setPermission(e.target.checked)}
              className="mt-0.5 size-5 shrink-0 accent-night-900"
              disabled={locked}
            />
            {t("permission")}
          </label>
          <input
            ref={photo}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            aria-label={t("classPhoto")}
            onChange={(e) => void upload("photo", e.target.files?.[0])}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              size="sm"
              loading={busy === "photo"}
              disabled={locked || !permission}
              onClick={() => photo.current?.click()}
            >
              {book.class_photo ? t("replace") : t("upload")}
            </Button>
            {book.class_photo && (
              <Button
                variant="ghost"
                size="sm"
                disabled={locked}
                onClick={async () => {
                  const r = await portalApi.deleteClassPhoto(classId);
                  if (r.ok) onBook(r.data);
                }}
              >
                {t("removePhoto")}
              </Button>
            )}
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="teacher-message" className="text-small font-semibold">
          {t("message")}
        </label>
        <textarea
          id="teacher-message"
          rows={4}
          maxLength={MESSAGE_MAX}
          value={message}
          disabled={locked}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={t("messagePlaceholder")}
          className="rounded-sm border border-line bg-paper-raised p-4 text-body outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-100"
        />
        <span className="self-end text-caption text-ink-muted">
          {message.length} / {MESSAGE_MAX}
        </span>
      </div>
      {error && <Alert>{error}</Alert>}
    </section>
  );
}
