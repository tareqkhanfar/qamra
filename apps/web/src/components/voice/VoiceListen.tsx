"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { MoonMark } from "@/components/Logo";
import { Spinner } from "@/components/ui/Button";
import { brandName } from "@/config/brand";
import { Link, useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { clock, voiceApi, type ListenPage } from "@/lib/voice";
import { Icon, ICONS } from "./VoicePieces";

/** The page a printed QR opens (design VoiceListen): the picture, the words, and the family's voices. */
export function VoiceListen({ token, beat }: { token: string; beat: number }) {
  const t = useTranslations("voice.listen");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [page, setPage] = useState<ListenPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pick, setPick] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState({ at: 0, of: 0 });
  const audio = useRef<HTMLAudioElement>(null);
  const retried = useRef(false);

  const load = useCallback(
    () =>
      voiceApi.listen(token, beat).then((r) => {
        if (r.ok && r.data.language !== locale) {
          router.replace(`/v/${token}/${beat}`, { locale: r.data.language }); // the book's own language
        } else if (r.ok) setPage(r.data);
        else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
        return r.ok;
      }),
    [token, beat, locale, te, router],
  );
  useEffect(() => {
    void load();
  }, [load]);

  if (!page) {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-night-950 p-6 text-center text-paper">
        {error ? (
          <>
            <h1 className="text-h3">{t("gone")}</h1>
            <p className="text-body text-ink-dark-muted">{error}</p>
            <Link href="/" className="font-bold text-amber-300">
              {t("home", { brand: brandName(locale) })}
            </Link>
          </>
        ) : (
          <Spinner />
        )}
      </main>
    );
  }

  const sources = page.voices.length
    ? page.voices.map((v) => ({ label: v.label, src: v.audio }))
    : page.narrator
      ? [{ label: t("narrator"), src: page.narrator }]
      : [];
  const current = sources[Math.min(pick, sources.length - 1)];
  const toggle = () => {
    const a = audio.current;
    if (!a) return;
    if (playing) a.pause();
    else void a.play().catch(() => setPlaying(false));
  };
  const choose = (i: number) => {
    setPick(i);
    setTime({ at: 0, of: 0 });
    requestAnimationFrame(() => void audio.current?.play().catch(() => setPlaying(false)));
  };
  const onError = () => {
    if (retried.current) return;
    retried.current = true; // a link older than 10 minutes: ask for fresh ones once
    void load();
  };
  const dir = locale === "ar" ? "rtl" : "ltr";

  return (
    <div className="mx-auto flex min-h-dvh max-w-xl flex-col bg-night-950 text-paper">
      <div className="relative aspect-square w-full bg-night-900">
        {page.image && (
          // eslint-disable-next-line @next/next/no-img-element -- a private picture streamed by the API
          <img src={page.image} alt="" width={520} height={520} className="size-full object-cover" />
        )}
        <span className="absolute start-4 top-4 rounded-full bg-night-950/80 px-3 py-1.5 text-small font-semibold">
          {t("page", { n: page.number })}
        </span>
      </div>
      <main className="relative -mt-6 flex grow flex-col gap-[18px] rounded-t-xl bg-night-950 px-5 pt-5 pb-6">
        <p
          lang={page.language}
          dir={page.language === "ar" ? "rtl" : "ltr"}
          className="font-display text-[21px] leading-[1.8] font-semibold text-night-100"
        >
          {page.text}
        </p>
        {sources.length > 1 && (
          <div role="group" aria-label={t("voices")} className="flex flex-wrap gap-2">
            {sources.map((s, i) => (
              <button
                key={s.label}
                type="button"
                aria-pressed={i === pick}
                onClick={() => choose(i)}
                className={`min-h-11 rounded-full px-4 text-[15px] ${i === pick ? "bg-amber-500 font-bold text-night-950" : "border-[1.5px] border-line-dark text-paper"}`}
              >
                {s.label}
              </button>
            ))}
          </div>
        )}
        {current ? (
          <div className="mt-auto flex items-center gap-4">
            <audio
              ref={audio}
              src={current.src}
              preload="metadata"
              onPlay={() => setPlaying(true)}
              onPause={() => setPlaying(false)}
              onEnded={() => setPlaying(false)}
              onError={onError}
              onTimeUpdate={(e) => {
                const a = e.currentTarget;
                setTime({ at: a.currentTime * 1000, of: a.duration * 1000 || 0 });
              }}
              onLoadedMetadata={(e) => {
                const of = e.currentTarget.duration * 1000 || 0;
                setTime((x) => ({ ...x, of }));
              }}
            />
            <button
              type="button"
              onClick={toggle}
              aria-label={playing ? t("pause") : t("play")}
              className="flex size-[76px] shrink-0 items-center justify-center rounded-full bg-amber-500 text-night-950"
            >
              <Icon d={playing ? ICONS.pause : ICONS.play} fill className="size-[30px] rtl:-scale-x-100" />
            </button>
            <div className="flex grow flex-col gap-1.5">
              <div className="flex h-1.5 rounded-full bg-night-800" dir={dir}>
                <div
                  className="rounded-full bg-amber-500"
                  style={{ width: `${time.of ? Math.min(100, (time.at / time.of) * 100) : 0}%` }}
                />
              </div>
              <div className="flex justify-between text-caption text-ink-dark-muted">
                <span>{t("by", { voice: current.label })}</span>
                <span dir="ltr">{`${clock(time.at)} / ${clock(time.of)}`}</span>
              </div>
            </div>
          </div>
        ) : (
          <p className="mt-auto rounded-md bg-night-900 px-4 py-3 text-body text-ink-dark-muted">{t("noVoice")}</p>
        )}
        <nav className="flex items-center justify-between border-t border-night-800 pt-3.5">
          {page.prev !== null ? (
            <Link
              href={`/v/${token}/${page.prev}`}
              className="flex min-h-11 items-center text-body font-semibold text-amber-300"
            >
              {t("prev", { n: page.number - 1 })}
            </Link>
          ) : (
            <span />
          )}
          <span className="flex items-center gap-1.5 text-caption text-ink-dark-muted">
            <MoonMark className="size-[18px]" tone="dark" />
            {brandName(locale)}
          </span>
          {page.next !== null ? (
            <Link
              href={`/v/${token}/${page.next}`}
              className="flex min-h-11 items-center text-body font-semibold text-amber-300"
            >
              {t("next", { n: page.number + 1 })}
            </Link>
          ) : (
            <span />
          )}
        </nav>
      </main>
    </div>
  );
}
