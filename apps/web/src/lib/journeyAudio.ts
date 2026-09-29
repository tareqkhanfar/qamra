/** The audio QR codes of «رحلتي الأولى للتعلّم» (API: routers/journey_audio.py). */

import { api, upload } from "@/lib/api";

export type AudioItem = {
  code: string;
  lang: "ar" | "en";
  title: string;
  show: string[];
  audio: string | null;
  source: "recording" | "narrator" | null;
};
export type AudioClip = {
  code: string;
  stage: number;
  page: number;
  title: string;
  say: string;
  show: string[];
  lang: "ar" | "en";
  tts: boolean;
  url: string;
  has_audio: boolean;
  source: string | null;
  duration_ms: number | null;
  updated_at: string | null;
  audio: string | null;
};
export type AudioClips = { stage: number; stages: number[]; items: AudioClip[] };

const enc = encodeURIComponent;

/** A file's length from its metadata (0 when the browser can't tell). */
export function audioDuration(file: File): Promise<number> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const a = new Audio();
    const done = (ms: number) => {
      URL.revokeObjectURL(url);
      resolve(Number.isFinite(ms) ? Math.round(ms) : 0);
    };
    a.preload = "metadata";
    a.onloadedmetadata = () => done(a.duration * 1000);
    a.onerror = () => done(0);
    a.src = url;
  });
}

export const journeyAudioApi = {
  item: (code: string) => api<AudioItem>(`/api/a/${enc(code)}`),
  clips: (stage: number) => api<AudioClips>(`/api/admin/journey/audio?stage=${stage}`),
  upload: (code: string, file: File, ms: number) => {
    const form = new FormData();
    form.append("file", file, file.name || "audio");
    form.append("duration_ms", String(Math.max(300, ms || 1000)));
    return upload<AudioClip>(`/api/admin/journey/audio/${enc(code)}`, form);
  },
};
