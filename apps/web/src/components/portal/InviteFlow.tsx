"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { CharacterStep, photoSavedNotice } from "@/components/create/CharacterStep";
import { FlowFrameContext } from "@/components/create/Frame";
import { PhotoStep, type PhotoChange } from "@/components/create/PhotoStep";
import { MoonMark } from "@/components/Logo";
import { Alert } from "@/components/ui/Alert";
import { Button, buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { api, errorText, type User } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import type { Character, Child } from "@/lib/create";
import { CLASS_BOOK } from "@/lib/drawings";
import { inviteApi, type Invite } from "@/lib/portal";
import { ConsentPart, DrawStart } from "./InviteSteps";

const STEPS = 3; // consent, photo, character

/**
 * A parent's invite link from the kindergarten: sign in, accept, consent, one photo, approve the drawing. The school
 * sees only which steps are done, never the photo. After the consent the steps are the create flow's own (PhotoStep,
 * CharacterStep): the photo placed in the oval, «تعديل الصورة» after the drawing, the portrait first («هل هذا
 * طفلكم؟»), every earlier drawing in the class's style to choose from, and «ما الذي لا يشبهه؟» in the parent's words.
 */
export function InviteFlow({ token }: { token: string }) {
  const t = useTranslations("portal.invite");
  const tc = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [invite, setInvite] = useState<Invite | null>(null);
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false); // «تعديل الصورة» from the character step
  const [photoSaved, setPhotoSaved] = useState<{ character: string; change: NonNullable<PhotoChange> } | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

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
  /** A drawing started or changed (a new one counts as one of the free redraws, as the API counts it). */
  const onCharacter = useCallback(
    (c: Character) =>
      setInvite((i) =>
        i?.child
          ? {
              ...i,
              child: {
                ...i.child,
                characters: [...i.child.characters.filter((x) => x.id !== c.id), c],
                redraws_left: i.child.redraws_left - (i.child.characters.some((x) => x.id === c.id) ? 0 : 1),
              },
            }
          : i,
      ),
    [],
  );
  /** Approving (maybe an earlier drawing): the child's character is now that one. */
  const onApproved = useCallback(
    (c: Character) =>
      setInvite((i) =>
        i?.child
          ? { ...i, child: { ...i.child, characters: [...i.child.characters.filter((x) => x.id !== c.id), c] } }
          : i,
      ),
    [],
  );

  /** The first drawing, in the class book's art style (the invite's own endpoint picks it). */
  async function draw() {
    setStarting(true);
    setStartError(null);
    const r = await inviteApi.draw(token);
    setStarting(false);
    if (r.ok) onCharacter(r.data);
    else setStartError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

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
            {t("title", { ...nameCases(invite.child_name), gender: invite.child_gender })}
          </h1>
          <p className="text-body-l text-ink">
            {t("lead", {
              school: invite.school,
              classroom: invite.classroom,
              ...nameCases(invite.child_name),
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
            {t("accept", nameCases(invite.child_name))}
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
  if (approved)
    return shell(
      <div className="flex flex-col gap-2 rounded-xl bg-success-bg p-5 text-success">
        <strong className="text-h3">{t("doneTitle")}</strong>
        <p className="text-body">{t("doneBody", { school: invite.school, ...nameCases(child.name) })}</p>
      </div>,
    );
  const title = t("mineTitle", nameCases(child.name));
  if (!child.consent)
    return (
      <FlowFrameContext.Provider value={{ title, n: 1, total: STEPS, close: "/account" }}>
        <ConsentPart invite={invite} token={token} onDone={setInvite} />
      </FlowFrameContext.Provider>
    );

  // the newest drawing in the class's style (the strip offers the earlier ones in that style)
  const latest = [...child.characters].reverse().find((c) => c.style === invite.style);
  const needsPhoto = (!latest || latest.status === "failed") && child.photos === 0;
  const step = needsPhoto || (editing && latest) ? 2 : 3;
  const notice =
    !editing && latest && photoSaved?.character === latest.id
      ? photoSavedNotice(tc, photoSaved.change, child.redraws_left)
      : undefined;
  const frame = { title, n: step, total: STEPS, close: "/account", notice };
  return (
    <FlowFrameContext.Provider value={frame}>
      {needsPhoto ? (
        <PhotoStep
          child={child}
          productLine={CLASS_BOOK}
          onDone={(c) => {
            setChild(c);
            void draw(); // the style is the class's: nothing to choose, the drawing starts at once
          }}
        />
      ) : editing && latest ? (
        <PhotoStep
          key="edit"
          child={child}
          productLine={CLASS_BOOK}
          edit
          back={() => setEditing(false)}
          onDone={(c, change) => {
            setChild(c);
            // a new framing or photo is drawn only by the next «أعيدوا الرسم»
            if (change) setPhotoSaved({ character: latest.id, change });
            setEditing(false);
          }}
        />
      ) : latest ? (
        <CharacterStep
          child={child}
          character={latest}
          productLine={CLASS_BOOK}
          usable={[invite.style]}
          onEditPhoto={() => setEditing(true)}
          onChange={onCharacter}
          onApproved={onApproved}
        />
      ) : (
        <DrawStart child={child} busy={starting} error={startError} onDraw={() => void draw()} />
      )}
    </FlowFrameContext.Provider>
  );
}
