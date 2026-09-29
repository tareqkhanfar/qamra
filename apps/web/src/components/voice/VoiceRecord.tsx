"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { clock, SUGGESTED_VOICES, voiceApi, type VoiceBook } from "@/lib/voice";
import { RecordPanel } from "./RecordPanel";
import { Dots, Icon, ICONS, VoiceChips } from "./VoicePieces";

/** «صوت أهلي» for the parent (design VoiceRecord): large text, one page at a time, up to three voices a page. */
export function VoiceRecord({ id }: { id: string }) {
  const t = useTranslations("voice.record");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [book, setBook] = useState<VoiceBook | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [voice, setVoice] = useState<string>("");
  const [notice, setNotice] = useState<string | null>(null);
  const top = useRef<HTMLDivElement>(null);

  const fail = useCallback(
    (e: Parameters<typeof errorText>[0], status: number) =>
      setError(errorText(e, locale, status === 0 ? te("network") : te("unknown"))),
    [locale, te],
  );

  useEffect(() => {
    let alive = true;
    void voiceApi.book(id).then((r) => {
      if (!alive) return;
      if (r.ok) {
        setBook(r.data);
        setVoice((v) => v || r.data.voices[0] || SUGGESTED_VOICES[locale === "ar" ? "ar" : "en"][0]);
        const first = r.data.pages.findIndex((p) => p.recordings.length === 0);
        setIndex(first < 0 ? 0 : first);
      } else if (r.status === 401) router.replace(`/login?next=${encodeURIComponent(`/books/${id}/voice`)}`);
      else fail(r.error, r.status);
    });
    return () => {
      alive = false;
    };
  }, [id, locale, router, fail]);

  if (error && !book) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-4 p-6 text-center">
        <p className="text-body-l">{error}</p>
        <Link href="/account" className="font-bold text-night-900 underline underline-offset-4">
          {t("back")}
        </Link>
      </main>
    );
  }
  if (!book) {
    return (
      <main className="flex min-h-dvh items-center justify-center gap-3 text-ink-muted" role="status">
        <Spinner /> {t("loading")}
      </main>
    );
  }

  const page = book.pages[index];
  const done = book.pages.map((p) => p.recordings.length > 0);
  const voices = [...new Set([...book.voices, ...SUGGESTED_VOICES[locale === "ar" ? "ar" : "en"], voice])];
  const mine = page?.recordings.find((r) => r.voice === voice) ?? null;
  const full = !mine && (page?.recordings.length ?? 0) >= book.max_voices;
  const go = (i: number) => {
    setIndex(i);
    setNotice(null);
    top.current?.scrollIntoView({ block: "start" });
  };

  return (
    <div ref={top} className="mx-auto flex min-h-dvh max-w-xl flex-col bg-paper">
      <header className="flex flex-col gap-2 border-b border-line px-2 pt-1 pb-3">
        <div className="flex h-[52px] items-center justify-between gap-2">
          <Link
            href="/account"
            aria-label={t("close")}
            className="flex size-11 items-center justify-center text-night-900"
          >
            <Icon d={ICONS.close} className="size-[22px]" />
          </Link>
          <strong className="min-w-0 truncate text-body">{t("title", { title: book.title })}</strong>
          <Link
            href={`/books/${id}/voice/invite`}
            className="flex min-h-11 items-center px-2 text-small font-bold text-amber-700"
          >
            {t("invite")}
          </Link>
        </div>
        <Dots
          done={done}
          current={index}
          label={t("progress", { done: done.filter(Boolean).length, total: book.pages.length })}
        />
      </header>

      {!page ? (
        <p className="p-6 text-center text-body-l">{t("empty")}</p>
      ) : (
        <main className="flex grow flex-col gap-4 px-4 pt-4 pb-6">
          <div className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element -- a private picture streamed by the API */}
            <img
              src={page.image}
              alt=""
              width={72}
              height={72}
              className="size-[72px] shrink-0 rounded-[10px] bg-night-100 object-cover"
            />
            <div className="flex flex-col gap-0.5">
              <strong className="text-[15px]">{t("pageOf", { n: index + 1, total: book.pages.length })}</strong>
              <span className="text-caption text-ink-muted">{t("hint")}</span>
            </div>
          </div>
          <p
            lang={book.language}
            className="rounded-lg border border-line bg-paper-raised px-5 py-[18px] font-display text-[26px] leading-[1.8] font-semibold"
          >
            {page.text}
          </p>
          <VoiceChips
            voices={voices}
            active={voice}
            onPick={(v) => {
              setVoice(v);
              setNotice(null);
            }}
            labels={{
              legend: t("who"),
              other: t("other"),
              name: t("otherLabel"),
              placeholder: t("otherPlaceholder"),
              add: t("add"),
            }}
          />
          {notice && <Alert tone="success">{notice}</Alert>}
          {error && <Alert tone="error">{error}</Alert>}
          {full ? (
            <Alert tone="info">{t("full")}</Alert>
          ) : (
            <RecordPanel
              key={`${page.beat}:${voice}`}
              saved={mine}
              last={index + 1 >= book.pages.length}
              nextNumber={index + 2}
              onSave={async (blob, ms) => {
                setError(null);
                const r = await voiceApi.record(id, page.beat, voice, blob, ms);
                if (!r.ok) return fail(r.error, r.status);
                setBook(r.data);
                if (index + 1 < book.pages.length) go(index + 1);
                else setNotice(t("saved"));
              }}
              onNext={() => (index + 1 < book.pages.length ? go(index + 1) : setNotice(t("allDone")))}
            />
          )}
          <PageVoices
            book={book}
            beat={page.beat}
            onDelete={async (rec) => {
              const r = await voiceApi.remove(id, rec);
              if (r.ok) setBook(r.data);
              else fail(r.error, r.status);
            }}
          />
          <nav className="flex justify-between border-t border-line pt-3 text-small font-semibold">
            <button
              type="button"
              disabled={index === 0}
              onClick={() => go(index - 1)}
              className="min-h-11 px-1 disabled:opacity-40"
            >
              {t("prev")}
            </button>
            <button
              type="button"
              disabled={index + 1 >= book.pages.length}
              onClick={() => go(index + 1)}
              className="min-h-11 px-1 disabled:opacity-40"
            >
              {t("next")}
            </button>
          </nav>
          <ListeningSwitch book={book} onChange={setBook} onError={fail} />
        </main>
      )}
    </div>
  );
}

