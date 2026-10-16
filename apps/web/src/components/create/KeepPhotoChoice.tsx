"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import { createApi, type PhotoKeep } from "@/lib/create";

type Who = { id: string; name: string; gender: "m" | "f" };

/** A date as the parent reads it («16 أكتوبر 2027», Latin digits like the rest of the site). */
function day(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale === "ar" ? "ar-EG-u-nu-latn" : "en-GB", { dateStyle: "long" }).format(
    new Date(iso),
  );
}

/**
 * «احتفظوا بالصورة» (owner, 2026-10-16): the guardian's optional choice to keep the child's original photo for
 * later books. Off by default and never pre-ticked; ticking it records its own versioned consent
 * (`photoKeep.version`), unticking takes it back (the photo then goes within 24 hours). On the photo step
 * (`variant="step"`) it is the box alone; in «أطفالي» (`variant="account"`) it also says what we hold and until
 * when, with «احذفوا الصورة الآن». `onChange`: the choice as the API now has it.
 */
export function KeepPhotoChoice({
  child,
  variant = "step",
  onChange,
}: {
  child: Who;
  variant?: "step" | "account";
  onChange?: (state: PhotoKeep) => void;
}) {
  const t = useTranslations("photoKeep");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [state, setState] = useState<PhotoKeep | null>(null);
  const [busy, setBusy] = useState<"keep" | "delete" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const who = { ...nameCases(child.name), gender: child.gender };

  useEffect(() => {
    let alive = true;
    (async () => {
      const r = await createApi.photoKeep(child.id);
      if (!alive) return;
      if (r.ok) {
        setState(r.data);
        onChange?.(r.data);
      } else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    })();
    return () => {
      alive = false;
    };
    // once per child
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [child.id]);

  function failed(r: { error: Parameters<typeof errorText>[0]; status: number }) {
    setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  async function toggle(keep: boolean) {
    setBusy("keep");
    setError(null);
    setNotice(null);
    const r = await createApi.setPhotoKeep(child.id, keep, keep ? t("version") : undefined);
    setBusy(null);
    if (!r.ok) return failed(r);
    setState(r.data);
    onChange?.(r.data);
    if (!keep && variant === "account") setNotice(t("turnedOff"));
  }

  async function deleteNow() {
    if (!window.confirm(t("deleteConfirm", who))) return;
    setBusy("delete");
    setError(null);
    setNotice(null);
    const r = await createApi.deletePhotos(child.id);
    if (!r.ok) {
      setBusy(null);
      return failed(r);
    }
    const after = await createApi.photoKeep(child.id);
    setBusy(null);
    if (after.ok) {
      setState(after.data);
      onChange?.(after.data);
    }
    setNotice(t("deleted"));
  }

  if (!state) return error ? <Alert>{error}</Alert> : null;
  const months = { months: state.months };
  const box = (
    <label
      className={`flex cursor-pointer items-start gap-3 rounded-2xl p-4 text-body ${state.keep ? "border-2 border-night-900 bg-night-100" : "border-[1.5px] border-line bg-paper-raised"}`}
    >
      <input
        type="checkbox"
        checked={state.keep}
        disabled={busy !== null}
        onChange={(e) => void toggle(e.target.checked)}
        className="mt-0.5 size-6 shrink-0 accent-night-900"
      />
      <span className="flex flex-col gap-1">
        <span>{t("accept", who)}</span>
        <span className="text-small text-ink-muted">{t("hint", months)}</span>
      </span>
    </label>
  );

  if (variant === "step")
    return (
      <div className="flex flex-col gap-2">
        {box}
        {error && <Alert>{error}</Alert>}
      </div>
    );

  const photo = state.photo;
  const status = !photo
    ? t("status.none", who)
    : state.keep && photo.deletes_at
      ? t("status.kept", { date: day(photo.deletes_at, locale) })
      : photo.deletes_at
        ? t("status.due", { date: day(photo.deletes_at, locale) })
        : t("status.afterApproval");
  return (
    <section
      aria-label={t("title", who)}
      className="flex flex-col gap-3 rounded-2xl border border-line bg-paper-raised p-4"
    >
      <strong className="text-body text-night-900">{t("title", who)}</strong>
      <p className="text-small text-ink-muted">{status}</p>
      {(photo || state.keep) && box}
      {photo && (
        <Button
          variant="ghost"
          size="sm"
          className="self-start text-danger hover:text-danger"
          loading={busy === "delete"}
          disabled={busy !== null}
          onClick={() => void deleteNow()}
        >
          {t("deleteNow")}
        </Button>
      )}
      {notice && <Alert tone="info">{notice}</Alert>}
      {error && <Alert>{error}</Alert>}
    </section>
  );
}
