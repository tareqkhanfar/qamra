/** The parent create flow (design Create1–Create11): the child, consent, photo, character, story, preview. */
import { api, fetchBlob, upload, type ApiResult } from "@/lib/api";
import type { CustomBriefBody } from "@/lib/customStory";
import { ALL_STEPS, type StepId } from "@/lib/flows";
import type { PhotoCrop } from "@/lib/photoCrop";
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
  // optional until the API sends them (docs/plans/order-flows.md §d chunk 8)
  interests?: string[]; // what the child likes and the «شيء مميز» note (Magic's story step)
  name_latin?: string | null; // the name in English letters, as the activity books print it
  // the newest kept photo and the parent's framing of it (null: none kept, e.g. deleted 24 h after the approval)
  photo?: StoredPhoto | null;
};
/** The child's kept photo: its original comes through `photoImage`; `crop` null means the whole photo. */
export type StoredPhoto = { id: string; crop: PhotoCrop | null };
/** What `PATCH /api/create/children/{id}` can change (the guardian only; the drawn character is untouched). */
export type ChildPatch = Partial<{
  name: string;
  gender: "m" | "f";
  age: number;
  interests: string[];
  note: string;
  hijab: boolean;
  glasses: boolean;
  name_latin: string;
}>;
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
  language?: "ar" | "en"; // the book's language (Magic: the site's by default; Classic: Arabic)
  dedication?: string;
  companion_id?: string;
  custom?: CustomBriefBody;
};

export const createApi = {
  children: () => api<Child[]>("/api/create/children"),
  addChild: (input: ChildInput) => api<Child>("/api/create/children", { json: input }),
  consent: (childId: string, version: string) =>
    api<Child>(`/api/create/children/${childId}/consent`, { json: { accept: true, version } }),
  // crop: the parent's framing (none: the API frames the photo around the face it finds)
  photo: (childId: string, file: File, crop?: PhotoCrop | null) => {
    const form = new FormData();
    form.append("photos", file);
    if (crop) form.append("crop", JSON.stringify(crop));
    return upload<Child>(`/api/create/children/${childId}/photos`, form);
  },
  // a new framing of the kept photo, checked again by the API (it never redraws by itself)
  frame: (photoId: string, crop: PhotoCrop) =>
    api<Child>(`/api/create/photos/${photoId}/crop`, { method: "PUT", json: crop }),
  photoBlob: (photoId: string) => fetchBlob(photoImage(photoId)),
  // sku: the activity book it is drawn for, so the API checks that the book accepts the style
  draw: (childId: string, style: string, fixes: Fix[] = [], sku?: string | null) =>
    api<Character>(`/api/create/children/${childId}/characters`, {
      json: { style, fixes, ...(sku ? { sku } : {}) },
    }),
  character: (id: string) => api<Character>(`/api/create/characters/${id}`),
  approve: (id: string) => api<Character>(`/api/create/characters/${id}/approve`, { method: "POST" }),
  startBook: (input: StartBook) => api<Book>("/api/create/books", { json: input }),
  book: (id: string) => api<Book>(`/api/create/books/${id}`),
  editPage: (id: string, beat: number, text: string) =>
    api<Book>(`/api/create/books/${id}/pages/${beat}`, { method: "PATCH", json: { text } }),
  // item: the cart line added in one tap on the story page, which this book fills
  toCart: (id: string, sku: string, addons: { slug: string; qty?: number }[], item?: string | null) =>
    api<Cart>(`/api/create/books/${id}/cart`, { json: { sku, addons, ...(item ? { item_id: item } : {}) } }),
  deleteChild: (id: string) => api<void>(`/api/create/children/${id}`, { method: "DELETE" }),
  updateChild: (id: string, patch: ChildPatch) =>
    api<Child>(`/api/create/children/${id}`, { method: "PATCH", json: patch }),
  // style: the parent's pick on the style step (the character it draws in, and the only one it reuses)
  needs: (sku: string, childId?: string, style?: string) => {
    const q = new URLSearchParams({ sku, ...(childId ? { child_id: childId } : {}), ...(style ? { style } : {}) });
    return api<Needs>(`/api/shop/workbooks/needs?${q.toString()}`);
  },
  addWorkbook: (body: AddWorkbook) => api<Cart>("/api/shop/workbooks/cart", { json: body }),
};

/**
 * What an activity book needs from this child (`GET /api/shop/workbooks/needs?sku&child_id`, §d chunk 8): its
 * ages, whether it asks the English name and the family, the character it reuses (or the style a new one is
 * drawn in), and whether the child's name can be traced.
 */
export type Needs = {
  line: string;
  product: string;
  ages: [number, number] | null;
  traces_name?: boolean; // the Arabic name is traced, so it must be in Arabic letters
  asks: { name_en: boolean; family: boolean };
  // draw_style: the style a new character is drawn in (the parent's pick, else the first: 3D); styles: the ones
  // the book accepts, in the site's order (the style step's list, owner's decision of 2026-10-09)
  character: { reuse_id: string | null; draw_style: string | null; styles?: string[] };
  child: {
    name_traceable: boolean;
    name_problem?: "not_arabic" | "not_traceable" | null;
    name_latin: string | null;
  } | null;
};

/** «مغامراتي مع عائلتي»: the family as the book prints it (components/workbook/FamilyDetails `familyPayload`). */
export type FamilyPayload = {
  name: string;
  city: string;
  members: { relation: string; name: string; adult?: boolean; scarf: boolean }[];
};

/** An activity book for one child: a new cart line, or the line added in one tap (`item_id`) filled. */
export type AddWorkbook = {
  sku: string;
  child_id: string;
  item_id?: string;
  character_id?: string;
  name_en?: string;
  family?: FamilyPayload;
};

/**
 * Whether a call failed only because the API doesn't have the endpoint yet (a bare 404 or 405, without our
 * error body): the callers then use their marked fallback. A real refusal always carries an error code.
 */
export function missingEndpoint(r: ApiResult<unknown>): boolean {
  return !r.ok && (r.status === 404 || r.status === 405) && !r.error;
}

/** Private images come through the API with the parent's cookies (never a public URL). */
export const characterImage = (id: string) => `/api/create/characters/${id}/image`;
export const photoImage = (id: string) => `/api/create/photos/${id}/image`; // the guardian's own, never cached
export const pageImage = (bookId: string, beat: number) => `/api/create/books/${bookId}/pages/${beat}/image`;

/**
 * Every step id the URL can name (lib/flows.ts decides which ones a product's flow has, and their count):
 * the story steps, plus `family` and `summary` for the activity books.
 */
export const STEPS: readonly StepId[] = ALL_STEPS;
export type Step = StepId;
/**
 * @deprecated The flow's count is per product now (lib/flows.ts `progress`, shown by Frame); kept only until
 * the checkout header stops saying "n of 12" (§c.9, chunk 7).
 */
export const TOTAL_STEPS = 12;
