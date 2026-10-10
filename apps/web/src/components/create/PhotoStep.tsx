"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Kid } from "@/components/art/Kid";
import { Alert } from "@/components/ui/Alert";
import { Button, Spinner } from "@/components/ui/Button";
import { errorText, type ApiResult } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import { createApi, type Child } from "@/lib/create";
import { sameCrop, toCrop, viewAt, type PhotoCrop, type Size } from "@/lib/photoCrop";
import { ACTIVITY_LINES } from "@/lib/shop";
import { Frame, Lead } from "./Frame";
import { PhotoEditor } from "./PhotoEditor";

const CHECKS = ["one", "front", "light", "close"] as const;
type CheckName = (typeof CHECKS)[number];
/** Which of the four checks a failed photo check (qamra_ai.pipeline.photo_check) points at. */
const FAILS: Record<string, CheckName[]> = {
  no_face: ["one", "front"],
  many_faces: ["one"],
  face_small: ["close"],
  face_cut: ["front"], // part of the face outside the frame
  crop_small: ["light"],
  blurry: ["light"],
  dark: ["light"],
  bright: ["light"],
  too_small: ["light"],
};
/** Failed checks that moving or zooming the photo may fix: the editor opens on them. */
const FRAMEABLE = new Set(["no_face", "many_faces", "face_small", "face_cut", "crop_small"]);
const EXAMPLES = [
  { key: "good", good: true, fx: "" },
  { key: "dark", good: false, fx: "brightness-[0.45]" },
  { key: "blurry", good: false, fx: "blur-[3px]" },
  { key: "far", good: false, fx: "scale-[0.45] origin-bottom" },
] as const;
/**
 * The photo picked on this device, by its kept id: the editor shows it again without downloading it back. In
 * memory for this visit only (a reload, or another device, gets the original from the API).
 */
const PICKED = new Map<string, Blob>();

type State = "idle" | "loading" | "checking" | "ok" | "failed" | "editing" | "saving" | "gone";
/** What changed when the step is done from a later step (`edit`): a new photo, a new framing, or nothing. */
export type PhotoChange = "photo" | "position" | null;

/**
 * Step 3 (design Create3): one clear photo, checked on the server before anything is drawn. The parent places
 * it in the frame so the face sits in the oval (PhotoEditor): on upload the API frames it around the face it
 * finds, and «تعديل موضع الصورة» moves, zooms and turns it; the API checks the framed part again. The lead says
 * where this product shows the character (order-flows §c.5); the card at the end says what we keep, what we
 * delete and what happens next. `edit`: opened from the character step to change the photo («تعديل الصورة»):
 * it opens on the kept photo in the editor, or says kindly that it was deleted and asks for a new one.
 */
