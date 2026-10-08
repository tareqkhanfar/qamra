"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { BookTextReview, type StoryField, type TextEdit } from "./BookTextReview";
import { ExamplePublish } from "./ExamplePublish";
import { api, errorText } from "@/lib/api";

type Status = "draft" | "generating" | "preview" | "in_review" | "approved" | "ordered" | "printed" | "failed";
type Card = {
  id: string;
  status: Status;
  title: string | null;
  child_name: string;
  theme_title: string;
  is_sample: boolean;
  updated_at: string;
  flags: string[];
  cost_usd: number;
  budget_usd: number | null;
  avg_likeness: number | null;
  needs_review: number;
  progress: { done?: number; total?: number };
  text_review: "waiting" | "confirmed" | null; // story books: «بانتظار مراجعة النص» until «تأكيد»
};
type Slot = {
  number: number;
  kind: string;
  side: "left" | "right";
  beat: number | null;
  half: "first" | "second" | null;
};
type Page = {
  beat: number;
  layout: string | null;
  pages: number[];
  status: "pending" | "ok" | "needs_review" | "failed" | "skipped";
  qa_score: number | null;
  likeness: number | null;
  flags: string[];
  attempts: number;
  regen_count: number;
  cost_usd: number;
  text: string | null;
  original_text: string | null;
  has_image: boolean;
  qa: Record<string, number | boolean | string>;
};
type Check = { name: string; ok: boolean; detail: string; level: "error" | "warning" };
type Detail = {
  id: string;
  status: Status;
  title: string | null;
  child: { name: string; gender: string; age: number; hijab: boolean; glasses: boolean };
  theme: { slug: string; title: string };
  language: string;
  art_style: string;
  is_sample: boolean;
  cost_usd: number;
  budget_usd: number | null;
  flags: string[];
  qa_summary: {
    avg_likeness?: number | null;
    needs_review?: number;
    failed?: number;
    redraws?: number;
    pages?: number;
  };
  preflight: Record<string, { passed: boolean; min_dpi: number | null; checks: Check[] }>;
  error: string | null;
  generation: {
    line?: string; // an activity book (family, journey): print files drawn from the plan, no pages to review
    pages?: number;
    mode?: string;
    progress?: { done?: number; total?: number };
    offline?: string | boolean;
    public_example?: boolean;
  };
  files: {
    interior: boolean;
    cover: boolean;
    proof: boolean;
    mockup_hardcover?: boolean; // product mockups (Addendum 11 §2.7), rendered beside the print files
    mockup_spread?: boolean;
  };
  // the activity books' files printed apart: the sticker sheet, card stock, the answer key (label: the printer's)
  inserts?: { name: string; label: string }[];
  pages: Page[];
  plan: Slot[];
  costs: Record<string, number>;
  approved_at: string | null;
  approved_by: string | null;
  parent_message: string | null;
  story: {
    title?: string | null;
    dedication?: string | null;
    parents_lesson?: string | null;
    parents_questions?: string[] | null;
    blurb?: string | null;
  };
  text_review: "waiting" | "confirmed" | null;
  text_editable: boolean;
  text_originals: Partial<Record<StoryField, string | null>>;
  text_edits: TextEdit[];
  class_pages: { index: number; text: string | null }[];
};
type Filter = "review" | "flagged" | "generating" | "approved" | "all";

const FILTERS: Filter[] = ["review", "flagged", "generating", "approved", "all"];
const SEVERE = new Set(["unsafe", "text_in_image", "anatomy", "hero_count", "face", "draw_failed", "missing_image"]);

function usd(n: number | null | undefined): string {
  return n === null || n === undefined ? "—" : `$${n.toFixed(2)}`;
}

function views(plan: Slot[]): [Slot | null, Slot | null][] {
  // open-book views in reading order: (right, left)
  if (!plan.length) return [];
  const [first, ...rest] = plan;
  const out: [Slot | null, Slot | null][] = [first!.side === "left" ? [null, first!] : [first!, null]];
  for (let i = 0; i < rest.length; i += 2) {
    const pair = rest.slice(i, i + 2);
    out.push([pair.find((s) => s.side === "right") ?? null, pair.find((s) => s.side === "left") ?? null]);
  }
  return out;
}

