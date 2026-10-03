/** «قلبي يعرف الله»: the scholar's review, unit by unit (API: routers/admin_islamic.py, Addendum 10 §3.3). */

import { api } from "@/lib/api";

export type ReviewStatus = "draft" | "scholar_review" | "changes_requested" | "approved";

export type ReviewMe = { scholar: boolean; can_edit: boolean; name_ar: string | null; may_be_named: boolean };

export type PreviewInfo = {
  status: "none" | "queued" | "ready" | "failed";
  run_id: string | null;
  pages: number;
  rendered_at: string | null;
  error: string | null;
  problems: string[];
};

export type ReviewPoint = {
  source_id: string;
  title_ar: string;
  question: string;
  decision: string | null;
  decided_by: string | null;
  decided_at: string | null;
};

export type VolumeSummary = {
  id: string;
  name_ar: string;
  title_ar: string;
  units: number;
  approved: number;
  in_review: number;
  changes_requested: number;
  all_approved: boolean;
  previews: PreviewInfo;
};

export type ReviewOverview = { volumes: VolumeSummary[]; general_points: ReviewPoint[]; me: ReviewMe };

export type ReviewPage = {
  n: number;
  kind: string;
  type: string;
  title: string;
  sources: string[];
  preview: string | null;
};

export type ReviewSource = {
  id: string;
  kind: string;
  title_ar: string;
  status: string;
  question: string | null;
  decision: string | null;
  decided_by: string | null;
  decided_at: string | null;
};

export type ReviewEvent = {
  kind: "submitted" | "approved" | "changes_requested" | "reopened" | "note";
  page: number | null;
  source_id: string | null;
  text: string;
  author_name: string;
  scholar: boolean;
  created_at: string;
};

export type ReviewUnit = {
  id: string;
  title_ar: string;
  matter: boolean;
  status: ReviewStatus;
  submitted_at: string | null;
  reviewer_name: string | null;
  decided_at: string | null;
  approved_at: string | null;
  preview_run: string | null;
  pages: ReviewPage[];
  sources: ReviewSource[];
  pending_points: number;
  events: ReviewEvent[];
};

export type ReviewVolume = {
  id: string;
  name_ar: string;
  title_ar: string;
  all_approved: boolean;
  previews: PreviewInfo;
  pages_mismatch: boolean;
  units: ReviewUnit[];
  me: ReviewMe;
};

export type StatusChange = { unit_id: string; status: ReviewStatus; volume_approved: boolean };
export type NoteBody = { text: string; page?: number | null; source_id?: string | null };

const BASE = "/api/admin/islamic/review";
const enc = encodeURIComponent;

export const islamicReviewApi = {
  overview: () => api<ReviewOverview>(BASE),
  volume: (id: string) => api<ReviewVolume>(`${BASE}/volumes/${enc(id)}`),
  submit: (unit: string, body: NoteBody) => api<StatusChange>(`${BASE}/units/${enc(unit)}/submit`, { json: body }),
  approve: (unit: string, body: NoteBody) => api<StatusChange>(`${BASE}/units/${enc(unit)}/approve`, { json: body }),
  requestChanges: (unit: string, body: NoteBody) =>
    api<StatusChange>(`${BASE}/units/${enc(unit)}/request-changes`, { json: body }),
  note: (unit: string, body: NoteBody) =>
    api<{ unit_id: string; events: ReviewEvent[] }>(`${BASE}/units/${enc(unit)}/notes`, { json: body }),
  decide: (source: string, decision: string) =>
    api<ReviewPoint>(`${BASE}/decisions/${enc(source)}`, { method: "PUT", json: { decision } }),
  saveMe: (name_ar: string, may_be_named: boolean) =>
    api<ReviewMe>(`${BASE}/me`, { method: "PUT", json: { name_ar, may_be_named } }),
  renderPreviews: (volume: string) =>
    api<PreviewInfo>(`${BASE}/volumes/${enc(volume)}/previews`, { method: "POST", json: {} }),
  exportUrl: `${BASE}/export`,
};
