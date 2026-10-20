"use client";

import { useTranslations } from "next-intl";
import { Kid } from "@/components/art/Kid";
import { nameCases } from "@/lib/arabicName";
import { characterImage, characterPortrait, type Character, type Child } from "@/lib/create";
import { isArabicName, isLatinName } from "@/lib/flows";
import { Hint, inputClass } from "./EditChild";
import { Chip } from "./Frame";

/** A known child's look, asked again only when a new character will be drawn. */
export type Look = { hijab: boolean; glasses: boolean };

/**
 * A child the parent added before, as a confirmation card (§c.4): «{name} · بنت · 5 سنوات», whether the
 * character this book uses is ready, the English name when the book prints it (editable), the look when a new
 * character will be drawn, and «تعديل البيانات». An activity book with a ready character also offers «ارسموا
 * شخصية جديدة بأسلوب آخر» (`onRedraw`): the card then says a new one will be drawn and asks the look.
 * «تغيير الصورة» (`onChangePhoto`, owner 2026-10-19) opens the photo step for this child: a new photo (or the
 * current one moved, while it is still kept), then a new character drawn from it; the earlier drawings stay.
 */
export function KnownChild({
  child,
  ready,
  asksNameEn,
  traces,
  nameEn,
  onNameEn,
  look,
  onLook,
  redraw = false,
  onRedraw,
  onEdit,
  onChangePhoto,
  busy = false,
  showErrors,
}: {
  child: Child;
  ready: Character | null;
  asksNameEn: boolean;
  traces: boolean;
  nameEn: string;
  onNameEn: (v: string) => void;
  look: Look;
  onLook: (look: Look) => void;
  /** A new character in another style instead of the ready one (activity books). */
  redraw?: boolean;
  onRedraw?: (on: boolean) => void;
  onEdit: () => void;
  /** «تغيير الصورة»: the photo step for this child, then a new character from the new photo. */
  onChangePhoto?: () => void;
  /** The flow is going on (a tap is being saved): the card's actions wait. */
  busy?: boolean;
  showErrors: boolean;
}) {
  const t = useTranslations("create");
  const who = { ...nameCases(child.name), gender: child.gender };
  const badName = traces && !isArabicName(child.name);
  const badEn = asksNameEn && showErrors && !isLatinName(nameEn);
  return (
    <section
      aria-label={t("who.known.about", { ...who, age: child.age })}
      className="flex flex-col gap-4 rounded-[20px] border-2 border-night-900 bg-paper-raised p-4"
    >
      <div className="flex items-center gap-3.5">
        <div className="flex size-[76px] shrink-0 items-end justify-center overflow-hidden rounded-2xl bg-night-100">
          {ready ? (
            // eslint-disable-next-line @next/next/no-img-element -- private image through the API, no-store
            <img
              src={ready.has_portrait ? characterPortrait(ready.id) : characterImage(ready.id)}
              alt={t("who.known.alt", who)}
              className={`size-full object-cover transition ${redraw ? "opacity-40" : ""}`}
            />
          ) : (
            <Kid hijab={child.hijab} className="h-auto w-[64px]" />
          )}
        </div>
        <div className="flex min-w-0 flex-col gap-1">
          <strong className="text-body-l text-night-900">{t("who.known.about", { ...who, age: child.age })}</strong>
          {ready && redraw ? (
            <span className="text-small text-ink-muted">{t("who.known.redrawOn", who)}</span>
          ) : ready ? (
            <span className="flex items-center gap-1.5 text-small font-semibold text-success">
              <span aria-hidden="true">✓</span> {t("who.known.ready", who)}
            </span>
          ) : (
            <span className="text-small text-ink-muted">{t("who.known.notDrawn", who)}</span>
          )}
        </div>
      </div>

      {badName && (
        <p role="alert" className="text-small font-semibold text-danger">
          {t("who.arabicInvalid")}
        </p>
      )}

      {asksNameEn && (
        <div className="flex flex-col gap-1.5">
          <label htmlFor={`en-${child.id}`} className="text-body font-semibold">
            {t("who.nameEn")}
          </label>
          <Hint id={`en-${child.id}-hint`}>{t("who.nameEnHint", who)}</Hint>
          <input
            id={`en-${child.id}`}
            dir="auto"
            lang="en"
            value={nameEn}
            maxLength={40}
            autoComplete="off"
            autoCapitalize="words"
            spellCheck={false}
            placeholder={t("who.nameEnPlaceholder")}
            aria-describedby={`en-${child.id}-hint`}
            aria-invalid={badEn ? true : undefined}
            onChange={(e) => onNameEn(e.target.value)}
            className={`${inputClass} text-start placeholder:text-ink-faint`}
          />
          {badEn && <span className="text-caption font-semibold text-danger">{t("who.nameEnInvalid")}</span>}
        </div>
      )}

      {ready && onRedraw && (
        <button
          type="button"
          aria-pressed={redraw}
          onClick={() => onRedraw(!redraw)}
          className="min-h-11 self-start rounded-full border-[1.5px] border-line px-4 text-small font-bold text-night-900 hover:border-night-500"
        >
          {redraw ? t("who.known.keep", who) : t("who.known.redraw")}
        </button>
      )}

      {(!ready || redraw) && (
        <fieldset className="flex flex-col gap-2" aria-describedby={`look-${child.id}-hint`}>
          <legend className="text-body font-semibold">{t("child.drawAs", who)}</legend>
          <Hint id={`look-${child.id}-hint`}>{t("child.lookHint")}</Hint>
          <div className="flex flex-wrap gap-2">
            {child.gender === "f" && (
              <Chip on={look.hijab} onClick={() => onLook({ ...look, hijab: !look.hijab })}>
                {t("child.hijab")}
              </Chip>
            )}
            <Chip on={look.glasses} onClick={() => onLook({ ...look, glasses: !look.glasses })}>
              {t("child.glasses", { gender: child.gender })}
            </Chip>
          </div>
        </fieldset>
      )}

      <div className="flex flex-col gap-1.5">
        <div className="flex flex-wrap gap-2">
          {onChangePhoto && (
            <button
              type="button"
              onClick={onChangePhoto}
              disabled={busy}
              aria-describedby={`photo-${child.id}-hint`}
              className="inline-flex min-h-11 items-center gap-1.5 rounded-full border-[1.5px] border-night-900 px-4 text-small font-bold text-night-900 hover:bg-night-100 disabled:opacity-60"
            >
              <svg className="size-[18px]" viewBox="0 0 24 24" aria-hidden="true">
                <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
                  <circle cx="12" cy="13" r="3.5" />
                </g>
              </svg>
              {t("photo.change")}
            </button>
          )}
          <button
            type="button"
            onClick={onEdit}
            disabled={busy}
            className="min-h-11 rounded-full border-[1.5px] border-line px-4 text-small font-bold text-night-900 hover:border-night-500 disabled:opacity-60"
          >
            {t("who.known.edit")}
          </button>
        </div>
        {onChangePhoto && <Hint id={`photo-${child.id}-hint`}>{t("who.known.changePhotoHint", who)}</Hint>}
      </div>
    </section>
  );
}
