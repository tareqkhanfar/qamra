/**
 * Digital delivery (docs/plans/digital-delivery.md; API: routers/downloads.py): the PDFs a parent bought as files.
 *
 * A line lists the files of its books that are ready (a set: each volume as soon as it is). A file is made once,
 * for home printing, by the worker: `prepare` asks for it and answers `ready` (with its link) or `preparing`;
 * `state` follows a file being made. The link downloads it for the signed-in parent only.
 */

import { api } from "@/lib/api";

export type DownloadKind = "book" | "answer-key" | "stickers" | "card-money-recipes" | "card-games-roles";

export type DownloadFile = {
  book_id: string;
  kind: DownloadKind;
  part: string; // V1…V5 and R («قلبي يعرف الله»), 1–3 (a journey stage, a workbook volume); "" for one book
  level: string; // kg1 / kg2 («دوسية التأسيس»), else ""
  name: string; // the file's name as it downloads
};

export type DownloadLine = {
  item_id: string;
  order_code: string;
  placed_at: string;
  child_id: string;
  child_name: string;
  line: string;
  sku: string | null;
  name_ar: string;
  name_en: string;
  options: Record<string, string>;
  book_title: string | null;
  status: "ready" | "preparing"; // ready: every book of the line can be downloaded
  parts_total: number;
  parts_ready: number;
  files: DownloadFile[];
};

export type FileState = { status: "ready" | "preparing" | "failed"; name: string; url: string | null };

const lang = (locale: string) => (locale === "en" ? "en" : "ar");
const filePath = (itemId: string, file: DownloadFile) =>
  `/api/downloads/${encodeURIComponent(itemId)}/files/${encodeURIComponent(file.book_id)}/${file.kind}`;

export const downloadsApi = {
  mine: (locale: string) => api<DownloadLine[]>(`/api/downloads?lang=${lang(locale)}`),
  line: (itemId: string, locale: string) =>
    api<DownloadLine>(`/api/downloads/${encodeURIComponent(itemId)}?lang=${lang(locale)}`),
  prepare: (itemId: string, file: DownloadFile, locale: string) =>
    api<FileState>(`${filePath(itemId, file)}?lang=${lang(locale)}`, { method: "POST", json: {} }),
  state: (itemId: string, file: DownloadFile, locale: string) =>
    api<FileState>(`${filePath(itemId, file)}?lang=${lang(locale)}`),
};

/** The option that names a line's part: a journey's stage, else a volume. */
export function partOption(line: string): "stage" | "volume" {
  return line === "journey" ? "stage" : "volume";
}
