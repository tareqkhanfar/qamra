/** The free cover (Addendum 9): one small watermarked cover from a story's Classic template, drawn in a minute. */
import { api } from "@/lib/api";

export type FreeCover = {
  id: string;
  status: "drawing" | "ready" | "failed";
  child_id: string;
  child_name: string;
  theme: string;
  ready: boolean;
};

export const freeCoverApi = {
  request: (childId: string, theme: string, lang: string) =>
    api<FreeCover>("/api/free-covers", { json: { child_id: childId, theme, lang } }),
  get: (id: string) => api<FreeCover>(`/api/free-covers/${id}`),
};

/** The drawn cover or its story-size copy: never the original photo. */
export const coverImage = (id: string, name: "cover.jpg" | "story.jpg", download = false) =>
  `/api/free-covers/${id}/${name}${download ? "?download=true" : ""}`;

/** Share the image itself where the phone allows it (WhatsApp is in the share sheet); else a WhatsApp text. */
export async function shareImage(url: string, fileName: string, text: string): Promise<"shared" | "link"> {
  let file: File | null = null;
  try {
    const res = await fetch(url, { credentials: "same-origin", headers: { "X-Qamra-Client": "web" } });
    if (res.ok) file = new File([await res.blob()], fileName, { type: "image/jpeg" });
  } catch {
    file = null;
  }
  if (file && typeof navigator !== "undefined" && navigator.canShare?.({ files: [file] })) {
    try {
      await navigator.share({ files: [file], text });
    } catch {
      /* the parent closed the share sheet */
    }
    return "shared";
  }
  window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener");
  return "link";
}
