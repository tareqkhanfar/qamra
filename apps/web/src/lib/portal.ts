/** The kindergarten portal (design Portal* and Class*): the school's API, and the parent's invite link. */
import { api, upload } from "@/lib/api";
import type { Character, Child } from "@/lib/create";

export type Stage = "not_invited" | "invited" | "consent" | "photo" | "approved";
export const STAGES: Stage[] = ["not_invited", "invited", "consent", "photo", "approved"];

export type Org = {
  id: string;
  name: string;
  status: "pending" | "approved" | "rejected" | "suspended";
  country: string;
  city: string | null;
  phone: string | null;
  address: string | null;
  has_logo: boolean;
  approved_at: string | null;
};
export type ClassSummary = {
  id: string;
  name: string;
  teacher_name: string | null;
  school_year: string | null;
  children: number;
  stages: Record<Stage, number>;
  book_status: BookStatus | null;
  book_line: string | null;
};
export type Me = { name: string; email: string; org: Org; classes: ClassSummary[]; kpis: Record<string, number> };

export type ChildRow = {
  id: string;
  name: string;
  gender: "m" | "f";
  age: number;
  parent_name: string | null;
  phone: string | null;
  email: string | null;
  stage: Stage;
  steps: { invited: boolean; consent: boolean; photo: boolean; drawing: boolean; approved: boolean };
  drawn: boolean;
  character_id: string | null;
  invite: { path: string | null; state: "none" | "ready" | "sent" | "claimed" | "expired"; expires_at: string | null };
  last_activity: string | null;
};
export type ClassDetail = {
  id: string;
  name: string;
  teacher_name: string | null;
  school_year: string | null;
  stages: Record<Stage, number>;
  children: ChildRow[];
  book_status: BookStatus | null;
  book_line: string | null;
  art_style: string | null;
};

export type Message = { ar: string; en: string };
export type ImportRow = {
  row: number;
  name: string;
  gender: "m" | "f" | null;
  birth_year: number | null;
  parent_name: string | null;
  phone: string | null;
  email: string | null;
  errors: Message[];
  warnings: Message[];
  ok: boolean;
};
export type Preview = { rows: ImportRow[]; ok: number; warnings: number; errors: number };

export type BookStatus = "setup" | "generating" | "review" | "approved" | "ordered" | "printing" | "failed";
export type ClassBook = {
  exists: boolean;
  status: BookStatus | null;
  theme: string | null;
  line: "classic" | "magic";
  style: string;
  language: "ar" | "en";
  min_appearances: number;
  teacher_message: string | null;
  class_photo: boolean;
  class_photo_permission_at: string | null;
  logo: boolean;
  ready: number;
  children: number;
  pages: number;
  plan_outdated: boolean;
  short: string[];
  progress: Progress;
  flags: string[];
  redraws_left: number;
  order_code: string | null;
  themes: { slug: string; name_ar: string; name_en: string; pages: number }[];
  styles: { slug: string; name_ar: string; name_en: string; lines: string[] }[];
};
export type Progress = {
  stage?: "queued" | "pages" | "covers" | "files" | "done";
  pages?: { done: number; total: number };
  covers?: { done: number; total: number };
  files?: { done: number; total: number };
};
export type PlanKid = { id: string; name: string };
export type PlanPage = { index: number; key: string; slots: number; text: string; children: PlanKid[] };
export type Plan = {
  min_appearances: number;
  line: string;
  manual: boolean;
  outdated: boolean;
  pages: PlanPage[];
  members: (PlanKid & { count: number })[];
};
export type ReviewPage = {
  index: number;
  text: string | null;
  children: string[];
  status: string;
  flags: string[];
  unrecognized: string[];
  image: boolean;
};
export type ReviewCopy = {
  child_id: string;
  name: string;
  status: "waiting" | "drawing" | "ready" | "approved" | "failed";
  cover: boolean;
  flags: string[];
  appearances: number;
  recognized: number;
};
export type Review = {
  status: BookStatus;
  progress: Progress;
  pages: ReviewPage[];
  copies: ReviewCopy[];
  redraws_left: number;
  combined: boolean;
};
export type Quote = {
  currency: "ILS" | "JOD";
  product: string;
  name_ar: string;
  name_en: string;
  copies: number;
  children: string[];
  tiers: { min_qty: number; unit_price: string }[];
  price_list: string | null;
  unit_price: string | null;
  subtotal: string;
  discount: string;
  shipping: string;
  total: string;
  delivery: { name: string | null; city: string | null; address: string | null; phone: string | null };
  notes: string[];
  ordered: string | null;
};
export type OrderRow = {
  code: string;
  status: string;
  currency: string;
  total: string;
  copies: number;
  placed_at: string;
  invoice: string | null;
  invoice_ready: boolean;
};

export type SignupInput = {
  school_name: string;
  contact_name: string;
  city: string;
  phone: string;
  email: string;
  password: string;
  address?: string;
  country: "PS" | "JO";
  locale: "ar" | "en";
};

const cls = (id: string) => `/api/portal/classes/${id}`;

