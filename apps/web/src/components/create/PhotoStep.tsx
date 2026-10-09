"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Kid } from "@/components/art/Kid";
import { Alert } from "@/components/ui/Alert";
import { Button, Spinner } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import { createApi, type Child } from "@/lib/create";
import { ACTIVITY_LINES } from "@/lib/shop";
import { Frame, Lead } from "./Frame";

const CHECKS = ["one", "front", "light", "close"] as const;
type CheckName = (typeof CHECKS)[number];
/** Which of the four checks a failed photo check (qamra_ai.pipeline.photo_check) points at. */
const FAILS: Record<string, CheckName[]> = {
  no_face: ["one", "front"],
  many_faces: ["one"],
  face_small: ["close"],
  blurry: ["light"],
  dark: ["light"],
  bright: ["light"],
  too_small: ["light"],
};
const EXAMPLES = [
  { key: "good", good: true, fx: "" },
  { key: "dark", good: false, fx: "brightness-[0.45]" },
  { key: "blurry", good: false, fx: "blur-[3px]" },
  { key: "far", good: false, fx: "scale-[0.45] origin-bottom" },
] as const;

/**
 * Step 3 (design Create3): one clear photo, checked on the server before anything is drawn. The lead says where
 * this product shows the character (order-flows §c.5); the card at the end says what we keep, what we delete and
 * what happens next.
 */
export function PhotoStep({
  child,
  productLine = null,
  title,
  back,
  onDone,
}: {
  child: Child;
  productLine?: string | null; // classic|magic|workbook|journey|family|islamic (null: a story, type not chosen)
  title?: string; // the frame title; the wizard's FlowFrameContext wins when present
  back: () => void;
  onDone: (c: Child) => void;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const input = useRef<HTMLInputElement>(null);
  const shown = useRef<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "checking" | "ok" | "failed">(child.photos ? "ok" : "idle");
  const [failed, setFailed] = useState<CheckName[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<Child>(child);
  const who = { ...nameCases(child.name), gender: child.gender };
  const activity = (ACTIVITY_LINES as readonly string[]).includes(productLine ?? "");
  // where this activity book prints the character (checked against the renderers, 2026-10-07)
  const places = t(
    t.has(`character.places.${productLine}`) ? `character.places.${productLine}` : "character.places.other",
  );

  useEffect(
    () => () => {
      if (shown.current) URL.revokeObjectURL(shown.current);
    },
    [],
  );

  async function choose(picked: File | undefined) {
    if (!picked) return;
    if (shown.current) URL.revokeObjectURL(shown.current);
    shown.current = URL.createObjectURL(picked); // shown from this device only, never downloaded back
    setPreview(shown.current);
    setState("checking");
    setFailed([]);
    setError(null);
    const r = await createApi.photo(child.id, picked);
    if (r.ok) {
      setSaved(r.data);
      setState("ok");
      return;
    }
    setState("failed");
    const details = r.error?.details as { reason?: string; ar?: string; en?: string } | undefined;
    setFailed(FAILS[details?.reason ?? ""] ?? []);
    const friendly = details?.ar && details?.en ? (locale === "ar" ? details.ar : details.en) : null;
    setError(friendly ?? errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  const mark = (c: CheckName) =>
    state === "ok" ? "ok" : state === "failed" ? (failed.includes(c) ? "bad" : "ok") : "wait";

  return (
    <Frame
      title={title ?? t("bookOf", who)}
      label={t("steps.photo")}
      back={back}
      footer={
        <Button onClick={() => onDone(saved)} disabled={state !== "ok"} size="lg" className="grow">
          {t("photo.cta")}
        </Button>
      }
    >
      <Lead
        title={t("photo.title")}
        body={`${activity ? t("photo.why.activity", { ...who, places }) : t("photo.why.story", who)} ${t("photo.how")}`}
      />

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
      <div className="relative flex h-[340px] items-end justify-center overflow-hidden rounded-3xl bg-[#D9D3C7]">
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element -- a local blob: preview, never uploaded anywhere else
          <img src={preview} alt="" className="absolute inset-0 size-full object-cover" />
        ) : (
          <Kid look="photo" hijab={child.hijab} hijabColor="#E9826B" outfit="#F2B33D" className="h-auto w-[290px]" />
        )}
        <svg viewBox="0 0 358 340" className="absolute inset-0 size-full" preserveAspectRatio="none" aria-hidden="true">
          <ellipse
            cx="179"
            cy="140"
            rx="84"
            ry="104"
            fill="none"
            stroke="#FFFDF8"
            strokeWidth="3"
            strokeDasharray="10 8"
          />
        </svg>
        <span className="absolute start-3.5 top-3.5 rounded-full bg-night-950/80 px-3 py-1.5 text-caption font-semibold text-paper">
          {t("photo.guide")}
        </span>
        {state !== "idle" && (
          <button
            type="button"
            onClick={() => input.current?.click()}
            disabled={state === "checking"}
            className="absolute end-2.5 top-2.5 min-h-11 rounded-full bg-paper/95 px-3.5 text-small font-semibold text-night-900"
          >
            {t("photo.change")}
          </button>
        )}
        {state === "idle" && (
          <Button onClick={() => input.current?.click()} size="lg" className="absolute bottom-6">
            {t("photo.pick")}
          </Button>
        )}
      </div>

      {state !== "idle" && (
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
      <ul className="flex flex-col gap-2.5 rounded-2xl bg-paper-sunk p-4 text-small text-ink">
        {(
          [
            ["lock", t("photo.private")],
            ["clock", t("photo.keep", who)],
            ["next", t(activity ? "photo.next.activity" : "photo.next.story", who)],
          ] as const
        ).map(([icon, text]) => (
          <li key={icon} className="flex items-start gap-2.5">
            <Icon name={icon} />
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
