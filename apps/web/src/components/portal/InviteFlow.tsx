"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { MoonMark } from "@/components/Logo";
import { Alert } from "@/components/ui/Alert";
import { Button, buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { api, errorText, type User } from "@/lib/api";
import { accusativeName } from "@/lib/arabicName";
import type { Character, Child } from "@/lib/create";
import { inviteApi, type Invite } from "@/lib/portal";
import { CharacterPart, ConsentPart, PhotoPart } from "./InviteSteps";

/** A parent's invite link from the kindergarten: sign in, accept, consent, one photo, approve the drawing.
 * The school sees only which steps are done — never the photo. */
export function InviteFlow({ token }: { token: string }) {
  const t = useTranslations("portal.invite");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [invite, setInvite] = useState<Invite | null>(null);
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [i, me] = await Promise.all([inviteApi.open(token), api<User>("/api/auth/me")]);
    setUser(me.ok ? me.data : null);
    if (i.ok) setInvite(i.data);
    else setError(errorText(i.error, locale, i.status === 0 ? te("network") : te("unknown")));
  }, [locale, te, token]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  async function claim() {
    setBusy(true);
    setError(null);
    const r = await inviteApi.claim(token);
    setBusy(false);
    if (r.ok) setInvite(r.data);
    else setError(errorText(r.error, locale, te("unknown")));
  }

  const setChild = (child: Child) => setInvite((i) => (i ? { ...i, child } : i));
  const onCharacter = useCallback(
    (c: Character, drawn = false) =>
      setInvite((i) =>
        i?.child
          ? {
              ...i,
              child: {
                ...i.child,
                characters: [...i.child.characters.filter((x) => x.id !== c.id), c],
                redraws_left: i.child.redraws_left - (drawn ? 1 : 0),
              },
            }
          : i,
      ),
    [],
  );
  const shell = (body: React.ReactNode) => (
    <div className="mx-auto flex min-h-dvh w-full max-w-[560px] flex-col gap-5 bg-paper px-4 py-8">
      <div className="flex items-center gap-2">
        <MoonMark className="size-8" />
        {invite && <span className="text-small text-ink-muted">{t("from", { school: invite.school })}</span>}
      </div>
      {body}
      {error && <Alert>{error}</Alert>}
    </div>
  );

  if (!invite || user === undefined)
    return shell(error ? null : <div className="h-64 animate-pulse rounded-xl bg-paper-sunk" aria-busy="true" />);
  if (invite.state === "expired" || invite.state === "taken")
    return shell(
      <div className="flex flex-col gap-2">
        <h1 className="text-h2 text-night-900">{t(`${invite.state}Title`)}</h1>
        <p className="text-body text-ink-muted">{t(`${invite.state}Body`, { school: invite.school })}</p>
      </div>,
    );
  const theme = locale === "ar" ? invite.theme_ar : invite.theme_en;
  if (invite.state === "open") {
    const next = encodeURIComponent(`/invite/${token}`);
    return shell(
      <>
        <div className="flex flex-col gap-2">
          <h1 className="text-h2 text-night-900">
            {t("title", { name: invite.child_name, gender: invite.child_gender })}
          </h1>
          <p className="text-body-l text-ink">
            {t("lead", {
              school: invite.school,
              classroom: invite.classroom,
              name: invite.child_name,
              nameAcc: accusativeName(invite.child_name),
              gender: invite.child_gender,
              theme: theme ?? t("classBook"),
            })}
          </p>
        </div>
        <ul className="flex flex-col gap-2 text-body">
          {(["p1", "p2", "p3"] as const).map((p) => (
            <li key={p} className="flex gap-2 rounded-md border border-line bg-paper-raised p-3">
              <span aria-hidden="true">✓</span>
              {t(`promise.${p}`)}
            </li>
          ))}
        </ul>
        {user ? (
          <Button size="lg" loading={busy} onClick={() => void claim()}>
            {t("accept", { name: invite.child_name })}
          </Button>
        ) : (
          <div className="flex flex-col gap-2">
            <Link href={`/register?next=${next}`} className={buttonClasses("primary", "lg")}>
              {t("register")}
            </Link>
            <Link href={`/login?next=${next}`} className={buttonClasses("secondary", "lg")}>
              {t("login")}
            </Link>
          </div>
        )}
      </>,
    );
  }
  const child = invite.child;
  if (!child) return shell(null);
  const approved = child.characters.some((c) => c.approved && c.style === invite.style);
  return shell(
    <>
      <h1 className="text-h2 text-night-900">{t("mineTitle", { name: child.name })}</h1>
      <ol className="flex gap-1.5" aria-label={t("stepsLabel")}>
        {[child.consent, child.photos > 0 || approved, approved].map((on, i) => (
          <li key={i} className={`h-2 flex-1 rounded-full ${on ? "bg-night-900" : "bg-line"}`} />
        ))}
      </ol>
      {!child.consent ? (
        <ConsentPart invite={invite} token={token} onDone={setInvite} />
      ) : approved ? (
        <div className="flex flex-col gap-2 rounded-xl bg-success-bg p-5 text-success">
          <strong className="text-h3">{t("doneTitle")}</strong>
          <p className="text-body">{t("doneBody", { school: invite.school, name: child.name })}</p>
        </div>
      ) : child.photos === 0 && !child.characters.some((c) => c.status !== "failed") ? (
        <PhotoPart child={child} onDone={setChild} />
      ) : (
        <CharacterPart child={child} invite={invite} token={token} onCharacter={onCharacter} />
      )}
    </>,
  );
}
