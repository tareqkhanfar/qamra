"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";
import { MoonMark } from "@/components/Logo";
import { Spinner } from "@/components/ui/Button";
import { brandName } from "@/config/brand";
import { Link } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { journeyAudioApi, type AudioItem } from "@/lib/journeyAudio";
import {
  DEFAULT_PACE,
  PACES,
  StepPlayer,
  browserClock,
  hasTimes,
  readPace,
  savePace,
  segmentAt,
  wholeSteps,
  wordStep,
  litKeys,
  partCount,
  type Pace,
  type PlayState,
} from "@/lib/journeyPlayback";

const PACE_ICON: Record<Pace, string> = { natural: "🐇", steady: "🚶", slow: "🐢" };

/** localStorage, or null where the browser blocks it (a private window, blocked site data). */
function deviceStore(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** The page a book's printed audio QR opens: the words or letters in big type and a play button. A shipped
 *  clip plays word by word with a pause between the words (lib/journeyPlayback.ts), and each shown word is a
 *  button that plays just that word. Until the item has audio it shows the words for a grown-up to read, with
 *  no error. No child data here. */
export function AudioPlayer({ code }: { code: string }) {
  const t = useTranslations("journeyAudio.player");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [item, setItem] = useState<AudioItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [state, setState] = useState<PlayState>({ playing: false, segment: null });
  // The page renders its spinner until the item loads, so reading the device's choice here never mismatches.
  const [pace, setPace] = useState<Pace>(() =>
    typeof window === "undefined" ? DEFAULT_PACE : readPace(deviceStore()),
  );
  const audio = useRef<HTMLAudioElement>(null);
  const stepper = useRef<StepPlayer | null>(null);
  const mode = useRef<"clip" | "steps">("clip"); // the clip as recorded, or pieces of it
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
  useEffect(() => () => stepper.current?.stop(), []);

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

  const lang = item.lang;
  const times = item.audio && hasTimes(item.words) ? item.words : null;
  const lit = new Set(litKeys(times, state.segment));
  // One chip per shown word, or per part of an entry the clip says part by part («أ ب ت …»).
  const chips = item.show.flatMap((word, i) => {
    const parts = word.split(" ");
    if (partCount(times, i) > 0 && partCount(times, i) === parts.length) {
      return parts.map((text, j) => ({ key: `${i}.${j}`, text, step: wordStep(times, i, pace, lang, j) }));
    }
    return [{ key: `${i}`, text: word, step: wordStep(times, i, pace, lang) }];
  });
  const tappable = chips.some((c) => c.step);
  const steps = (): StepPlayer | null => {
    const a = audio.current;
    if (!a) return null;
    stepper.current ??= new StepPlayer(a, browserClock, setState);
    return stepper.current;
  };
  const stopAll = () => {
    stepper.current?.stop();
    audio.current?.pause();
    setState({ playing: false, segment: null });
  };
  const toggle = () => {
    const a = audio.current;
    if (!a) return;
    if (state.playing) return stopAll();
    const whole = wholeSteps(times, pace, lang);
    if (whole.length > 0) {
      mode.current = "steps";
      steps()?.play(whole);
      return;
    }
    if (a.ended || mode.current === "steps") a.currentTime = 0; // after words played one by one: from the start
    mode.current = "clip";
    a.playbackRate = 1;
    void a.play().catch(() => setState({ playing: false, segment: null }));
  };
  const playWord = (key: string) => {
    const step = chips.find((c) => c.key === key)?.step;
    if (!step) return;
    audio.current?.pause();
    mode.current = "steps";
    steps()?.play([step]);
  };
  const choosePace = (next: Pace) => {
    if (state.playing) stopAll();
    setPace(next);
    savePace(deviceStore(), next);
  };
  const onClip = (playing: boolean) => {
    if (mode.current !== "clip") return; // pieces: the step player says what plays
    setState((s) => ({ playing, segment: playing ? s.segment : null }));
  };
  const onTime = () => {
    const a = audio.current;
    if (mode.current !== "clip" || !a || a.paused) return;
    const segment = segmentAt(times, a.currentTime * 1000);
    setState((s) => (s.segment === segment ? s : { ...s, segment }));
  };
  const onError = () => {
    if (retried.current) return;
    retried.current = true; // a link older than 10 minutes: ask for a fresh one once
    stopAll();
    void load();
  };
  const dir = lang === "ar" ? "rtl" : "ltr";
  const wordClass = "min-w-20 rounded-lg border-[1.5px] px-5 py-3 font-display text-[30px] leading-[1.6] font-bold";

  return (
    <div className="mx-auto flex min-h-dvh max-w-xl flex-col bg-paper">
      <main className="flex grow flex-col items-center gap-6 px-5 pt-10 pb-8 text-center">
        <p className="rounded-full bg-amber-100 px-4 py-1.5 text-small font-semibold text-amber-700">{t("kicker")}</p>
        <h1 lang={lang} dir={dir} className="font-display text-h2 font-bold text-night-900">
          {item.title}
        </h1>
        {item.show.length > 0 && (
          <ul lang={lang} dir={dir} className="flex flex-wrap justify-center gap-3">
            {chips.map(({ key, text, step }) => {
              const on = lit.has(key);
              const look = on
                ? "border-amber-500 bg-amber-100 text-night-900 shadow-md"
                : step || !tappable
                  ? "border-line bg-paper-raised text-night-900"
                  : "border-dashed border-line bg-transparent text-ink-muted"; // not playable alone: no button
              return (
                <li key={key}>
                  {step ? (
                    <button
                      type="button"
                      onClick={() => playWord(key)}
                      aria-label={t("playWord", { word: text })}
                      aria-current={on ? "true" : undefined}
                      className={`${wordClass} ${look} min-h-16 cursor-pointer transition-colors active:scale-95`}
                    >
                      {text}
                    </button>
                  ) : (
                    <span className={`${wordClass} ${look} inline-block`} aria-current={on ? "true" : undefined}>
                      {text}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        {tappable && <p className="-mt-2 text-small text-ink-muted">{t("tapWord")}</p>}
        {item.audio ? (
          <div className="mt-auto flex flex-col items-center gap-4">
            <audio
              ref={audio}
              src={item.audio}
              preload={times ? "auto" : "metadata"}
              onPlay={() => onClip(true)}
              onPause={() => onClip(false)}
              onEnded={() => onClip(false)}
              onTimeUpdate={onTime}
              onError={onError}
            />
            <button
              type="button"
              onClick={toggle}
              aria-label={state.playing ? t("pause") : t("play")}
              className="flex size-24 items-center justify-center rounded-full bg-amber-500 text-night-950 shadow-lg"
            >
              <svg viewBox="0 0 24 24" className="size-10 rtl:-scale-x-100" aria-hidden="true" fill="currentColor">
                {state.playing ? <path d="M7 5h3v14H7zM14 5h3v14h-3z" /> : <path d="M8 5v14l11-7z" />}
              </svg>
            </button>
            {times && (
              <fieldset className="flex flex-col items-center gap-2">
                <legend className="mb-2 text-small font-semibold text-night-900">{t("pace")}</legend>
                <div className="flex gap-2">
                  {PACES.map((p) => (
                    <label key={p} className="cursor-pointer">
                      <input
                        type="radio"
                        name="pace"
                        value={p}
                        checked={pace === p}
                        onChange={() => choosePace(p)}
                        className="peer sr-only"
                      />
                      <span className="flex min-h-14 min-w-24 flex-col items-center justify-center rounded-lg border-[1.5px] border-line bg-paper-raised px-3 py-2 text-small font-semibold text-night-900 peer-checked:border-amber-500 peer-checked:bg-amber-100 peer-focus-visible:outline-3 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-amber-500">
                        <span aria-hidden="true" className="text-[22px] leading-none">
                          {PACE_ICON[p]}
                        </span>
                        {t(`paces.${p}`)}
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            )}
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
