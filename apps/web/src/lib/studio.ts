/** Template studio (Addendum 4 §3): API shapes and small helpers shared by the studio's admin pages. */
import { fillName } from "@/lib/arabicName";

export type TemplateStatus = "draft" | "in_review" | "approved" | "live";
export type VersionStatus = TemplateStatus | "retired";
export const TEMPLATE_STATUSES: TemplateStatus[] = ["draft", "in_review", "approved", "live"];

export type Option = { slug: string; title_ar: string; title_en: string };
export type StudioTemplate = {
  id: string;
  theme: string;
  theme_title_ar: string;
  theme_title_en: string;
  style: string;
  variant: string;
  status: TemplateStatus;
  job: "idle" | "queued" | "running" | "failed";
  theme_version: number;
  live_version: number;
  pages_drawn: number;
  pages_total: number;
  flags: string[];
  cost_usd: number;
  vowelized: boolean;
  texts_stale: boolean;
  story_changed: boolean;
  publish_at: string | null;
  live_at: string | null;
  updated_at: string;
};
export type StudioList = { templates: StudioTemplate[]; themes: Option[]; styles: Option[]; variants: string[] };
export type BulkResult = { done: string[]; skipped: { id: string; reason: string }[] };

export type Box = { x: number; y: number; w: number; h: number };
export type TemplatePage = {
  beat: number;
  layout: string | null;
  status: string;
  has_hero: boolean;
  hero_box: Box | null;
  text_box: (Box & { area?: string }) | null;
  locked: boolean;
  regen_count: number;
  cost_usd: number;
  qa_score: number | null;
  flags: string[];
  has_image: boolean;
};
export type TemplateDetail = {
  id: string;
  theme: string;
  theme_version: number;
  style: string;
  variant: string;
  lang: string;
  status: TemplateStatus;
  job: StudioTemplate["job"];
  cost_usd: number;
  flags: string[];
  error: string | null;
  pages_drawn: number;
  pages_total: number;
  texts: { vowelized: boolean; kept: string[]; at: string | null };
  pages: TemplatePage[];
};
export type Words = { ar: string; en: string };
export type TextPage = {
  beat: number;
  layout: string | null;
  area: string | null;
  pinned: Words;
  current: Words;
  vowelized: string | null;
};
export type TemplateTexts = {
  template: string;
  theme: string;
  theme_title: Words;
  style: string;
  style_title: Words;
  variant: string;
  gender: "m" | "f";
  pinned_version: number;
  live_version: number;
  editing: { version: number; status: VersionStatus } | null;
  texts_stale: boolean;
  story_changed: boolean;
  vowelized: boolean;
  text_pt: Record<"young" | "older", [number, number]>;
  sample: { name_ar: string; name_en: string; companion_ar: string; companion_en: string };
  pages: TextPage[];
};

export type Version = {
  version: number;
  status: VersionStatus;
  source: "file" | "studio";
  base_version: number | null;
  note: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  submitted_at: string | null;
  approved_at: string | null;
  approved_by: string | null;
  published_at: string | null;
  published_by: string | null;
  translate: { state: string; estimate_usd?: number; cost_usd?: number; error?: string | null } | null;
};
export type ThemeSummary = {
  slug: string;
  title_ar: string;
  title_en: string;
  live_version: number;
  open: Version | null;
  versions: number;
  templates: number;
  stale_templates: number;
};
export type ThemeDetail = ThemeSummary & { history: Version[] };
export type Change = { key: string; before: string | null; after: string | null };
export type VersionDetail = Version & {
  theme: string;
  live_version: number;
  title_ar: string;
  title_en: string;
  pages: { index: number; layout: string; text_pos: string; text_ar: string; text_en: string }[];
  changes: Change[];
};
export type TranslateEstimate = {
  model: string;
  input_tokens: number;
  output_tokens: number;
  usd: number;
  pages: number;
};

export type StaffMember = {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  mfa: boolean;
  active: boolean;
  last_login_at: string | null;
};
export type StaffList = { me: string; roles: { role: string; permissions: string[] }[]; staff: StaffMember[] };
export type AuditItem = {
  id: string;
  at: string;
  actor: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  data: Record<string, unknown>;
};
export type AuditPage = { items: AuditItem[]; total: number; page: number; pages: number; per_page: number };

const VARIANT = /\{([^{}/]+)\/([^{}/]+)\}/g;

/**
 * A theme text for one child, as the book prints it: `{boy/girl}` variants, then the placeholders; a name after
 * «يا» and at `{name:acc}` in the accusative («يا أبا بكر», lib/arabicName.ts).
 */
export function renderText(template: string, gender: "m" | "f", name: string, companion: string): string {
  const text = template.replace(VARIANT, (_, m: string, f: string) => (gender === "m" ? m : f));
  return fillName(fillName(text, "name", name), "companion", companion);
}

/** Braces left after rendering: an unknown placeholder or a broken variant (the API rejects them too). */
export function brokenPlaceholders(template: string): boolean {
  return (["m", "f"] as const).some((g) => /[{}]/.test(renderText(template, g, "", "")));
}

/** US dollars, isolated left-to-right so "$0.10" keeps its order inside Arabic text. */
export function usd(value: number): string {
  return `⁦$${value === 0 ? "0" : value.toFixed(value < 1 ? 3 : 2)}⁩`;
}

export function when(iso: string | null, locale: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat(locale === "ar" ? "ar-EG-u-nu-latn" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

export const STATUS_TONE: Record<VersionStatus, string> = {
  draft: "bg-paper-sunk text-ink-muted",
  in_review: "bg-info-bg text-info",
  approved: "bg-amber-100 text-amber-700",
  live: "bg-success-bg text-success",
  retired: "bg-paper-sunk text-ink-faint",
};