/** «على هذه الصفحة»: the voices already recorded here, each playable and deletable. */
function PageVoices({ book, beat, onDelete }: { book: VoiceBook; beat: number; onDelete: (id: string) => void }) {
  const t = useTranslations("voice.record");
  const recs = book.pages.find((p) => p.beat === beat)?.recordings ?? [];
  if (!recs.length) return null;
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-small font-semibold text-ink-muted">{t("onPage")}</h2>
      <ul className="flex flex-col gap-2">
        {recs.map((r) => (
          <li key={r.id} className="flex items-center gap-3 rounded-sm border border-line bg-paper-raised px-3 py-2">
            <strong className="grow text-[15px]">
              {r.voice}
              {r.by_invite && <span className="ms-2 text-caption font-normal text-ink-muted">{t("byInvite")}</span>}
            </strong>
            <span className="text-caption text-ink-muted tabular-nums" dir="ltr">
              {clock(r.duration_ms)}
            </span>
            <audio src={r.audio} controls preload="none" className="h-9 max-w-[140px]" />
            <button
              type="button"
              onClick={() => onDelete(r.id)}
              aria-label={t("delete", { voice: r.voice })}
              className="flex size-11 items-center justify-center text-danger"
            >
              <Icon d={ICONS.trash} />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Pause or resume the printed codes, with the real-voices promise. */
function ListeningSwitch({
  book,
  onChange,
  onError,
}: {
  book: VoiceBook;
  onChange: (b: VoiceBook) => void;
  onError: (e: Parameters<typeof errorText>[0], status: number) => void;
}) {
  const t = useTranslations("voice.record");
  const [busy, setBusy] = useState(false);
  const toggle = async () => {
    setBusy(true);
    const r = await voiceApi.listening(book.book_id, !book.listening);
    setBusy(false);
    if (r.ok) onChange(r.data);
    else onError(r.error, r.status);
  };
  return (
    <section className="flex flex-col gap-2 rounded-md bg-paper-sunk px-4 py-3 text-small">
      <p className={book.listening ? "text-success" : "text-warning"}>
        {book.listening ? t("listeningOn") : t("listeningOff")}
      </p>
      <button
        type="button"
        disabled={busy}
        onClick={toggle}
        className="min-h-11 self-start font-bold text-night-900 underline underline-offset-4"
      >
        {book.listening ? t("pause") : t("resume")}
      </button>
      <p className="text-caption text-ink-muted">{t("realVoice")}</p>
    </section>
  );
}
