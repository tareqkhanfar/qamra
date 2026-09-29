"use client";

import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { Spinner } from "@/components/ui/Button";
import { clock, type Recording } from "@/lib/voice";
import { useRecorder } from "./useRecorder";
import { Icon, ICONS, Wave } from "./VoicePieces";

type Props = {
  saved: Recording | null; // this voice's recording of the page, if any
  last: boolean;
  nextNumber: number;
  onSave: (blob: Blob, ms: number) => Promise<void>;
  onNext: () => void;
};

/** Record / listen / record again for one voice on one page (design VoiceRecord, bottom half). */
export function RecordPanel({ saved, last, nextNumber, onSave, onNext }: Props) {
  const t = useTranslations("voice.record");
  const rec = useRecorder();
  const player = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [saving, setSaving] = useState(false);
  const recording = rec.state === "recording";
  const source = rec.url ?? saved?.audio ?? null;

  const listen = () => {
    const a = player.current;
    if (!a || !source) return;
    if (playing) a.pause();
    else void a.play().catch(() => setPlaying(false));
  };
  const again = () => {
    player.current?.pause();
    rec.reset();
    void rec.start();
  };
  const save = async () => {
    if (!rec.blob) return;
    setSaving(true);
    await onSave(rec.blob, rec.ms);
    setSaving(false);
  };
  const round =
    "flex size-12 items-center justify-center rounded-full border-[1.5px] border-line bg-paper-raised text-night-900";

  return (
    <>
      <div role="status" className="flex flex-col gap-2.5 rounded-lg bg-night-900 px-4 py-3.5">
        <div className="flex justify-between text-small text-paper">
          <span className="flex items-center gap-1.5">
            <span
              className={`size-2.5 rounded-full ${recording ? "bg-coral-300" : rec.blob || saved ? "bg-success" : "bg-line-dark"}`}
            />
            {recording ? t("recording") : rec.blob || saved ? t("recorded") : t("ready")}
          </span>
          <span dir="ltr" className="tabular-nums">
            {clock(recording || rec.blob ? rec.ms : (saved?.duration_ms ?? 0))}
          </span>
        </div>
        <Wave levels={rec.levels} bars={rec.bars} />
      </div>
      {rec.error && (
        <p role="alert" className="text-small text-danger">
          {rec.error === "denied" ? t("micDenied") : t("unsupported")}
        </p>
      )}
      {/* the recording itself, played back as it is */}
      <audio
        ref={player}
        src={source ?? undefined}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />

      <div className="mt-auto flex items-center justify-between px-3">
        <button
          type="button"
          onClick={again}
          disabled={recording || (!rec.blob && !saved)}
          className="flex min-h-16 w-16 flex-col items-center gap-1 text-caption text-night-900 disabled:opacity-40"
        >
          <span className={round}>
            <Icon d={ICONS.again} />
          </span>
          {t("again")}
        </button>
        <button
          type="button"
          onClick={() => (recording ? rec.stop() : void rec.start())}
          disabled={rec.state === "starting"}
          aria-label={recording ? t("stop") : t("start")}
          className="relative flex size-[88px] items-center justify-center rounded-full border-[6px] border-danger-bg bg-danger text-white"
        >
          {recording && (
            <span
              aria-hidden="true"
              className="absolute -inset-1.5 animate-ping rounded-full bg-danger/30 motion-reduce:hidden"
            />
          )}
          {recording ? <span className="size-7 rounded-[6px] bg-white" /> : <Icon d={ICONS.mic} className="size-9" />}
        </button>
        <button
          type="button"
          onClick={listen}
          disabled={!source || recording}
          className="flex min-h-16 w-16 flex-col items-center gap-1 text-caption text-night-900 disabled:opacity-40"
        >
          <span className={round}>
            <Icon d={playing ? ICONS.pause : ICONS.play} fill className="size-5 rtl:-scale-x-100" />
          </span>
          {t("listen")}
        </button>
      </div>

      {rec.blob ? (
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="flex min-h-[52px] items-center justify-center gap-2 rounded-full bg-night-900 text-body font-bold text-paper"
        >
          {saving && <Spinner />}
          {saving ? t("saving") : last ? t("saveLast") : t("save", { n: nextNumber })}
        </button>
      ) : (
        <button
          type="button"
          onClick={onNext}
          disabled={recording || !saved}
          className="flex min-h-[52px] items-center justify-center rounded-full border-2 border-night-900 text-body font-bold text-night-900 disabled:border-line disabled:text-ink-faint"
        >
          {last ? t("finish") : t("next")}
        </button>
      )}
    </>
  );
}
