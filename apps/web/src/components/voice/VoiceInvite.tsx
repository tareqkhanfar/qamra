"use client";

import { useFormatter, useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import { voiceApi, type Invite, type VoiceBook } from "@/lib/voice";
import { Icon, ICONS } from "./VoicePieces";

const WHO = ["grandma", "grandpa", "aunt", "other"] as const;

/** Invite a grandparent to record from their own phone (design VoiceInvite): no account, 7 days, revocable. */
export function VoiceInvite({ id }: { id: string }) {
  const t = useTranslations("voice.invite");
  const te = useTranslations("errors");
  const locale = useLocale();
  const format = useFormatter();
  const router = useRouter();
  const [book, setBook] = useState<VoiceBook | null>(null);
  const [who, setWho] = useState<(typeof WHO)[number]>("grandma");
  const [name, setName] = useState("");
  const [some, setSome] = useState(false);
  const [pages, setPages] = useState<number[]>([]);
  const [made, setMade] = useState<Invite | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void voiceApi.book(id).then((r) => {
      if (r.ok) setBook(r.data);
      else if (r.status === 401) router.replace(`/login?next=${encodeURIComponent(`/books/${id}/voice/invite`)}`);
      else setError(errorText(r.error, locale, te("unknown")));
    });
  }, [id, locale, router, te]);

  const label = who === "other" || who === "aunt" ? name.trim() || t(`who.${who}`) : t(`who.${who}`);
  const url = made && typeof window !== "undefined" ? `${window.location.origin}/${locale}${made.path}` : "";
  const text = t("message", {
    ...nameCases(label, "label"),
    ...nameCases(book?.child_name ?? "", "child"),
    url: url || "…",
  });

  const create = async () => {
    setBusy(true);
    setError(null);
    const r = await voiceApi.invite(id, label, some ? pages : null);
    setBusy(false);
    if (!r.ok) return setError(errorText(r.error, locale, te("unknown")));
    setMade(r.data);
    const fresh = await voiceApi.book(id);
    if (fresh.ok) setBook(fresh.data);
  };
  const copy = async () => {
    await navigator.clipboard?.writeText(url).catch(() => undefined);
    setCopied(true);
  };
  const revoke = async (invite: Invite) => {
    const r = await voiceApi.revoke(id, invite.id);
    if (!r.ok) return setError(errorText(r.error, locale, te("unknown")));
    const fresh = await voiceApi.book(id);
    if (fresh.ok) setBook(fresh.data);
    if (made?.id === invite.id) setMade(null);
  };
  const choice = (on: boolean) =>
    `min-h-14 rounded-md text-body ${on ? "border-2 border-night-900 bg-night-100 font-bold text-night-900" : "border-[1.5px] border-line bg-paper-raised text-ink"}`;
  const radio = (on: boolean) =>
    `flex min-h-[52px] items-center gap-2.5 rounded-[14px] px-3.5 text-body ${on ? "border-2 border-night-900 bg-night-100" : "border-[1.5px] border-line bg-paper-raised"}`;

  return (
    <div className="mx-auto flex min-h-dvh max-w-xl flex-col bg-paper">
      <header className="flex h-[60px] items-center gap-2 border-b border-line px-2">
        <Link
          href={`/books/${id}/voice`}
          aria-label={t("back")}
          className="flex size-11 items-center justify-center text-night-900"
        >
          <Icon d={ICONS.back} className="size-[22px] ltr:-scale-x-100" />
        </Link>
        <h1 className="text-[20px] font-bold text-night-900">{t("title")}</h1>
      </header>
      {!book ? (
        <main className="flex grow items-center justify-center gap-3 p-6 text-ink-muted" role="status">
          {error ?? <Spinner />}
        </main>
      ) : (
        <main className="flex flex-col gap-[18px] px-4 pt-5 pb-6">
          <p className="text-body leading-[1.7] text-ink-muted">{t("lead")}</p>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-body font-semibold">{t("whoLegend")}</legend>
            <div className="grid grid-cols-2 gap-2.5">
              {WHO.map((w) => (
                <button
                  key={w}
                  type="button"
                  aria-pressed={who === w}
                  onClick={() => setWho(w)}
                  className={choice(who === w)}
                >
                  {t(`who.${w}`)}
                </button>
              ))}
            </div>
            {(who === "other" || who === "aunt") && (
              <input
                aria-label={t("name")}
                placeholder={t("namePlaceholder")}
                maxLength={30}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="min-h-12 rounded-md border-[1.5px] border-line bg-paper-raised px-4 text-body"
              />
            )}
          </fieldset>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-body font-semibold">{t("pagesLegend")}</legend>
            <label className={radio(!some)}>
              <input
                type="radio"
                name="pages"
                checked={!some}
                onChange={() => setSome(false)}
                className="size-5 accent-night-900"
              />
              {t("allPages", { n: book.pages.length })}
            </label>
            <label className={radio(some)}>
              <input
                type="radio"
                name="pages"
                checked={some}
                onChange={() => setSome(true)}
                className="size-5 accent-night-900"
              />
              {t("somePages")}
            </label>
            {some && (
              <div className="flex flex-wrap gap-2 pt-1">
                {book.pages.map((p, i) => {
                  const on = pages.includes(p.beat);
                  return (
                    <button
                      key={p.beat}
                      type="button"
                      aria-pressed={on}
                      onClick={() => setPages(on ? pages.filter((x) => x !== p.beat) : [...pages, p.beat])}
                      className={`min-h-11 min-w-11 rounded-full px-3 text-small ${on ? "bg-night-900 font-bold text-paper" : "border border-line bg-paper-raised"}`}
                    >
                      {i + 1}
                    </button>
                  );
                })}
              </div>
            )}
          </fieldset>
          <div className="rounded-[16px_16px_4px_16px] bg-success-bg px-4 py-3.5 text-body leading-[1.7] [overflow-wrap:anywhere]">
            {text}
          </div>
          {error && <Alert>{error}</Alert>}
          {!made ? (
            <button
              type="button"
              onClick={create}
              disabled={busy || (some && !pages.length)}
              className="flex min-h-14 items-center justify-center gap-2 rounded-full bg-night-900 text-body-l font-bold text-paper disabled:opacity-50"
            >
              {busy && <Spinner />}
              {t("create")}
            </button>
          ) : (
            <>
              <a
                href={`https://wa.me/?text=${encodeURIComponent(text)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex min-h-14 items-center justify-center gap-2 rounded-full bg-success text-[17px] font-bold text-white"
              >
                <Icon d="M21 12a8.5 8.5 0 0 1-12.6 7.4L3 21l1.6-5.2A8.5 8.5 0 1 1 21 12z" />
                {t("whatsapp")}
              </a>
              <button
                type="button"
                onClick={copy}
                className="min-h-12 rounded-full border-2 border-night-900 text-body font-bold text-night-900"
              >
                {copied ? t("copied") : t("copy")}
              </button>
            </>
          )}
          <Sent invites={book.invites} onRevoke={revoke} format={format} />
        </main>
      )}
    </div>
  );
}

/** «الدعوات المرسلة»: who opened their link and how many pages they recorded. */
function Sent({
  invites,
  onRevoke,
  format,
}: {
  invites: Invite[];
  onRevoke: (invite: Invite) => void;
  format: ReturnType<typeof useFormatter>;
}) {
  const t = useTranslations("voice.invite");
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-body font-bold text-night-900">{t("sent")}</h2>
      {!invites.length && <p className="text-small text-ink-muted">{t("none")}</p>}
      {invites.map((inv) => (
        <div
          key={inv.id}
          className="flex min-h-[52px] flex-wrap items-center justify-between gap-x-3 gap-y-1 rounded-[14px] border border-line bg-paper-raised px-3.5 py-2"
        >
          <strong className="text-[15px]">{inv.label}</strong>
          <span className={`text-caption font-bold ${inv.opened_at ? "text-success" : "text-amber-700"}`}>
            {!inv.active
              ? t("expired")
              : inv.opened_at
                ? t("recorded", { done: inv.recorded, total: inv.total })
                : t("notOpened")}
          </span>
          <span className="flex w-full items-center justify-between text-caption text-ink-muted">
            {inv.active && inv.expires_at
              ? t("until", { date: format.dateTime(new Date(inv.expires_at), { day: "numeric", month: "long" }) })
              : ""}
            {inv.active && (
              <button
                type="button"
                onClick={() => onRevoke(inv)}
                className="min-h-11 px-1 font-semibold text-danger underline underline-offset-4"
              >
                {t("revoke")}
              </button>
            )}
          </span>
        </div>
      ))}
    </section>
  );
}
