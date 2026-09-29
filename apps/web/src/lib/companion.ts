/** «ارسم صاحبك» (Addendum 1 §1): the child's drawing becomes the companion of their books. */
import { api, upload } from "@/lib/api";
import type { Catalog } from "@/lib/store";

export type CompanionType = "creature" | "animal" | "robot" | "other";
export const COMPANION_TYPES: CompanionType[] = ["creature", "animal", "robot", "other"];
export const TRAITS = ["funny", "brave", "shy", "kind", "curious"] as const;
export type Trait = (typeof TRAITS)[number];
export type Box = { x: number; y: number; w: number; h: number };
export type Rotation = 0 | 90 | 180 | 270;

export type Companion = {
  id: string;
  child_id: string;
  status: "draft" | "generating" | "ready" | "approved" | "failed";
  name: string;
  type: CompanionType;
  type_other: string | null;
  traits: Trait[];
  options: number;
  redraws_left: number;
  original: boolean;
  paper_found: boolean;
  box: Box | null;
  rotate: Rotation;
  clean: boolean;
  error: { code: string; ar: string; en: string } | null;
  approved: boolean;
  books: number;
};
export type MyCompanion = Companion & { child_name: string };
export type DrawInput = { name: string; type: CompanionType; type_other?: string; traits: Trait[]; style?: string };

const base = "/api/create/companions";

export const companionApi = {
  upload: (childId: string, file: File) => {
    const form = new FormData();
    form.append("drawing", file);
    return upload<Companion>(`/api/create/children/${childId}/companions`, form);
  },
  get: (id: string) => api<Companion>(`${base}/${id}`),
  crop: (id: string, body: { box: Box | null; rotate: Rotation; clean: boolean }) =>
    api<Companion>(`${base}/${id}/crop`, { json: body }),
  draw: (id: string, body: DrawInput) => api<Companion>(`${base}/${id}/draw`, { json: body }),
  choose: (id: string, option: number) => api<Companion>(`${base}/${id}/choose`, { json: { option } }),
  mine: () => api<MyCompanion[]>(base),
  remove: (id: string) => api<void>(`${base}/${id}`, { method: "DELETE" }),
};

/** Private images through the API with the parent's cookies; `v` busts the browser cache after a change. */
export const drawingImage = (id: string, kind: "cleaned" | "original", v = 0) =>
  `${base}/${id}/drawing?kind=${kind}&v=${v}`;
export const optionImage = (id: string, n: number, v = 0) => `${base}/${id}/options/${n}/image?v=${v}`;
export const companionImage = (id: string) => `${base}/${id}/image`;

/** The add-on from the catalog (admin data): free in Magic, priced in Classic, or not offered at all. */
export function companionAddOn(catalog: Catalog | null, line: string) {
  const addon = catalog?.addons.find((a) => a.slug === "drawing-companion");
  if (!addon || !(addon.lines.includes(line) || addon.included_lines.includes(line))) return null;
  return { addon, free: addon.included_lines.includes(line), price: addon.price };
}
