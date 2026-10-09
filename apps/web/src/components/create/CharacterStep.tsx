"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { accusativeName } from "@/lib/arabicName";
import { characterImage, createApi, type Character, type Child, type Fix } from "@/lib/create";
import { ACTIVITY_LINES } from "@/lib/shop";
import { Chip, Frame, Lead } from "./Frame";

const FIXES: Fix[] = ["skin", "face", "hair", "age"];
const POLL_MS = 3000;

/**
 * Step 6 (design Create5): the drawn character; approve it, or redraw with what didn't look right. It says where
 * this product shows the character, what approving does (kept for the next books, the photo deleted within 24 h)
 * and the free-redraw rule (3 per child; a drawing that failed on our side doesn't count).
 */
export function CharacterStep({
  child,
  character,
  productLine = null,
  title,
  back,
  onChange,
  onApproved,
}: {
  child: Child;
  character: Character;
  productLine?: string | null; // classic|magic|workbook|journey|family|islamic (null: a story)
  title?: string; // the frame title; the wizard's FlowFrameContext wins when present
  back: () => void;
  onChange: (c: Character) => void;
  onApproved: (c: Character) => void;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [fixes, setFixes] = useState<Fix[]>([]);
  const [busy, setBusy] = useState<"approve" | "redraw" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const who = { name: child.name, nameAcc: accusativeName(child.name), gender: child.gender };
  const drawing = character.status === "generating";
  const kind = (ACTIVITY_LINES as readonly string[]).includes(productLine ?? "") ? "activity" : "story";
  const places = t(
    t.has(`character.places.${productLine}`) ? `character.places.${productLine}` : "character.places.other",
  );

  useEffect(() => {
    if (!drawing) return;
    const timer = setInterval(async () => {
      setTick((n) => n + 1);
      const r = await createApi.character(character.id);
      if (r.ok && r.data.status !== "generating") onChange(r.data);
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [drawing, character.id, onChange]);

  async function approve() {
    setBusy("approve");
    setError(null);
    const r = await createApi.approve(character.id);
    setBusy(null);
    if (r.ok) onApproved(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  async function redraw() {
    setBusy("redraw");
    setError(null);
    const r = await createApi.draw(child.id, character.style, character.status === "failed" ? [] : fixes);
    setBusy(null);
    if (r.ok) {
      setFixes([]);
      onChange(r.data);
    } else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  const left = Math.max(0, child.redraws_left);
  return (
    <Frame
      title={title ?? t("bookOf", { name: child.name })}
      label={t("steps.character")}
      back={back}
      footer={
        character.status === "ready" || character.status === "approved" ? (
          <div className="flex grow flex-col gap-2">
            <Button onClick={approve} loading={busy === "approve"} size="lg">
              {t("character.approve", who)}
            </Button>
            <Button onClick={redraw} loading={busy === "redraw"} variant="secondary" disabled={!left || !!busy}>
              <svg className="size-[18px]" viewBox="0 0 24 24" aria-hidden="true">
                <g fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 12a8 8 0 1 1-2.3-5.7" />
                  <path d="M20 4v5h-5" />
                </g>
              </svg>
              {t("character.redraw", { left })}
            </Button>
          </div>
        ) : character.status === "failed" ? (
          <Button onClick={redraw} loading={busy === "redraw"} size="lg" className="grow" disabled={!left}>
            {t("retry")}
          </Button>
        ) : undefined
      }
    >
      {drawing ? (
        <div role="status" className="flex flex-col items-center gap-5 py-10 text-center">
          <MoonPhase p={((tick % 12) + 1) / 12} className="size-24" />
          <h1 className="text-[26px] text-night-900">
            {t("character.drawing", { name: child.name, nameAcc: accusativeName(child.name) })}
          </h1>
          <p className="text-body text-ink-muted">{t("character.drawingHint")}</p>
        </div>
      ) : character.status === "failed" ? (
        <Alert>{t("character.failed")}</Alert>
      ) : (
        <>
          <Lead title={t("character.title", who)} body={t(`character.where.${kind}`, { ...who, places })} />
          <figure className="flex flex-col gap-2 overflow-hidden rounded-3xl border border-line bg-paper-raised p-2">
            {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API, no-store */}
            <img
              src={characterImage(character.id)}
              alt={t("character.alt", { name: child.name })}
              className="aspect-[3/2] w-full rounded-2xl object-contain"
            />
            <figcaption className="pb-1 text-center text-caption text-ink-muted">{t("character.views")}</figcaption>
          </figure>
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
