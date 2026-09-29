/** The parent create flow (design Create1–Create11): the child, consent, photo, character, story, preview. */
import { api, upload } from "@/lib/api";
import type { CustomBriefBody } from "@/lib/customStory";
import type { Cart } from "@/lib/store";

export type Line = "classic" | "magic";

export type Character = {
  id: string;
  status: "generating" | "ready" | "approved" | "failed";
  style: string;
  approved: boolean;
};
export type Child = {
  id: string;
  name: string;
  gender: "m" | "f";
  age: number;
  hijab: boolean;
  glasses: boolean;
  consent: boolean;
  photos: number;
  characters: Character[];
  redraws_left: number;
};
export type ChildInput = {
  name: string;
  gender: "m" | "f";
  age: number;
  interests: string[];
  note?: string;
  hijab: boolean;
  glasses: boolean;
};
export type BookPage = { beat: number; text: string | null; image: boolean };
export type Book = {
  id: string;
  status: "draft" | "generating" | "preview" | "approved" | "ordered" | "printed" | "failed" | "in_review";
  line: Line;
  theme: string;
  style: string;
  title: string | null;
  dedication: string | null;
  preview: boolean;
  progress: { done?: number; total?: number };
  pages: BookPage[];
  custom?: boolean; // «حكاية خاصة»: sold as magic-custom-story
  companion?: { id: string; name: string } | null; // the child's drawn companion
  problem?: "brief_unsafe" | null; // why the book stopped, when the parent can fix it
};
export type Fix = "skin" | "face" | "hair" | "age";
export type StartBook = {
  child_id: string;
  character_id: string;
  theme: string;
  line: Line;
  dedication?: string;
  companion_id?: string;
  custom?: CustomBriefBody;
};

export const createApi = {
  children: () => api<Child[]>("/api/create/children"),
  addChild: (input: ChildInput) => api<Child>("/api/create/children", { json: input }),
  consent: (childId: string, version: string) =>
    api<Child>(`/api/create/children/${childId}/consent`, { json: { accept: true, version } }),
  photo: (childId: string, file: File) => {
    const form = new FormData();
    form.append("photos", file);
    return upload<Child>(`/api/create/children/${childId}/photos`, form);
  },
  draw: (childId: string, style: string, fixes: Fix[] = []) =>
    api<Character>(`/api/create/children/${childId}/characters`, { json: { style, fixes } }),
  character: (id: string) => api<Character>(`/api/create/characters/${id}`),
  approve: (id: string) => api<Character>(`/api/create/characters/${id}/approve`, { method: "POST" }),
  startBook: (input: StartBook) => api<Book>("/api/create/books", { json: input }),
  book: (id: string) => api<Book>(`/api/create/books/${id}`),
  editPage: (id: string, beat: number, text: string) =>
    api<Book>(`/api/create/books/${id}/pages/${beat}`, { method: "PATCH", json: { text } }),
  toCart: (id: string, sku: string, addons: { slug: string; qty?: number }[]) =>
    api<Cart>(`/api/create/books/${id}/cart`, { json: { sku, addons } }),
  deleteChild: (id: string) => api<void>(`/api/create/children/${id}`, { method: "DELETE" }),
};

/** Private images come through the API with the parent's cookies (never a public URL). */
export const characterImage = (id: string) => `/api/create/characters/${id}/image`;
export const pageImage = (bookId: string, beat: number) => `/api/create/books/${bookId}/pages/${beat}/image`;

/** The 12 steps of the design; checkout (11) and the order page (12) are the store's own pages. */
export const STEPS = [
  "child",
  "consent",
  "photo",
  "line",
  "style",
  "character",
  "companion", // «ارسم صاحبك»: optional sub-steps of step 6 (design CompIntro…CompChoose)
  "story",
  "writing",
  "review",
  "format",
  "addons", // Addendum 9 (design AddOns), then the cart and the checkout (Create10)
] as const;
export type Step = (typeof STEPS)[number];
export const TOTAL_STEPS = 12;
