"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { errorText } from "@/lib/api";
import { audioDuration, journeyAudioApi, type AudioClip, type AudioClips } from "@/lib/journeyAudio";

/** Staff: the audio items of a stage (Addendum 6 §4.8), each with its script, its QR link and its recording:
 *  upload or replace a file, then play it. Items without audio play the TTS fallback when one is switched on,
 *  otherwise the public player shows their words. */
export function AdminJourneyAudio() {
  const t = useTranslations("journeyAudio.admin");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [stage, setStage] = useState(1);
  const [data, setData] = useState<AudioClips | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ code: string; ok: boolean; text: string } | null>(null);

  const load = useCallback(
    (s: number) =>
      journeyAudioApi.clips(s).then((r) => {
        if (r.ok) setData(r.data);
        else setError(errorText(r.error, locale, te("unknown")));
      }),
    [locale, te],
  );
  useEffect(() => {
    void load(stage);
  }, [load, stage]);

  const send = async (item: AudioClip, file: File | undefined) => {
    if (!file) return;
    setBusy(item.code);
    setNotice(null);
    const r = await journeyAudioApi.upload(item.code, file, await audioDuration(file));
    setBusy(null);
    if (r.ok) {
      setData((d) => (d ? { ...d, items: d.items.map((i) => (i.code === item.code ? r.data : i)) } : d));
      setNotice({ code: item.code, ok: true, text: t("saved") });
    } else setNotice({ code: item.code, ok: false, text: errorText(r.error, locale, te("unknown")) });
  };

  if (error) return <Alert>{error}</Alert>;
  if (!data) return <p className="text-ink-muted">{t("loading")}</p>;
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-h2 text-night-900 md:text-h1">{t("title")}</h1>
        <p className="max-w-3xl text-body text-ink-muted">{t("intro")}</p>
      </header>
      <div role="group" aria-label={t("stage")} className="flex gap-2">
        {[1, 2, 3].map((s) => (
          <button
            key={s}
            type="button"
            aria-pressed={s === stage}
            disabled={!data.stages.includes(s)}
            onClick={() => setStage(s)}
            className={`min-h-11 rounded-full px-4 font-semibold disabled:opacity-40 ${s === stage ? "bg-night-900 text-paper" : "border border-line"}`}
          >
            {t("stageN", { n: s })}
          </button>
        ))}
      </div>
      {data.items.length === 0 && <p className="text-ink-muted">{t("empty")}</p>}
      <ul className="flex flex-col gap-3">
        {data.items.map((item) => (
          <li
            key={item.code}
            className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-4 md:flex-row md:items-center"
          >
            <div className="flex grow flex-col gap-1">
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-caption font-bold text-amber-700">
                  {t("page", { n: item.page })}
                </span>
                <h2 lang={item.lang} className="text-body font-bold text-night-900">
                  {item.title}
                </h2>
                <code className="text-caption text-ink-muted" dir="ltr">
                  {item.url}
                </code>
              </div>
              <p lang={item.lang} className="text-small text-ink">
                <span className="font-semibold">{t("say")}: </span>
                {item.say}
              </p>
              <p className="text-caption text-ink-muted">
                {item.has_audio
                  ? t(item.source === "upload" ? "recorded" : "narrated", {
                      s: ((item.duration_ms ?? 0) / 1000).toFixed(1),
                    })
                  : item.tts
                    ? t("missingTts")
                    : t("missing")}
              </p>
              {notice?.code === item.code && (
                <p role="status" className={`text-small ${notice.ok ? "text-success" : "text-danger"}`}>
                  {notice.text}
                </p>
              )}
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-3">
              {item.audio && <audio controls preload="none" src={item.audio} className="h-11 max-w-60" />}
              <label className="flex min-h-11 cursor-pointer items-center rounded-full bg-night-900 px-4 font-semibold text-paper">
                {busy === item.code
                  ? t("uploading")
                  : item.has_audio && item.source === "upload"
                    ? t("replace")
                    : t("upload")}
                <input
                  type="file"
                  accept="audio/*"
                  className="sr-only"
                  disabled={busy !== null}
                  onChange={(e) => void send(item, e.currentTarget.files?.[0])}
                />
              </label>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