export function PhotoStep({
  child,
  productLine = null,
  title,
  edit = false,
  back,
  onDone,
}: {
  child: Child;
  productLine?: string | null; // classic|magic|workbook|journey|family|islamic (null: a story, type not chosen)
  title?: string; // the frame title; the wizard's FlowFrameContext wins when present
  edit?: boolean;
  back: () => void;
  onDone: (c: Child, change: PhotoChange) => void;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const input = useRef<HTMLInputElement>(null);
  const shown = useRef<string | null>(null);
  const kept = child.photo ?? null;
  const [preview, setPreview] = useState<string | null>(null);
  const [state, setState] = useState<State>(
    kept ? "loading" : child.photos ? "ok" : edit ? "gone" : "idle", // photos without `photo`: an older API
  );
  const [failed, setFailed] = useState<CheckName[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [saved, setSaved] = useState<Child>(child);
  const [picked, setPicked] = useState<File | null>(null); // a photo the check refused: never kept on the server
  const [crop, setCrop] = useState<PhotoCrop | null>(kept?.crop ?? null); // the framing on screen
  const [savedCrop, setSavedCrop] = useState<PhotoCrop | null>(kept?.crop ?? null); // the API's
  const [natural, setNatural] = useState<Size | null>(null);
  const [change, setChange] = useState<PhotoChange>(null);
  const who = { ...nameCases(child.name), gender: child.gender };
  const activity = (ACTIVITY_LINES as readonly string[]).includes(productLine ?? "");
  // where this activity book prints the character (checked against the renderers, 2026-10-07)
  const places = t(
    t.has(`character.places.${productLine}`) ? `character.places.${productLine}` : "character.places.other",
  );
  const photoId = saved.photo?.id ?? null;

  function show(blob: Blob) {
    if (shown.current) URL.revokeObjectURL(shown.current);
    shown.current = URL.createObjectURL(blob); // shown on this device only, never sent anywhere else
    setPreview(shown.current);
  }

  useEffect(() => {
    if (!kept) return;
    let alive = true;
    (async () => {
      // the copy picked on this device, else the kept original from the API (the guardian's only, no-store)
      const local = PICKED.get(kept.id);
      const r: ApiResult<Blob> = local ? { ok: true, status: 200, data: local } : await createApi.photoBlob(kept.id);
      if (!alive) return;
      if (r.ok) {
        show(r.data);
        setState(edit ? "editing" : "ok");
      } else if (r.status === 410) setState("gone");
      else {
        setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
        setState("ok"); // the photo is kept: the flow goes on, only its picture didn't load
      }
    })();
    return () => {
      alive = false;
    };
    // once, for the photo the step opened with
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(
    () => () => {
      if (shown.current) URL.revokeObjectURL(shown.current);
    },
    [],
  );

  /** A refused call: the four checks' marks and the friendly reason (the API's Arabic or English). */
  function refused(r: Extract<ApiResult<unknown>, { ok: false }>) {
    const details = r.error?.details as { reason?: string; ar?: string; en?: string } | undefined;
    setFailed(FAILS[details?.reason ?? ""] ?? []);
    const friendly = details?.ar && details?.en ? (locale === "ar" ? details.ar : details.en) : null;
    setError(friendly ?? errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    return details?.reason ?? null;
  }

  /** The framing to send: the one on screen, else the starting view (centred, unzoomed). */
  function framing(): PhotoCrop | null {
    return crop ?? (natural ? toCrop(viewAt(natural, 0)) : null);
  }

  async function choose(file: File | undefined) {
    if (!file) return;
    show(file);
    setPicked(file);
    setCrop(null);
    setNatural(null);
    await check(file, null);
  }

  /** Upload and check: without a framing the API frames the photo around the face it finds. */
  async function check(file: File, frame: PhotoCrop | null) {
    setState("checking");
    setFailed([]);
    setError(null);
    setNote(null);
    const r = await createApi.photo(child.id, file, frame);
    if (r.ok) {
      const photo = r.data.photo ?? null;
      if (photo) PICKED.set(photo.id, file);
      setSaved(r.data);
      setPicked(null);
      setCrop(photo?.crop ?? frame);
      setSavedCrop(photo?.crop ?? frame);
      setChange("photo");
      setState("ok");
      return;
    }
    const reason = refused(r);
    setState("failed");
    if (!reason || !FRAMEABLE.has(reason)) setPicked(null); // only another photo helps
  }

  /** «احفظوا الموضع»: the API checks the new framing; a framing it refuses leaves the saved one. */
  async function saveFraming() {
    const frame = framing();
    if (!photoId || !frame) return;
    if (sameCrop(frame, savedCrop)) return finished(saved, false);
    setState("saving");
    setError(null);
    setFailed([]);
    const r = await createApi.frame(photoId, frame);
    if (r.ok) {
      setSaved(r.data);
      setSavedCrop(r.data.photo?.crop ?? frame);
      setCrop(r.data.photo?.crop ?? frame);
      return finished(r.data, true);
    }
    if (r.status === 410) {
      setState("gone");
      setError(null);
      return;
    }
    refused(r);
    setState("editing");
  }

  function finished(c: Child, moved: boolean) {
    const now: PhotoChange = change === "photo" ? "photo" : moved ? "position" : change; // a new photo says more
    if (edit) return onDone(c, now);
    setState("ok");
    setChange(now);
    if (moved) setNote(t("photo.editor.saved"));
  }

  function cancel() {
    setCrop(savedCrop);
    setError(null);
    setFailed([]);
    if (edit) back();
    else setState("ok");
  }

  const editing = state === "editing" || state === "saving";
  const fixable = state === "failed" && !!picked;
  const mark = (c: CheckName) =>
    state === "ok" || editing ? "ok" : state === "failed" ? (failed.includes(c) ? "bad" : "ok") : "wait";
  const footer = editing ? (
    <Button onClick={saveFraming} loading={state === "saving"} size="lg" className="grow">
      {t("photo.editor.save")}
    </Button>
  ) : fixable ? (
    <Button onClick={() => void check(picked, framing())} size="lg" className="grow">
      {t("photo.editor.recheck")}
    </Button>
  ) : (
    <Button onClick={() => onDone(saved, change)} disabled={state !== "ok"} size="lg" className="grow">
      {t("photo.cta")}
    </Button>
  );

  return (
    <Frame title={title ?? t("bookOf", who)} label={t("steps.photo")} back={back} footer={footer}>
      {edit ? (
        <Lead
          title={t("photo.editTitle", who)}
          // «أعيدوا الرسم» only while a free redraw is left
          body={child.redraws_left > 0 ? `${t("photo.editBody")} ${t("photo.editRedraw")}` : t("photo.editBody")}
        />
      ) : (
        <Lead
          title={t("photo.title")}
          body={`${activity ? t("photo.why.activity", { ...who, places }) : t("photo.why.story", who)} ${t("photo.how")}`}
        />
      )}

      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        aria-label={t("photo.pick")}
        onChange={(e) => {
          void choose(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      <PhotoEditor
        src={state === "gone" ? null : preview}
        crop={crop}
        editable={editing || fixable}
        onChange={(c) => {
          setCrop(c);
          setNote(null);
        }}
        onNatural={setNatural}
        placeholder={
          <Kid look="photo" hijab={child.hijab} hijabColor="#E9826B" outfit="#F2B33D" className="h-auto w-[290px]" />
        }
      >
        <span className="absolute start-3.5 top-3.5 rounded-full bg-night-950/80 px-3 py-1.5 text-caption font-semibold text-paper">
          {t("photo.guide")}
        </span>
        {state !== "idle" && state !== "gone" && state !== "loading" && (
          <button
            type="button"
            onClick={() => input.current?.click()}
            disabled={state === "checking" || state === "saving"}
            className="absolute end-2.5 top-2.5 min-h-11 rounded-full bg-paper/95 px-3.5 text-small font-semibold text-night-900"
          >
            {t("photo.change")}
          </button>
        )}
        {(state === "idle" || state === "gone") && (
          <Button
            onClick={() => input.current?.click()}
            size="lg"
            className="absolute inset-x-6 bottom-6 mx-auto w-fit"
          >
            {state === "gone" ? t("photo.newPhoto") : t("photo.pick")}
          </Button>
        )}
        {state === "loading" && (
          <span role="status" className="absolute inset-0 flex items-center justify-center gap-2 text-small">
            <span className="flex items-center gap-2 rounded-full bg-paper-raised px-3 py-1.5 shadow-1">
              <Spinner /> {t("photo.editor.loading")}
            </span>
          </span>
        )}
      </PhotoEditor>

      {state === "ok" && preview && (
        <Button variant="secondary" size="sm" className="self-center" onClick={() => setState("editing")}>
          <svg className="size-[18px]" viewBox="0 0 24 24" aria-hidden="true">
            <g fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3v18M3 12h18M12 3l-3 3M12 3l3 3M12 21l-3-3M12 21l3-3M3 12l3-3M3 12l3 3M21 12l-3-3M21 12l-3 3" />
            </g>
          </svg>
          {t("photo.adjust")}
        </Button>
      )}
      {editing && !edit && (
        <button
          type="button"
          onClick={cancel}
          disabled={state === "saving"}
          className="min-h-11 self-center px-4 text-small font-semibold text-night-900 underline underline-offset-4"
        >
          {t("photo.editor.cancel")}
        </button>
      )}
      {state === "gone" && <Alert tone="info">{t("photo.gone", who)}</Alert>}
      {note && <Alert tone="success">{note}</Alert>}

      {state !== "idle" && state !== "gone" && state !== "loading" && (
        <div role="status" className="flex flex-col gap-2.5 rounded-2xl border border-line bg-paper-raised px-4 py-3.5">
          <strong className="flex items-center gap-2 text-body">
            {state === "checking" ? (
              <>
                <Spinner /> {t("photo.checking")}
              </>
            ) : (
              t("photo.check")
            )}
          </strong>
          {CHECKS.map((c) => {
            const m = mark(c);
            return (
              <div key={c} className="flex items-center gap-2.5 text-small">
                <span
                  aria-hidden="true"
                  className={`flex size-6 items-center justify-center rounded-full text-caption font-bold ${m === "ok" ? "bg-success-bg text-success" : m === "bad" ? "bg-danger-bg text-danger" : "bg-paper-sunk text-ink-faint"}`}
                >
                  {m === "ok" ? "✓" : m === "bad" ? "✕" : "·"}
                </span>
                <span className="grow">{t(`photo.checks.${c}`)}</span>
              </div>
            );
          })}
          <p className="border-t border-dashed border-line pt-1 text-caption text-amber-700">{t("photo.tip", who)}</p>
        </div>
      )}
      {error && <Alert>{error}</Alert>}
      {fixable && <p className="text-small text-ink-muted">{t("photo.editor.retry")}</p>}

      {!edit && (
        <div className="flex flex-col gap-2.5">
          <strong className="text-body">{t("photo.examples")}</strong>
          <div className="grid grid-cols-4 gap-2">
            {EXAMPLES.map((e) => (
              <figure key={e.key} className="flex flex-col items-center gap-1.5">
                <div
                  className={`relative flex aspect-square w-full items-end justify-center overflow-hidden rounded-xl border-2 bg-[#D9D3C7] ${e.good ? "border-success" : "border-danger"}`}
                >
                  <div className={e.fx}>
                    <Kid look="photo" hairStyle="curly" skin="#C98F63" className="h-auto w-[70px]" />
                  </div>
                  <span
                    aria-hidden="true"
                    className={`absolute end-1 top-1 flex size-5 items-center justify-center rounded-full text-[12px] font-bold text-white ${e.good ? "bg-success" : "bg-danger"}`}
                  >
                    {e.good ? "✓" : "✕"}
                  </span>
                </div>
                <figcaption className="text-center text-[12px] text-ink-muted">{t(`photo.${e.key}`)}</figcaption>
              </figure>
            ))}
          </div>
        </div>
      )}
      <ul className="flex flex-col gap-2.5 rounded-2xl bg-paper-sunk p-4 text-small text-ink">
        {(
          [
            ["lock", t("photo.private")],
            ["clock", t("photo.keep", who)],
            ...(edit ? [] : [["next", t(activity ? "photo.next.activity" : "photo.next.story", who)]]),
          ] as const
        ).map(([icon, text]) => (
          <li key={icon} className="flex items-start gap-2.5">
            <Icon name={icon as "lock" | "clock" | "next"} />
            <span>{text}</span>
          </li>
        ))}
      </ul>
    </Frame>
  );
}

/** The small line icons of the "what happens to the photo" card. */
function Icon({ name }: { name: "lock" | "clock" | "next" }) {
  return (
    <svg
      className={`mt-0.5 size-[18px] shrink-0 text-night-700 ${name === "next" ? "rtl:-scale-x-100" : ""}`}
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {name === "lock" && (
          <>
            <rect x="5" y="11" width="14" height="10" rx="2" />
            <path d="M8 11V8a4 4 0 0 1 8 0v3" />
          </>
        )}
        {name === "clock" && (
          <>
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 2" />
          </>
        )}
        {name === "next" && <path d="M5 12h14M13 6l6 6-6 6" />}
      </g>
    </svg>
  );
}
