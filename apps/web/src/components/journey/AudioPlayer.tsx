"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { MoonMark } from "@/components/Logo";
import { Spinner } from "@/components/ui/Button";
import { brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { journeyAudioApi, type AudioItem } from "@/lib/journeyAudio";

/** The page a book's printed audio QR opens: the words or letters in big type and a play button. Until the
 *  item has audio it shows the words for a grown-up to read, with no error. No child data here. */
export function AudioPlayer({ code }: { code: string }) {
  const t = useTranslations("journeyAudio.player");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [item, setItem] = useState<AudioItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const audio = useRef<HTMLAudioElement>(null);
  const retried = useRef(false);

  const load = useCallback(
    () =>
      journeyAudioApi.item(code).then((r) => {
        if (r.ok) setItem(r.data);
        else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
      }),
    [code, locale, te],
  );
  useEffect(() => {
    void load();
  }, [load]);

  if (!item) {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-paper p-6 text-center">
        {error ? (
          <>
            <h1 className="text-h3 text-night-900">{t("gone")}</h1>
            <p className="text-body text-ink-muted">{error}</p>
            <Link href="/" className="font-bold text-amber-700">
              {t("home", { brand: brandName(locale) })}
            </Link>
          </>
        ) : (
          <Spinner />
        )}
      </main>
    );
  }

  const toggle = () => {
    const a = audio.current;
    if (!a) return;
    if (playing) a.pause();
    else void a.play().catch(() => setPlaying(false));
  };
  const onError = () => {
    if (retried.current) return;
    retried.current = true; // a link older than 10 minutes: ask for a fresh one once
    void load();
  };
  const dir = item.lang === "ar" ? "rtl" : "ltr";

  return (
    <div className="mx-auto flex min-h-dvh max-w-xl flex-col bg-paper">
      <main className="flex grow flex-col items-center gap-6 px-5 pt-10 pb-8 text-center">
        <p className="rounded-full bg-amber-100 px-4 py-1.5 text-small font-semibold text-amber-700">{t("kicker")}</p>
        <h1 lang={item.lang} dir={dir} className="font-display text-h2 font-bold text-night-900">
          {item.title}
        </h1>
        {item.show.length > 0 && (
          <ul lang={item.lang} dir={dir} className="flex flex-wrap justify-center gap-3">
            {item.show.map((word, i) => (
              <li
                key={`${word}-${i}`}
                className="min-w-20 rounded-lg border-[1.5px] border-line bg-paper-raised px-5 py-3 font-display text-[30px] leading-[1.6] font-bold text-night-900"
              >
                {word}
              </li>
            ))}
          </ul>
        )}
        {item.audio ? (
          <div className="mt-auto flex flex-col items-center gap-3">
            <audio
              ref={audio}
              src={item.audio}
              preload="metadata"
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onEnded={() => setPlaying(false)}
              onError={onError}
            />
            <button
              type="button"
              onClick={toggle}
              aria-label={playing ? t("pause") : t("play")}
              className="flex size-24 items-center justify-center rounded-full bg-amber-500 text-night-950 shadow-lg"
            >
              <svg viewBox="0 0 24 24" className="size-10 rtl:-scale-x-100" aria-hidden="true" fill="currentColor">
                {playing ? <path d="M7 5h3v14H7zM14 5h3v14h-3z" /> : <path d="M8 5v14l11-7z" />}
              </svg>
            </button>
            <p className="text-caption text-ink-muted">{item.source === "narrator" ? t("narrator") : t("recorded")}</p>
          </div>
        ) : (
          <p className="mt-auto rounded-md bg-paper-raised px-4 py-3 text-body text-ink-muted">{t("noAudio")}</p>
        )}
      </main>
      <footer className="flex items-center justify-center gap-1.5 border-t border-line py-3 text-caption text-ink-muted">
        <MoonMark className="size-[18px]" />
        {brandName(locale)}
      </footer>
    </div>
  );
}
