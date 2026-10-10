/** The web reader and share links (API: routers/reader.py). */

import { api } from "@/lib/api";

export type ReaderPage = { beat: number; text: string | null; layout: string | null; image: string | null };

export type Share = { id: string; token: string; expires_at: string | null; created_at: string };

export type ReaderBook = {
  title: string;
  language: "ar" | "en";
  kind: "preview" | "final";
  pages: ReaderPage[];
};

export type OwnerBook = ReaderBook & {
  id: string;
  child_id: string;
  child_name: string;
  can_share: boolean;
  share: Share | null;
};

export type SharedBook = ReaderBook & { expires_at: string | null; hero_gender: "m" | "f" | null };

export const SHARE_DAYS = [7, 30, 90] as const;

export const readerApi = {
  book: (id: string) => api<OwnerBook>(`/api/books/${encodeURIComponent(id)}/reader`),
  shared: (token: string) => api<SharedBook>(`/api/shared/${encodeURIComponent(token)}`),
  share: (id: string, days: (typeof SHARE_DAYS)[number]) =>
    api<Share>(`/api/books/${encodeURIComponent(id)}/share`, { json: { days } }),
  revoke: (id: string, shareId: string) =>
    api<void>(`/api/books/${encodeURIComponent(id)}/share/${encodeURIComponent(shareId)}`, { method: "DELETE" }),
};

/** The public address of a share link, in the viewer's language. */
export function shareUrl(token: string, locale: string): string {
  const origin = typeof window === "undefined" ? "" : window.location.origin;
  return `${origin}/${locale}/s/${token}`;
}

/** Books a parent can open in the reader (the rest continue in the create flow or wait). A finished book opens
 * once our team confirmed its text (`in_review` waits for that: API routers/reader.py). */
export const READABLE = new Set(["preview", "approved", "ordered", "printed"]);
