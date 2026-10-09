"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { accusativeName } from "@/lib/arabicName";
import { characterImage, createApi, type Character, type Child, type Fix } from "@/lib/create";
import { inviteApi, type Invite } from "@/lib/portal";

const POINTS = ["p1", "p2", "p3", "p4"] as const;
const FIXES: Fix[] = ["skin", "face", "hair", "age"];

/** The guardian's consent for the photo and the class book, stored with this text's version. */
export function ConsentPart({ invite, token, onDone }: { invite: Invite; token: string; onDone: (i: Invite) => void }) {
  const t = useTranslations("portal.invite.consent");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const who = { name: invite.child_name, school: invite.school };

  async function submit() {
    if (!accepted) return setError(t("required"));
    setBusy(true);
    setError(null);
    const r = await inviteApi.consent(token, invite.consent_version);
    setBusy(false);
    if (r.ok) onDone(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-h3 text-night-900">{t("title", who)}</h2>
      <ol className="flex flex-col gap-2">
        {POINTS.map((p, i) => (
          <li key={p} className="flex gap-3 rounded-md border border-line bg-paper-raised p-3">
            <span className="flex size-7 shrink-0 items-center justify-center rounded-sm bg-night-100 font-bold">
              {i + 1}
            </span>
            <span className="text-small">{t(p, who)}</span>
          </li>
        ))}
      </ol>
      <label
        className={`flex cursor-pointer items-start gap-3 rounded-md p-3 ${accepted ? "border-2 border-night-900 bg-night-100" : "border-[1.5px] border-line bg-paper-raised"}`}
      >
        <input
          type="checkbox"
          checked={accepted}
          onChange={(e) => setAccepted(e.target.checked)}
          className="mt-0.5 size-6 shrink-0 accent-night-900"
        />
        <span className="text-body">{t("accept", who)}</span>
      </label>
      {error && <Alert>{error}</Alert>}
      <Button size="lg" loading={busy} onClick={() => void submit()}>
        {t("cta")}
      </Button>
    </section>
  );
}

/** One clear photo, checked on the server; only our drawing step ever sees it. */
export function PhotoPart({ child, onDone }: { child: Child; onDone: (c: Child) => void }) {
  const t = useTranslations("portal.invite.photo");
  const te = useTranslations("errors");
  const locale = useLocale();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function choose(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError(null);
    const r = await createApi.photo(child.id, file);
    setBusy(false);
    if (r.ok) return onDone(r.data);
    const d = r.error?.details as { ar?: string; en?: string } | undefined;
    setError((d?.ar && d?.en ? (locale === "ar" ? d.ar : d.en) : null) ?? errorText(r.error, locale, te("unknown")));
  }

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-h3 text-night-900">{t("title", { name: child.name })}</h2>
      <p className="text-body text-ink-muted">{t("body")}</p>
      <ul className="flex flex-col gap-1 text-small">
        {(["one", "front", "light"] as const).map((k) => (
          <li key={k}>• {t(`tips.${k}`)}</li>
        ))}
      </ul>
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        aria-label={t("pick")}
        onChange={(e) => {
          void choose(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {error && <Alert>{error}</Alert>}
      <Button size="lg" loading={busy} loadingLabel={t("checking")} onClick={() => input.current?.click()}>
        {t("pick")}
      </Button>
      <p className="text-caption text-ink-muted">{t("private")}</p>
    </section>
  );
}

/** The drawing in the class's art style: draw, wait, approve or redraw (3 free redraws). */
export function CharacterPart({
  child,
  invite,
  token,
  onCharacter,
}: {
  child: Child;
  invite: Invite;
  token: string;
  onCharacter: (c: Character, drawn?: boolean) => void;
}) {
  const t = useTranslations("portal.invite.character");
  const te = useTranslations("errors");
  const locale = useLocale();
  const latest: Character | undefined = [...child.characters].reverse().find((c) => c.style === invite.style);
  const [fixes, setFixes] = useState<Fix[]>([]);
  const [busy, setBusy] = useState<"draw" | "approve" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const drawing = latest?.status === "generating";

  const latestId = latest?.id;

  useEffect(() => {
    if (!drawing || !latestId) return;
    const timer = setInterval(async () => {
      setTick((n) => n + 1);
      const r = await createApi.character(latestId);
      if (r.ok && r.data.status !== "generating") onCharacter(r.data);
    }, 3000);
    return () => clearInterval(timer);
  }, [drawing, latestId, onCharacter]);

  async function draw() {
    setBusy("draw");
    setError(null);
    const r = await inviteApi.draw(token, latest?.status === "ready" ? fixes : []);
    setBusy(null);
    if (r.ok) {
      setFixes([]);
      onCharacter(r.data, true);
    } else setError(errorText(r.error, locale, te("unknown")));
  }

  async function approve() {
    if (!latest) return;
    setBusy("approve");
    const r = await createApi.approve(latest.id);
    setBusy(null);
    if (r.ok) onCharacter(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }

  return (
    <section className="flex flex-col gap-3">
      {!latest || latest.status === "failed" ? (
        <>
          <h2 className="text-h3 text-night-900">{t("drawTitle", { name: child.name })}</h2>
          {latest?.status === "failed" && <Alert>{t("failed")}</Alert>}
          <Button size="lg" loading={busy === "draw"} onClick={() => void draw()}>
            {t("draw")}
          </Button>
        </>
      ) : drawing ? (
        <div role="status" className="flex flex-col items-center gap-4 py-8 text-center">
          <MoonPhase p={((tick % 12) + 1) / 12} className="size-20" />
          <strong className="text-h3 text-night-900">
            {t("drawing", { name: child.name, nameAcc: accusativeName(child.name) })}
          </strong>
          <p className="text-small text-ink-muted">{t("drawingHint")}</p>
        </div>
      ) : (
        <>
          <h2 className="text-h3 text-night-900">{t("title", { name: child.name })}</h2>
          {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API, no-store */}
          <img
            src={characterImage(latest.id)}
            alt={t("alt", { name: child.name })}
            className="aspect-[3/2] w-full rounded-xl border border-line bg-paper-raised object-contain"
          />
          <Button size="lg" loading={busy === "approve"} onClick={() => void approve()}>
            {t("approve")}
          </Button>
          {child.redraws_left > 0 && (
            <details className="rounded-md border border-line bg-paper-raised p-3">
              <summary className="cursor-pointer text-body font-semibold">
                {t("wrong", { gender: child.gender })}
              </summary>
              <div className="flex flex-wrap gap-2 pt-3">
                {FIXES.map((f) => (
                  <button
                    key={f}
                    type="button"
                    aria-pressed={fixes.includes(f)}
                    onClick={() => setFixes((l) => (l.includes(f) ? l.filter((x) => x !== f) : [...l, f]))}
                    className={`min-h-11 rounded-full px-4 text-small ${fixes.includes(f) ? "bg-night-900 text-paper" : "border border-line"}`}
                  >
                    {t(`fixes.${f}`)}
                  </button>
                ))}
              </div>
              <Button variant="secondary" className="mt-3" loading={busy === "draw"} onClick={() => void draw()}>
                {t("redraw", { n: child.redraws_left })}
              </Button>
            </details>
          )}
        </>
      )}
      {error && <Alert>{error}</Alert>}
    </section>
  );
}
