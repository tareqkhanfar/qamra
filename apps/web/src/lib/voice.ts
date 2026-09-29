/** «صوت أهلي» (API: routers/voice.py and routers/voice_public.py). */

import { api, upload } from "@/lib/api";

export type Recording = { id: string; voice: string; duration_ms: number; audio: string; by_invite: boolean };
export type VoicePage = { beat: number; text: string; image: string; recordings: Recording[] };
export type Invite = {
  id: string;
  label: string;
  path: string;
  pages: number[] | null;
  expires_at: string | null;
  opened_at: string | null;
  active: boolean;
  recorded: number;
  total: number;
};
export type VoiceBook = {
  book_id: string;
  title: string;
  child_name: string;
  language: "ar" | "en";
  max_voices: number;
  voices: string[];
  listening: boolean;
  listen_url: string;
  pages: VoicePage[];
  invites: Invite[];
};
export type ElderBook = {
  label: string;
  child_name: string;
  title: string;
  language: "ar" | "en";
  expires_at: string | null;
  pages: { beat: number; text: string; audio: string | null }[];
};
export type ListenPage = {
  title: string;
  language: "ar" | "en";
  beat: number;
  number: number;
  total: number;
  prev: number | null;
  next: number | null;
  text: string;
  image: string | null;
  voices: { label: string; audio: string; duration_ms: number }[];
  narrator: string | null;
};

const enc = encodeURIComponent;
const book = (id: string) => `/api/books/${enc(id)}/voice`;

function audioForm(blob: Blob, ms: number, voice?: string): FormData {
  const form = new FormData();
  form.append("file", blob, "voice");
  form.append("duration_ms", String(Math.round(ms)));
  if (voice !== undefined) form.append("voice", voice);
  return form;
}

export const voiceApi = {
  mine: () => api<string[]>("/api/voice/books"),
  book: (id: string) => api<VoiceBook>(book(id)),
  record: (id: string, beat: number, voice: string, blob: Blob, ms: number) =>
    upload<VoiceBook>(`${book(id)}/pages/${beat}`, audioForm(blob, ms, voice)),
  remove: (id: string, recording: string) =>
    api<VoiceBook>(`${book(id)}/recordings/${enc(recording)}`, { method: "DELETE" }),
  invite: (id: string, label: string, pages: number[] | null) =>
    api<Invite>(`${book(id)}/invites`, { json: { label, pages } }),
  revoke: (id: string, invite: string) => api<void>(`${book(id)}/invites/${enc(invite)}`, { method: "DELETE" }),
  listening: (id: string, on: boolean) => api<VoiceBook>(`${book(id)}/listening`, { method: "PUT", json: { on } }),
  elder: (token: string) => api<ElderBook>(`/api/voice/invites/${enc(token)}`),
  elderRecord: (token: string, beat: number, blob: Blob, ms: number) =>
    upload<ElderBook>(`/api/voice/invites/${enc(token)}/pages/${beat}`, audioForm(blob, ms)),
  listen: (token: string, beat: number) => api<ListenPage>(`/api/voice/listen/${enc(token)}/${beat}`),
  start: (token: string) => api<{ first: number; language: "ar" | "en" }>(`/api/voice/listen/${enc(token)}`),
};

/** m:ss for timers. */
export function clock(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** The voices families use most (typed names are always allowed). */
export const SUGGESTED_VOICES = { ar: ["ماما", "بابا", "ستّي", "سيدي"], en: ["Mom", "Dad", "Grandma", "Grandpa"] };
