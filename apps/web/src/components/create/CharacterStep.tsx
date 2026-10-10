"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import { characterImage, createApi, type Character, type Child, type Drawing, type Fix } from "@/lib/create";
import { lastApproved, NOTE_MAX, offered, tidyNote } from "@/lib/drawings";
import { ACTIVITY_LINES } from "@/lib/shop";
import { Chip, Frame, Lead } from "./Frame";

const FIXES: Fix[] = ["skin", "face", "hair", "age"];
const POLL_MS = 3000;

/**
 * Step 6 (design Create5): the drawn character; approve it, or redraw with what didn't look right (the chips and,
 * optionally, the parent's own words). It says where this product shows the character, what approving does (kept
 * for the next books, the photo deleted within 24 h) and the free-redraw rule (3 per child; a drawing that failed
 * on our side doesn't count).
 *
 * Every drawing of the child stays (owner, 2026-10-10): the earlier ones, in any style this book can use
 * (`usable`), show as a strip under the picture, newest first, so the parent can compare them and go back to one.
 * Tapping one shows it large; the approve button approves it and a redraw starts from it. Approving a drawing in
 * another style makes the book use that style (`onApproved` gets that drawing).
 */
export function CharacterStep({
  child,
  character,
  productLine = null,
  usable = null,
  title,
  back,
  onChange,
  onApproved,
  onEditPhoto,
}: {
  child: Child;
  character: Character;
  productLine?: string | null; // classic|magic|workbook|journey|family|islamic (null: a story)
  usable?: readonly string[] | null; // the styles this book can use (null: any): drawings in others aren't offered
  title?: string; // the frame title; the wizard's FlowFrameContext wins when present
  back: () => void;
  onChange: (c: Character) => void;
  onApproved: (c: Character) => void;
  onEditPhoto?: () => void; // «تعديل الصورة»: the photo's framing (or a new photo); never redraws by itself
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [fixes, setFixes] = useState<Fix[]>([]);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "redraw" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  // the child's drawings, newest first (kept while a newer list loads)
  const [drawings, setDrawings] = useState<Drawing[] | null>(null);
  // the drawing tapped in the strip, for this drawing in this state (a new drawing, or a finished one, shows itself)
  const [picked, setPicked] = useState<{ key: string; id: string } | null>(null);
  const who = { ...nameCases(child.name), gender: child.gender };
  const drawing = character.status === "generating";
  const kind = (ACTIVITY_LINES as readonly string[]).includes(productLine ?? "") ? "activity" : "story";
  const places = t(
    t.has(`character.places.${productLine}`) ? `character.places.${productLine}` : "character.places.other",
  );
  const key = `${character.id}:${character.status}`;

  useEffect(() => {
    if (!drawing) return;
    const timer = setInterval(async () => {
      setTick((n) => n + 1);
      const r = await createApi.character(character.id);
      if (r.ok && r.data.status !== "generating") onChange(r.data);
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [drawing, character.id, onChange]);

  useEffect(() => {
    let alive = true;
    (async () => {
      const r = await createApi.drawings(child.id);
      if (alive && r.ok) setDrawings(r.data);
    })();
    return () => {
      alive = false;
    };
  }, [child.id, key]);

  const list = offered(drawings ?? [], character.id, usable);
  const chosen = picked?.key === key ? list.find((d) => d.id === picked.id) : undefined;
  const selected: Character = chosen ?? character;
  const shown = selected.status === "ready" || selected.status === "approved";
  const inUse = lastApproved(drawings ?? []); // the child's character today, if any
  const styleName = (d: Drawing) => (locale === "ar" ? d.style_name_ar : d.style_name_en);
  const strip = list.length + (drawing ? 1 : 0) > 1; // something to compare with

  async function approve() {
    setBusy("approve");
    setError(null);
    const r = await createApi.approve(selected.id);
    setBusy(null);
    if (r.ok) onApproved(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  async function redraw() {
    setBusy("redraw");
    setError(null);
    const failed = selected.status === "failed";
    const said = failed ? undefined : tidyNote(note);
    const r = await createApi.draw(child.id, selected.style, failed ? [] : fixes, null, {
      redraw: true,
      ...(said ? { note: said } : {}),
    });
    setBusy(null);
    if (r.ok) {
      setFixes([]);
      setNote("");
      onChange(r.data);
    } else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  const left = Math.max(0, child.redraws_left);
  return (
    <Frame
      title={title ?? t("bookOf", who)}
      label={t("steps.character")}
      back={back}
      footer={
        shown ? (
          <div className="flex grow flex-col gap-2">
            <Button onClick={approve} loading={busy === "approve"} size="lg">
              {t("character.approve", who)}
            </Button>
            <Button
              onClick={redraw}
              loading={busy === "redraw"}
              variant="secondary"
              disabled={!left || !!busy || drawing}
            >
              <svg className="size-[18px]" viewBox="0 0 24 24" aria-hidden="true">
                <g fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                  <path d="M20 4v5h-5" />
                </g>
              </svg>
              {t("character.redraw", { left })}
            </Button>
          </div>
        ) : selected.status === "failed" ? (
          <Button onClick={redraw} loading={busy === "redraw"} size="lg" className="grow" disabled={!left}>
            {t("retry")}
          </Button>
        ) : undefined
      }
    >
      {selected.status === "generating" ? (
        <div role="status" className="flex flex-col items-center gap-5 py-10 text-center">
          <MoonPhase p={((tick % 12) + 1) / 12} className="size-24" />
          <h1 className="text-[26px] text-night-900">{t("character.drawing", who)}</h1>
          <p className="text-body text-ink-muted">{t("character.drawingHint")}</p>
        </div>
      ) : selected.status === "failed" ? (
        <Alert>{t("character.failed")}</Alert>
      ) : (
        <>
          <Lead title={t("character.title", who)} body={t(`character.where.${kind}`, { ...who, places })} />
          <figure className="flex flex-col gap-2 overflow-hidden rounded-3xl border border-line bg-paper-raised p-2">
            {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API, no-store */}
            <img
              src={characterImage(selected.id)}
              alt={t("character.alt", who)}
              className="aspect-[3/2] w-full rounded-2xl object-contain"
            />
            <figcaption className="pb-1 text-center text-caption text-ink-muted">{t("character.views")}</figcaption>
          </figure>
          {onEditPhoto && (
            <button
              type="button"
              onClick={onEditPhoto}
              className="-mt-3 min-h-11 self-center px-3 text-small font-semibold text-night-900 underline underline-offset-4"
            >
              {t("character.editPhoto")}
            </button>
          )}
        </>
      )}
      {strip && (
        <section aria-labelledby="drawings-title" className="flex flex-col gap-2">
          <h2 id="drawings-title" className="text-body font-semibold text-night-900">
            {t("character.drawings", who)}
          </h2>
          <p className="text-small text-ink-muted">{t("character.drawingsHint", who)}</p>
          <div className="-mx-4 flex gap-2.5 overflow-x-auto px-4 pt-1 pb-2">
            {drawing && (
              <button
                type="button"
                aria-pressed={selected.id === character.id}
                onClick={() => setPicked(null)}
                className={`flex w-[96px] shrink-0 flex-col gap-1.5 rounded-2xl bg-paper-raised p-1.5 text-start transition ${selected.id === character.id ? "border-[3px] border-amber-500" : "border-[1.5px] border-line"}`}
              >
                <span className="flex h-[100px] w-full items-center justify-center rounded-xl bg-paper-sunk">
                  <MoonPhase p={((tick % 12) + 1) / 12} className="size-10" />
                </span>
                <span className="text-caption font-semibold text-night-900">{t("character.drawingNow")}</span>
              </button>
            )}
            {list.map((d) => {
              const on = d.id === selected.id;
              return (
                <button
                  key={d.id}
                  type="button"
                  aria-pressed={on}
                  onClick={() => setPicked({ key, id: d.id })}
                  className={`flex w-[96px] shrink-0 flex-col gap-1.5 rounded-2xl bg-paper-raised p-1.5 text-start transition ${on ? "border-[3px] border-amber-500 shadow-[0_8px_24px_rgba(242,179,61,0.25)]" : "border-[1.5px] border-line"}`}
                >
                  <span className="relative block h-[100px] w-full overflow-hidden rounded-xl bg-paper-sunk">
                    {/* the sheet is three full figures side by side: the thumbnail shows the front view */}
                    {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API, no-store */}
                    <img
                      src={characterImage(d.id)}
                      alt=""
                      loading="lazy"
                      className="absolute top-0 left-0 h-[150px] w-auto max-w-none"
                    />
                  </span>
                  <span className="line-clamp-2 text-caption font-semibold text-night-900">{styleName(d)}</span>
                  {d.id === inUse?.id && (
                    <span className="self-start rounded-full bg-amber-100 px-2 py-0.5 text-caption font-bold text-amber-700">
                      {t("character.inUse")}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </section>
      )}
      {shown && (
        <>
          {left > 0 ? (
            <details className="rounded-2xl border border-line bg-paper-raised p-4">
              <summary className="cursor-pointer text-body font-semibold">
                {t("character.wrong", who)}{" "}
                <span className="font-normal text-ink-muted">{t("character.wrongHint")}</span>
              </summary>
              <div className="flex flex-wrap gap-2 pt-3">
                {FIXES.map((f) => (
                  <Chip
                    key={f}
                    on={fixes.includes(f)}
                    onClick={() => setFixes((l) => (l.includes(f) ? l.filter((x) => x !== f) : [...l, f]))}
                  >
                    {t(`character.fixes.${f}`)}
                  </Chip>
                ))}
              </div>
              <div className="flex flex-col gap-1.5 pt-4">
                <label htmlFor="character-note" className="text-small font-semibold">
                  {t("character.noteLabel", who)}{" "}
                  <span className="font-normal text-ink-muted">{t("story.optional")}</span>
                </label>
                <textarea
                  id="character-note"
                  rows={3}
                  maxLength={NOTE_MAX}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder={t("character.notePlaceholder", who)}
                  aria-describedby="character-note-hint"
                  className="resize-none rounded-[14px] border-[1.5px] border-line bg-white px-4 py-3 text-body outline-none placeholder:text-ink-faint focus:border-night-900 focus:ring-4 focus:ring-night-100"
                />
                <span id="character-note-hint" className="flex justify-between gap-3 text-caption text-ink-muted">
                  <span>{t("character.noteHint", who)}</span>
                  <span dir="ltr">
                    {note.length}/{NOTE_MAX}
                  </span>
                </span>
              </div>
            </details>
          ) : (
            <p className="text-small text-ink-muted">{t("character.noRedraws")}</p>
          )}
          <section
            aria-labelledby="on-approve"
            className="flex flex-col gap-2 rounded-2xl bg-paper-sunk p-4 text-small text-ink"
          >
            <strong id="on-approve" className="text-body text-night-900">
              {t("character.onApprove", who)}
            </strong>
            <ul className="flex list-disc flex-col gap-1.5 ps-5 marker:text-night-700">
              {kind === "story" && chosen && chosen.style !== character.style && (
                <li>{t("character.otherStyle", { style: styleName(chosen) })}</li>
              )}
              <li>{t("character.keep", who)}</li>
              <li>{t(`character.next.${kind}`, who)}</li>
            </ul>
            {left > 0 && <p className="border-t border-dashed border-line pt-2">{t("character.redrawRule")}</p>}
          </section>
        </>
      )}
      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