export function AdminQueue() {
  const t = useTranslations("queue");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [filter, setFilter] = useState<Filter>("review");
  const [cards, setCards] = useState<Card[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [open, setOpen] = useState<Page | null>(null);
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [cacheKey, setCacheKey] = useState(0);

  const loadList = useCallback(async () => {
    const res = await api<Card[]>(`/api/admin/books?view=${filter}`);
    if (res.ok) {
      setCards(res.data);
      setSelected((s) => s ?? res.data[0]?.id ?? null);
    } else setMessage({ tone: "error", text: errorText(res.error, locale, te("unknown")) });
  }, [filter, locale, te]);

  const loadDetail = useCallback(async (id: string) => {
    const res = await api<Detail>(`/api/admin/books/${id}`);
    if (res.ok) setDetail(res.data);
  }, []);

  useEffect(() => {
    void (async () => {
      await loadList();
    })();
    const timer = setInterval(() => void loadList(), 15000);
    return () => clearInterval(timer);
  }, [loadList]);

  useEffect(() => {
    if (!selected) return;
    void (async () => {
      await loadDetail(selected);
    })();
  }, [selected, loadDetail]);

  useEffect(() => {
    if (!selected || detail?.status !== "generating") return;
    const timer = setInterval(() => {
      void loadDetail(selected);
      setCacheKey((k) => k + 1);
    }, 4000);
    return () => clearInterval(timer);
  }, [selected, detail?.status, loadDetail]);

  const byBeat = useMemo(() => new Map((detail?.pages ?? []).map((p) => [p.beat, p])), [detail]);

  async function act(path: string, json?: unknown, method = "POST") {
    if (!detail) return;
    setBusy(true);
    setMessage(null);
    const res = await api<unknown>(`/api/admin/books/${detail.id}${path}`, { method, json: json ?? {} });
    setBusy(false);
    if (!res.ok) {
      setMessage({ tone: "error", text: errorText(res.error, locale, te("unknown")) });
      return false;
    }
    await loadDetail(detail.id);
    await loadList();
    setCacheKey((k) => k + 1);
    return true;
  }

  const thumb = (beat: number) => `/api/admin/books/${detail?.id}/pages/${beat}/image?v=thumb&k=${cacheKey}`;
  const flagLabel = (f: string) => (t.has(`flags.${f}`) ? t(`flags.${f}`) : f);
  const num = (n: number) => n.toLocaleString(locale === "ar" ? "ar-EG" : "en-US");

  const togglePick = (beat: number, on: boolean) =>
    setPicked((s) => {
      const n = new Set(s);
      if (on) n.add(beat);
      else n.delete(beat);
      return n;
    });
  const cell = (slot: Slot | null): CellProps => {
    const page = slot && slot.beat !== null ? byBeat.get(slot.beat) : undefined;
    return {
      slot,
      page,
      thumb,
      label: slot ? (slot.number === 0 ? t("cover") : t("page", { n: num(slot.number) })) : "",
      kindLabel: slot && t.has(`kinds.${slot.kind}`) ? t(`kinds.${slot.kind}`) : (slot?.kind ?? ""),
      flagLabel,
      selectLabel: t("select"),
      picked: page ? picked.has(page.beat) : false,
      onPick: togglePick,
      onOpen: setOpen,
    };
  };

  const inReview = detail?.status === "in_review";
  const textChanged = detail?.flags.includes("text_changed") ?? false; // saved words not in the PDFs yet
  const progress = detail?.generation.progress ?? {};
  const preflightPassed = detail
    ? Object.values(detail.preflight).length > 0 && Object.values(detail.preflight).every((r) => r.passed)
    : false;

  return (
    <div className="grid gap-6 xl:grid-cols-[340px_1fr]">
      <aside className="flex flex-col gap-3 xl:order-first">
        <h1 className="text-h3 text-night-900">
          {t("title")} {cards && <span className="text-ink-muted">({num(cards.length)})</span>}
        </h1>
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => {
                setFilter(f);
                setSelected(null);
              }}
              aria-pressed={f === filter}
              className={`min-h-9 rounded-full border px-3 text-small ${f === filter ? "border-night-900 bg-night-900 text-paper" : "border-line bg-paper-raised"}`}
            >
              {t(`filters.${f}`)}
            </button>
          ))}
        </div>
        <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-xl border border-line bg-paper-raised">
          {cards?.length === 0 && <li className="p-4 text-small text-ink-muted">{t("empty")}</li>}
          {cards?.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => {
                  setSelected(c.id);
                  setPicked(new Set());
                }}
                className={`flex w-full items-center gap-3 p-3 text-start ${c.id === selected ? "bg-night-100" : "hover:bg-paper-sunk"}`}
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold text-night-900">
                    {c.child_name} · {c.theme_title}
                  </span>
                  <span className="block text-caption text-ink-muted">
                    {c.is_sample ? t("sample") : t("order")} · {t(`status.${c.status}`)} · {usd(c.cost_usd)}
                  </span>
                </span>
                {c.avg_likeness !== null && (
                  <span
                    dir="ltr"
                    className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${c.avg_likeness < 0.7 ? "bg-danger-bg text-danger" : "bg-success-bg text-success"}`}
                  >
                    {c.avg_likeness.toFixed(2)}
                  </span>
                )}
                {c.text_review === "waiting" ? (
                  <span className="rounded-full bg-info-bg px-2 py-0.5 text-[11px] font-bold text-info">
                    {t("textReview.waiting")}
                  </span>
                ) : (
                  c.flags.length > 0 && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-700">
                      {flagLabel(c.flags[0]!)}
                    </span>
                  )
                )}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="flex min-w-0 flex-col gap-5">
        {message && <Alert tone={message.tone}>{message.text}</Alert>}
        {!detail ? (
          <p className="text-ink-muted">{t("pick")}</p>
        ) : (
          <>
            <header className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex flex-col gap-1">
                <h2 className="text-h2 text-night-900">{detail.title ?? detail.child.name}</h2>
                <p className="text-small text-ink-muted">
                  {detail.is_sample ? t("sample") : t("order")} · {detail.theme.title} ·{" "}
                  {t("pages", { n: num(detail.generation.pages ?? detail.plan.length) })} · {detail.art_style} ·{" "}
                  {t(`status.${detail.status}`)}
                </p>
                {detail.text_review === "waiting" && (
                  <p className="text-small font-semibold text-info">{t("textReview.waiting")}</p>
                )}
                {detail.text_review === "confirmed" && detail.approved_at && (
                  <p className="text-small font-semibold text-success">
                    {t("confirmedBy", {
                      name: detail.approved_by ?? "—",
                      date: new Date(detail.approved_at).toLocaleString(locale === "ar" ? "ar-EG" : "en-GB", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      }),
                    })}
                  </p>
                )}
                {detail.status === "generating" && (
                  <p className="text-small font-semibold text-info">
                    {detail.generation.line
                      ? t("renderingFiles")
                      : t("generating", { done: num(progress.done ?? 0), total: num(progress.total ?? 0) })}
                  </p>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={picked.size === 0 || busy || detail.status === "generating"}
                  onClick={async () => {
                    if (await act("/redraw", { beats: [...picked] })) setPicked(new Set());
                  }}
                >
                  {t("regenerate", { n: num(picked.size) })}
                </Button>
                {detail.status === "approved" ? (
                  <span className="inline-flex min-h-11 items-center rounded-full bg-success-bg px-4 text-small font-bold text-success">
                    {t("approved")}
                  </span>
                ) : (
                  <Button
                    size="sm"
                    className="bg-success text-white hover:brightness-110"
                    disabled={!inReview || !preflightPassed || textChanged || busy}
                    onClick={() => {
                      if (window.confirm(t("confirmApprove"))) void act("/approve");
                    }}
                  >
                    {t("approve")}
                  </Button>
                )}
                {detail.is_sample && (
                  <ExamplePublish
                    bookId={detail.id}
                    status={detail.status}
                    published={!!detail.generation.public_example}
                    onChange={() => void loadDetail(detail.id)}
                    onError={(text) => setMessage({ tone: "error", text })}
                  />
                )}
                {(detail.status === "failed" || detail.status === "preview") && (
                  <Button
                    variant="solid"
                    size="sm"
                    disabled={busy}
                    onClick={() => void act("/generate", { mode: "final" })}
                  >
                    {t("generate")}
                  </Button>
                )}
              </div>
            </header>

            {detail.error && <Alert>{detail.error}</Alert>}

            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <div className="rounded-xl bg-success-bg p-4">
                <div className="text-caption text-ink-muted">{t("faceMatch")}</div>
                <div dir="ltr" className="text-h2 font-bold text-success rtl:text-right">
                  {detail.qa_summary.avg_likeness?.toFixed(2) ?? "—"}
                </div>
              </div>
              <div className="rounded-xl bg-amber-100 p-4">
                <div className="text-caption text-ink-muted">{t("flaggedPages")}</div>
                <div className="text-h2 font-bold text-amber-700">
                  {num((detail.qa_summary.needs_review ?? 0) + (detail.qa_summary.failed ?? 0))}
                </div>
              </div>
              <div className="rounded-xl border border-line bg-paper-raised p-4">
                <div className="text-caption text-ink-muted">{t("aiCost")}</div>
                <div dir="ltr" className="text-h2 font-bold text-night-900 rtl:text-right">
                  {usd(detail.cost_usd)}
                </div>
                <div className="text-caption text-ink-muted">{t("ofBudget", { cap: usd(detail.budget_usd) })}</div>
              </div>
              <div className="rounded-xl border border-line bg-paper-raised p-4">
                <div className="text-caption text-ink-muted">{t("redraws")}</div>
                <div className="text-h2 font-bold text-night-900">{num(detail.qa_summary.redraws ?? 0)}</div>
              </div>
            </div>

            {detail.flags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {detail.flags.map((f) => (
                  <span key={f} className="rounded-full bg-amber-100 px-3 py-1 text-small font-semibold text-amber-700">
                    {flagLabel(f)}
                  </span>
                ))}
              </div>
            )}

            {(detail.text_editable || detail.class_pages.length > 0) && (
              <BookTextReview
                key={detail.id}
                book={detail}
                thumb={thumb}
                busy={busy}
                onSaved={async () => {
                  setMessage({ tone: "success", text: t("words.saved") });
                  await loadDetail(detail.id);
                  await loadList();
                }}
                onRerender={async () => {
                  await act("/rerender");
                }}
                onError={(text) => setMessage({ tone: "error", text })}
              />
            )}

            <div className="grid gap-3 md:grid-cols-[1fr_1fr]">
              <div className="flex flex-col gap-2 rounded-xl border border-line bg-paper-raised p-4 text-small">
                <div className="font-semibold text-night-900">{t("preflight")}</div>
                {Object.entries(detail.preflight).length === 0 && <span className="text-ink-muted">—</span>}
                {Object.entries(detail.preflight).map(([name, r]) => (
                  <div key={name} className="flex flex-col gap-0.5">
                    <span className={r.passed ? "text-success" : "text-danger"}>
                      {name}.pdf · {r.passed ? t("pass") : t("fail")} · min {r.min_dpi ?? "—"} DPI
                    </span>
                    {r.checks
                      .filter((c) => !c.ok)
                      .map((c) => (
                        <span key={c.name} className={c.level === "error" ? "text-danger" : "text-warning"}>
                          {c.name}: {c.detail}
                        </span>
                      ))}
                  </div>
                ))}
                <div className="mt-1 flex flex-wrap gap-3">
                  {(["proof", "interior", "cover"] as const).map(
                    (f) =>
                      detail.files[f] && (
                        <a
                          key={f}
                          href={`/api/admin/books/${detail.id}/files/${f}.pdf`}
                          className="font-semibold text-night-800 underline underline-offset-4"
                        >
                          {t(`files.${f}`)}
                        </a>
                      ),
                  )}
                  {(["hardcover", "spread"] as const).map(
                    (m) =>
                      detail.files[`mockup_${m}`] && (
                        <a
                          key={m}
                          href={`/api/admin/books/${detail.id}/files/mockup-${m}.png`}
                          download
                          className="font-semibold text-night-800 underline underline-offset-4"
                        >
                          {t(`files.mockup_${m}`)}
                        </a>
                      ),
                  )}
                  {(detail.inserts ?? []).map((f) => (
                    <a
                      key={f.name}
                      href={`/api/admin/books/${detail.id}/inserts/${encodeURIComponent(f.name)}`}
                      className="font-semibold text-night-800 underline underline-offset-4"
                    >
                      {f.label}
                    </a>
                  ))}
                  <a
                    href={`/api/admin/books/${detail.id}/character`}
                    target="_blank"
                    rel="noreferrer"
                    className="font-semibold text-night-800 underline underline-offset-4"
                  >
                    {t("character")}
                  </a>
                </div>
              </div>
              <form
                className="flex flex-col gap-2 rounded-xl border border-line bg-paper-raised p-4 text-small"
                onSubmit={(e) => {
                  e.preventDefault();
                  const v = String(new FormData(e.currentTarget).get("budget") ?? "");
                  void act("/budget", { budget_usd: v });
                }}
              >
                <label htmlFor="budget" className="font-semibold text-night-900">
                  {t("budget")}
                </label>
                <div className="flex gap-2">
                  <input
                    id="budget"
                    name="budget"
                    dir="ltr"
                    inputMode="decimal"
                    defaultValue={detail.budget_usd?.toFixed(2) ?? ""}
                    key={detail.id + String(detail.budget_usd)}
                    className="min-h-11 w-28 rounded-sm border border-line bg-paper px-3"
                  />
                  <Button type="submit" variant="secondary" size="sm" disabled={busy}>
                    {t("raiseBudget")}
                  </Button>
                </div>
                <div className="text-caption text-ink-muted" dir="ltr">
                  {Object.entries(detail.costs)
                    .map(([k, v]) => `${k} $${v.toFixed(3)}`)
                    .join(" · ")}
                </div>
              </form>
            </div>

            {byBeat.get(0) && (
              <div className="flex items-start gap-4">
                <div className="w-40">
                  <PageCell {...cell({ number: 0, kind: "cover", side: "right", beat: 0, half: null })} />
                </div>
                <span className="mt-2 text-small font-semibold text-night-900">{t("cover")}</span>
              </div>
            )}

            <div className="flex flex-col gap-4">
              {views(detail.plan).map(([right, left], i) => (
                <div key={i} className="grid grid-cols-2 gap-1 rounded-lg bg-paper-sunk p-2 [direction:rtl]">
                  <PageCell {...cell(right)} />
                  <PageCell {...cell(left)} />
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {open && detail && (
        <PageDrawer
          page={open}
          bookId={detail.id}
          cacheKey={cacheKey}
          onClose={() => setOpen(null)}
          onRedraw={async () => {
            if (await act("/redraw", { beats: [open.beat] })) setOpen(null);
          }}
          busy={busy}
        />
      )}
    </div>
  );
}

type CellProps = {
  slot: Slot | null;
  page: Page | undefined;
  thumb: (beat: number) => string;
  label: string;
  kindLabel: string;
  flagLabel: (f: string) => string;
  selectLabel: string;
  picked: boolean;
  onPick: (beat: number, on: boolean) => void;
  onOpen: (page: Page) => void;
};

function PageCell({ slot, page, thumb, label, kindLabel, flagLabel, selectLabel, picked, onPick, onOpen }: CellProps) {
  if (!slot) return <div className="aspect-square rounded-md bg-paper-sunk/60" />;
  const isSpread = page?.layout === "spread";
  const severe = page?.flags.some((f) => SEVERE.has(f));
  const pickable = page !== undefined;
  if (!page)
    return (
      <div className="flex aspect-square flex-col items-center justify-center gap-1 rounded-md border border-line bg-paper-raised p-2 text-center text-caption text-ink-muted">
        <span className="font-semibold text-night-900">{label}</span>
        <span>{kindLabel}</span>
      </div>
    );
  return (
    <div
      className={`relative flex flex-col overflow-hidden rounded-md border-2 bg-paper-raised ${severe ? "border-danger" : page.status === "needs_review" ? "border-amber-500" : "border-line"}`}
    >
      <button
        type="button"
        onClick={() => onOpen(page)}
        className="relative aspect-square overflow-hidden bg-night-100"
        aria-label={label}
      >
        {page.has_image && (
          // eslint-disable-next-line @next/next/no-img-element -- private image streamed by the admin API
          <img
            src={thumb(page.beat)}
            alt=""
            loading="lazy"
            className={
              isSpread
                ? `absolute top-0 h-full w-[200%] max-w-none object-cover ${slot.side === "left" ? "left-0" : "right-0"}`
                : "absolute inset-0 h-full w-full object-cover"
            }
          />
        )}
      </button>
      {pickable && slot.half !== "second" && (
        <label className="absolute top-1.5 inline-flex size-7 items-center justify-center rounded-sm bg-paper-raised/90 ltr:right-1.5 rtl:left-1.5">
          <span className="sr-only">{selectLabel}</span>
          <input
            type="checkbox"
            checked={picked}
            onChange={(e) => onPick(page.beat, e.target.checked)}
            className="size-4 accent-night-900"
          />
        </label>
      )}
      <div className="flex items-center justify-between gap-1 px-2 py-1.5 text-caption">
        <span className="font-semibold text-night-900">{label}</span>
        {page.qa_score !== null && (
          <span className={`font-bold ${page.status === "ok" ? "text-success" : "text-warning"}`} dir="ltr">
            {page.qa_score.toFixed(2)}
          </span>
        )}
      </div>
      {page.flags.length > 0 && slot.half !== "second" && (
        <div className="flex flex-wrap gap-1 px-2 pb-2">
          {page.flags.slice(0, 3).map((f) => (
            <span
              key={f}
              className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${SEVERE.has(f) ? "bg-danger-bg text-danger" : "bg-amber-100 text-amber-700"}`}
            >
              {flagLabel(f)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function PageDrawer({
  page,
  bookId,
  cacheKey,
  onClose,
  onRedraw,
  busy,
}: {
  page: Page;
  bookId: string;
  cacheKey: number;
  onClose: () => void;
  onRedraw: () => Promise<void>;
  busy: boolean;
}) {
  const t = useTranslations("queue");
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const qaKeys = [
    "likeness",
    "people_count_ok",
    "anatomy_ok",
    "text_in_image",
    "outfit_ok",
    "hijab_ok",
    "cropped",
    "text_space_ok",
    "companion_ok",
    "style_ok",
    "safe",
  ];
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-night-950/60 p-2 md:items-center"
      role="dialog"
      aria-modal="true"
    >
      <div className="flex max-h-[95dvh] w-full max-w-4xl flex-col gap-4 overflow-auto rounded-xl bg-paper-raised p-5 md:grid md:grid-cols-[1.2fr_1fr]">
        {/* eslint-disable-next-line @next/next/no-img-element -- private image streamed by the admin API */}
        <img
          src={`/api/admin/books/${bookId}/pages/${page.beat}/image?v=raw&k=${cacheKey}`}
          alt=""
          className="w-full rounded-md border border-line object-contain"
        />
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h3 className="text-h3 text-night-900">
              {page.beat === 0 ? t("cover") : page.pages.map((n) => t("page", { n })).join(" – ")}
            </h3>
            <button type="button" onClick={onClose} className="text-small underline underline-offset-4">
              {t("close")}
            </button>
          </div>
          <div className="text-small text-ink-muted">
            {t("attempts", { n: page.attempts })} · {t("score")}:{" "}
            <span dir="ltr">{page.qa_score?.toFixed(2) ?? "—"}</span> ·{" "}
            <span dir="ltr">${page.cost_usd.toFixed(3)}</span>
          </div>
          {Object.keys(page.qa).length > 0 && (
            <div className="rounded-md border border-line p-3 text-small">
              <div className="mb-1 font-semibold text-night-900">{t("qa")}</div>
              <ul className="grid grid-cols-2 gap-x-4 gap-y-1">
                {qaKeys
                  .filter((k) => k in page.qa)
                  .map((k) => {
                    const v = page.qa[k];
                    const good =
                      k === "likeness"
                        ? Number(v) >= 7
                        : k === "text_in_image"
                          ? v === false
                          : k === "cropped" // the characters cut by the trim: none is good
                            ? Array.isArray(v) && v.length === 0
                            : v === true;
                    return (
                      <li key={k} className="flex justify-between gap-2">
                        <span>{t(`questions.${k}`)}</span>
                        <span className={good ? "text-success" : "text-danger"} dir="ltr">
                          {k === "likeness" ? `${v}/10` : good ? "✓" : "✗"}
                        </span>
                      </li>
                    );
                  })}
              </ul>
              {typeof page.qa.notes === "string" && <p className="mt-2 text-caption text-ink-muted">{page.qa.notes}</p>}
            </div>
          )}
          {page.beat > 0 && page.text && (
            <div className="flex flex-col gap-1 text-small">
              <span className="font-semibold text-night-900">{t("text")}</span>
              <p className="rounded-sm bg-paper-sunk p-3 text-body-l leading-[1.9]">{page.text}</p>
              <span className="text-caption text-ink-muted">{t("textInPanel")}</span>
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => void onRedraw()}>
              {t("redrawOne")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
