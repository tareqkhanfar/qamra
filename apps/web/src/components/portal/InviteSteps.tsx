"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { DrawLimitNote, useNow } from "@/components/create/DrawLimit";
import { Frame, Lead } from "@/components/create/Frame";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import type { Child } from "@/lib/create";
import { drawsLeft } from "@/lib/drawLimits";
import { inviteApi, type Invite } from "@/lib/portal";

const POINTS = ["p1", "p2", "p3", "p4"] as const;

/** The guardian's consent for the photo and the class book, stored with this text's version. */
export function ConsentPart({ invite, token, onDone }: { invite: Invite; token: string; onDone: (i: Invite) => void }) {
  const t = useTranslations("portal.invite.consent");
  const tc = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const who = { ...nameCases(invite.child_name), school: invite.school };

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
    <Frame
      title={invite.child_name}
      label={tc("steps.consent")}
      footer={
        <Button size="lg" className="grow" loading={busy} onClick={() => void submit()}>
          {t("cta")}
        </Button>
      }
    >
      <Lead title={t("title", who)} />
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
    </Frame>
  );
}

/**
 * The photo is kept but nothing is drawn in the class's style yet (the start of the drawing failed, or the parent
 * came back later): start it. Every later step is the create flow's own character step.
 */
export function DrawStart({
  child,
  busy,
  error,
  blockedUntil = null,
  onDraw,
}: {
  child: Child;
  busy: boolean;
  error: string | null;
  blockedUntil?: string | null; // the API said no free drawing is left until then (lib/drawLimits)
  onDraw: () => void;
}) {
  const t = useTranslations("portal.invite.character");
  const tc = useTranslations("create");
  const now = useNow();
  const out = drawsLeft(child, now, blockedUntil) <= 0;
  return (
    <Frame
      title={child.name}
      label={tc("steps.character")}
      footer={
        <Button size="lg" className="grow" loading={busy} onClick={onDraw} disabled={out}>
          {t("draw")}
        </Button>
      }
    >
      <Lead title={t("drawTitle", nameCases(child.name))} />
      {out && (
        <DrawLimitNote child={child} now={now} resetAt={blockedUntil ?? child.redraws_reset_at} earlier={false} />
      )}
      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
