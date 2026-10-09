"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { MoonMark } from "@/components/Logo";
import { Spinner } from "@/components/ui/Button";
import { brandName } from "@/config/brand";
import { errorText } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import { voiceApi, type ElderBook } from "@/lib/voice";
import { useRecorder } from "./useRecorder";
import { Icon, ICONS } from "./VoicePieces";

/** A grandparent's recording link (design VoiceElder): no account, very large text, one big button.
 * Stopping saves the recording at once; pressing again records the page again. */
export function VoiceElder({ token }: { token: string }) {
  const t = useTranslations("voice.elder");
  const te = useTranslations("errors");
  const locale = useLocale();
  const rec = useRecorder();
  const [book, setBook] = useState<ElderBook | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [index, setIndex] = useState(0);
  const [saving, setSaving] = useState(false);
  const [playing, setPlaying] = useState(false);
  const player = useRef<HTMLAudioElement>(null);
  const sent = useRef<Blob | null>(null);

  useEffect(() => {
    void voiceApi.elder(token).then((r) => {
      if (r.ok) {
        setBook(r.data);
        const first = r.data.pages.findIndex((p) => !p.audio);
        setIndex(first < 0 ? 0 : first);
      } else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    });
  }, [token, locale, te]);

  const page = book?.pages[index];
  useEffect(() => {
    if (!book || !page || !rec.blob || sent.current === rec.blob) return;
    sent.current = rec.blob;
    setSaving(true);
    void voiceApi.elderRecord(token, page.beat, rec.blob, rec.ms).then((r) => {
      setSaving(false);
      if (r.ok) setBook(r.data);
      else setError(errorText(r.error, locale, te("unknown")));
    });
  }, [book, page, rec.blob, rec.ms, token, locale, te]);

  if (!book || !page) {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-paper p-6 text-center">
        {error ? (
          <>
            <h1 className="text-h2 text-night-900">{t("gone")}</h1>
            <p className="text-body-l">{error}</p>
          </>
        ) : (
          <Spinner />
        )}
      </main>
    );
  }

  const recording = rec.state === "recording";
  const done = book.pages.every((p) => p.audio);
  const move = (i: number) => {
    player.current?.pause();
    rec.reset();
    setError(null);
    setIndex(i);
  };
  const listen = () => {
    const a = player.current;
    if (!a) return;
    if (playing) a.pause();
    else void a.play().catch(() => setPlaying(false));
  };

  return (
    <main lang={book.language} className="mx-auto flex min-h-dvh max-w-xl flex-col gap-[18px] bg-paper px-5 pt-5 pb-7">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2">
          <MoonMark className="size-[34px]" />
          <span className="font-display text-[22px] font-extrabold text-night-900">{brandName(locale)}</span>
        </span>
        <span className="text-[20px] font-bold text-night-900">
          {t("pageOf", { n: index + 1, total: book.pages.length })}
        </span>
      </div>
      <h1 className="text-[30px] leading-[1.35] font-bold text-night-900">
        {t("hello", { ...nameCases(book.label, "label"), ...nameCases(book.child_name, "child") })}
      </h1>
      <p className="rounded-xl border-2 border-line bg-white p-5 font-display text-[30px] leading-[1.8] font-semibold">
        {page.text}
      </p>
      <div className="flex grow flex-col items-center justify-center gap-3.5 py-2">
        <button
          type="button"
          onClick={() => (recording ? rec.stop() : void rec.start())}
          disabled={saving || rec.state === "starting"}
          aria-label={recording ? t("stop") : t("press")}
          className="relative flex size-[132px] items-center justify-center rounded-full border-8 border-danger-bg bg-danger text-white disabled:opacity-60"
        >
          {recording && (
            <span
              aria-hidden="true"
              className="absolute -inset-2 animate-ping rounded-full bg-danger/25 motion-reduce:hidden"
            />
          )}
          {recording ? <span className="size-11 rounded-[8px] bg-white" /> : <Icon d={ICONS.mic} className="size-14" />}
        </button>
        <span role="status" className="flex items-center gap-2 text-[24px] font-bold text-night-900">
          {saving && <Spinner />}
          {saving ? t("saving") : recording ? t("stop") : page.audio ? t("saved") : t("press")}
        </span>
        {rec.error && (
          <p className="text-center text-body-l text-danger">
            {rec.error === "denied" ? t("micDenied") : t("unsupported")}
          </p>
        )}
        {error && <p className="text-center text-body-l text-danger">{error}</p>}
        {done && <p className="text-center text-body-l text-success">{t("done", { child: book.child_name })}</p>}
      </div>
      <audio
        ref={player}
        src={page.audio ?? undefined}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={listen}
          disabled={!page.audio || recording}
          className="min-h-[72px] rounded-lg border-2 border-line bg-paper-raised text-[22px] font-bold text-ink-muted disabled:opacity-50"
        >
          {playing ? t("pause") : t("listen")}
        </button>
        <button
          type="button"
          onClick={() => move(index + 1 < book.pages.length ? index + 1 : 0)}
          disabled={recording || saving}
          className="min-h-[72px] rounded-lg bg-night-900 text-[22px] font-bold text-paper disabled:opacity-50"
        >
          {index + 1 < book.pages.length ? t("next") : t("first")}
        </button>
      </div>
      {index > 0 && (
        <button
          type="button"
          onClick={() => move(index - 1)}
          className="min-h-12 text-body-l font-semibold text-night-900 underline underline-offset-4"
        >
          {t("prev")}
        </button>
      )}
    </main>
  );
}