export const portalApi = {
  signup: (input: SignupInput) => api<Me>("/api/portal/signup", { json: input }),
  me: () => api<Me>("/api/portal/me"),
  updateOrg: (input: { name?: string; city?: string; phone?: string; address?: string }) =>
    api<Me>("/api/portal/org", { method: "PATCH", json: input }),
  logo: (file: File) => {
    const form = new FormData();
    form.append("logo", file);
    return upload<Me>("/api/portal/logo", form);
  },
  createClass: (input: { name: string; teacher_name?: string; school_year?: string }) =>
    api<ClassSummary>("/api/portal/classes", { json: input }),
  classDetail: (id: string) => api<ClassDetail>(cls(id)),
  preview: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return upload<Preview>(`${cls(id)}/import/preview`, form);
  },
  importRows: (id: string, rows: ImportRow[]) =>
    api<{ created: number; skipped: ImportRow[]; detail: ClassDetail }>(`${cls(id)}/import`, { json: { rows } }),
  removeChild: (id: string, childId: string) =>
    api<ClassDetail>(`${cls(id)}/children/${childId}`, { method: "DELETE" }),
  markSent: (id: string, children: string[]) => api<ClassDetail>(`${cls(id)}/invites/sent`, { json: { children } }),
  renewInvite: (id: string, childId: string) =>
    api<ClassDetail>(`${cls(id)}/children/${childId}/invite`, { method: "POST" }),
  book: (id: string) => api<ClassBook>(`${cls(id)}/book`),
  setupBook: (
    id: string,
    input: Partial<{ theme: string; line: string; style: string; min_appearances: number; teacher_message: string }>,
  ) => api<ClassBook>(`${cls(id)}/book`, { method: "PUT", json: input }),
  classPhoto: (id: string, file: File, permission: boolean) => {
    const form = new FormData();
    form.append("photo", file);
    form.append("permission", permission ? "true" : "false");
    return upload<ClassBook>(`${cls(id)}/book/photo`, form);
  },
  deleteClassPhoto: (id: string) => api<ClassBook>(`${cls(id)}/book/photo`, { method: "DELETE" }),
  plan: (id: string) => api<Plan>(`${cls(id)}/book/plan`),
  autoPlan: (id: string) => api<Plan>(`${cls(id)}/book/plan/auto`, { method: "POST" }),
  savePlan: (id: string, pages: { index: number; children: string[] }[]) =>
    api<Plan>(`${cls(id)}/book/plan`, { method: "PUT", json: { pages } }),
  generate: (id: string) => api<ClassBook>(`${cls(id)}/book/generate`, { method: "POST" }),
  review: (id: string) => api<Review>(`${cls(id)}/book/review`),
  redraw: (id: string, pages: number[], covers: string[]) =>
    api<ClassBook>(`${cls(id)}/book/redraw`, { json: { pages, covers } }),
  approve: (id: string, children: string[] | null) => api<Review>(`${cls(id)}/book/approve`, { json: { children } }),
  quote: (id: string) => api<Quote>(`${cls(id)}/order/quote`),
  order: (id: string, notes?: string) =>
    api<{ code: string; total: string; currency: string; invoice: string }>(`${cls(id)}/order`, {
      json: { accept_terms: true, notes },
    }),
  orders: () => api<OrderRow[]>("/api/portal/orders"),
};

/** Private files through the API with the school's cookies (never a storage address). */
export const portalFiles = {
  logo: "/api/portal/logo",
  classPhoto: (id: string) => `${cls(id)}/book/photo`,
  character: (id: string, childId: string) => `${cls(id)}/children/${childId}/character`,
  page: (id: string, index: number) => `${cls(id)}/book/pages/${index}/image`,
  cover: (id: string, childId: string) => `${cls(id)}/book/copies/${childId}/cover`,
  copyPdf: (id: string, childId: string) => `${cls(id)}/book/copies/${childId}/book.pdf`,
  template: (id: string) => `${cls(id)}/template.csv`,
  invoice: (code: string) => `/api/portal/orders/${code}/invoice.pdf`,
};

// ---- the parent's invite link ---------------------------------------------------------------------------

export type Invite = {
  state: "open" | "mine" | "taken" | "expired";
  school: string;
  classroom: string;
  child_name: string;
  theme_ar: string | null;
  theme_en: string | null;
  style: string;
  consent_version: string;
  child: Child | null;
};

export const inviteApi = {
  open: (token: string) => api<Invite>(`/api/invite/${token}`),
  claim: (token: string) => api<Invite>(`/api/invite/${token}/claim`, { method: "POST" }),
  consent: (token: string, version: string) =>
    api<Invite>(`/api/invite/${token}/consent`, { json: { accept: true, version } }),
  draw: (token: string, fixes: string[] = []) => api<Character>(`/api/invite/${token}/character`, { json: { fixes } }),
};

/** "0.00 ₪" / "0.00 د.أ". */
export function money(amount: string | number | null, currency: string, locale: string): string {
  if (amount === null) return "—";
  const value = Number(amount).toLocaleString(locale === "ar" ? "ar-EG" : "en-US", { minimumFractionDigits: 2 });
  return currency === "JOD" ? `${value} ${locale === "ar" ? "د.أ" : "JD"}` : `${value} ₪`;
}
