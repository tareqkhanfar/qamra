"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { api, errorText, upload } from "@/lib/api";
import type { Child } from "@/lib/create";
import { RELATIONS, type Relation } from "./FamilyDetails";

type Member = {
  id: string;
  relation: Relation;
  first_name: string;
  scarf: boolean;
  consented: boolean;
  has_photo: boolean;
  status: "draft" | "generating" | "ready" | "approved" | "failed";
  approved: boolean;
  drawings_left: number;
};
const CONSENT_VERSION = "family-member-2026-09"; // the API's routers/family_members.CONSENT_VERSION
const button =
  "min-h-11 rounded-full border-[1.5px] border-line px-4 text-small font-bold text-night-900 disabled:opacity-50";

/** The illustrated-family add-on (Addendum 7 §7): consent, a photo, a drawing and approval for each person. */
export function FamilyCharacters() {
  const locale = useLocale();
  const t = useTranslations("familyCharacters");
  const te = useTranslations("errors");
  const [children, setChildren] = useState<Child[]>([]);
  const [child, setChild] = useState<string>("");
  const [members, setMembers] = useState<Member[]>([]);
  const [relation, setRelation] = useState<Relation>("grandmother");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fail = useCallback(
    (e: Parameters<typeof errorText>[0]) => setError(errorText(e, locale, te("unknown"))),
    [locale, te],
  );
  const load = useCallback(async (id: string) => {
    const r = await api<Member[]>(`/api/create/children/${id}/family`);
    if (r.ok) setMembers(r.data);
  }, []);
  useEffect(() => {
    void (async () => {
      const r = await api<Child[]>("/api/create/children");
      if (r.ok && r.data.length) {
        setChildren(r.data);
        setChild(r.data[0]!.id);
        await load(r.data[0]!.id);
      }
    })();
  }, [load]);
  useEffect(() => {
    if (!child || !members.some((m) => m.status === "generating")) return;
    const timer = setInterval(() => void load(child), 4000); // the drawing takes about a minute
    return () => clearInterval(timer);
  }, [child, members, load]);

  async function call(path: string, json?: unknown, method = "POST") {
    setError(null);
    const r = await api<Member>(path, { method, json });
    if (!r.ok) fail(r.error);
    await load(child);
  }
  async function sendPhoto(id: string, file: File) {
    const form = new FormData();
    form.set("photo", file);
    const r = await upload<Member>(`/api/create/family/${id}/photo`, form);
    if (!r.ok) fail(r.error);
    await load(child);
  }

  return (
    <section className="flex flex-col gap-4">
      <h1 className="text-[26px] text-night-900">{t("title")}</h1>
      <p className="text-body text-ink">{t("lead")}</p>
      {error && <Alert>{error}</Alert>}
      {children.length > 1 && (
        <label className="flex flex-col gap-1 text-small font-semibold">
          {t("child")}
          <select
            className="min-h-11 rounded-[12px] border border-line px-3"
            value={child}
            onChange={(e) => {
              setChild(e.target.value);
              void load(e.target.value);
            }}
          >
            {children.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
      )}
      {members.map((m) => (
        <article key={m.id} className="flex flex-col gap-2 rounded-[18px] border border-line bg-paper-raised p-4">
          <strong className="text-night-900">{m.first_name || t(`relations.${m.relation}`)}</strong>
          {!m.consented && (
            <label className="flex items-start gap-2 text-small">
              <input
                type="checkbox"
                onChange={(e) =>
                  e.target.checked &&
                  void call(`/api/create/family/${m.id}/consent`, { accept: true, version: CONSENT_VERSION })
                }
              />
              {t("consent")}
            </label>
          )}
          {m.consented && !m.approved && (
            <label className="flex flex-col gap-1 text-small font-semibold">
              {t("photo")}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e) => e.target.files?.[0] && void sendPhoto(m.id, e.target.files[0])}
              />
            </label>
          )}
          {m.status === "generating" && <p className="text-small text-ink-faint">{t("drawing")}</p>}
          {(m.status === "ready" || m.status === "approved") && (
            // eslint-disable-next-line @next/next/no-img-element -- a private drawing behind the parent's session
            <img
              src={`/api/create/family/${m.id}/image?v=${m.drawings_left}`}
              alt=""
              className="max-h-48 w-auto self-start rounded-[12px] bg-white"
            />
          )}
          <div className="flex flex-wrap gap-2">
            {m.has_photo && !m.approved && m.status !== "generating" && m.drawings_left > 0 && (
              <button
                type="button"
                className={button}
                onClick={() => void call(`/api/create/family/${m.id}/draw`, {})}
              >
                {m.status === "ready" ? t("redraw") : t("draw")} ({m.drawings_left} {t("left")})
              </button>
            )}
            {m.status === "ready" && (
              <button type="button" className={button} onClick={() => void call(`/api/create/family/${m.id}/approve`)}>
                {t("approve")}
              </button>
            )}
            {m.approved && <span className="text-small font-bold text-success">{t("approved")}</span>}
            <button
              type="button"
              className={button}
              onClick={() => void call(`/api/create/family/${m.id}`, undefined, "DELETE")}
            >
              {t("remove")}
            </button>
          </div>
        </article>
      ))}
      {child && members.length < 4 && (
        <div className="flex flex-wrap items-end gap-2">
          <select
            className="min-h-11 rounded-[12px] border border-line px-3"
            value={relation}
            onChange={(e) => setRelation(e.target.value as Relation)}
          >
            {RELATIONS.map((r) => (
              <option key={r} value={r}>
                {t(`relations.${r}`)}
              </option>
            ))}
          </select>
          <input
            className="min-h-11 rounded-[12px] border border-line px-3"
            maxLength={20}
            placeholder={t("name")}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button
            type="button"
            className={button}
            onClick={() => {
              void call(`/api/create/children/${child}/family`, { relation, name });
              setName("");
            }}
          >
            {t("add")}
          </button>
        </div>
      )}
    </section>
  );
}
