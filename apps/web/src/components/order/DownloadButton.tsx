"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button, buttonClasses, Spinner } from "@/components/ui/Button";
import { Link, usePathname } from "@/i18n/navigation";
import { useSummaryText } from "@/components/order/LineSummary";
import { errorText } from "@/lib/api";
import { downloadsApi, partOption, type DownloadFile, type DownloadLine } from "@/lib/downloads";
import { lineSummary } from "@/lib/order";

const POLL_MS = 3000;
const POLL_LIMIT = 60; // about three minutes, then «يستغرق التجهيز وقتًا أطول من المعتاد»

/**
 * «تنزيل PDF» for one order line (docs/plans/digital-delivery.md): a button per file the line has ready (a set:
 * each volume, and the answer keys or sticker sheets that come with it), and a note while the rest is made.
 *
 * Props:
 * - `itemId`: the order line's id (the order page: the tracking's `items[].id`; the account page: `item_id`).
 * - `line` (optional): the line as `GET /api/downloads` returned it, so the account page doesn't fetch it again.
 *   Without it the component fetches `GET /api/downloads/{itemId}`: signed out it asks to sign in, someone else's
 *   order says so (403), and a line with nothing to download (404) renders nothing.
 */
export function DownloadButton({ itemId, line: given }: { itemId: string; line?: DownloadLine }) {
  const t = useTranslations("downloads");
  const te = useTranslations("errors");
  const locale = useLocale();
  const pathname = usePathname();
  const [fetched, setFetched] = useState<DownloadLine | null>(null);
  const [problem, setProblem] = useState<string | null>(null); // "signin", "gone" or a message
  const line = given ?? fetched;

  useEffect(() => {
    if (given) return;
    let live = true;
    (async () => {
      const r = await downloadsApi.line(itemId, locale);
      if (!live) return;
      if (r.ok) return setFetched(r.data);
      if (r.status === 401) return setProblem("signin");
      if (r.status === 404) return setProblem("gone");
      setProblem(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    })();
    return () => {
      live = false;
    };
  }, [given, itemId, locale, te]);

  if (problem === "gone") return null;
  if (problem === "signin")
    return (
      <div className="flex flex-wrap items-center gap-2 text-caption text-ink">
        <span>{t("signIn")}</span>
        <Link href={`/login?next=${encodeURIComponent(pathname)}`} className={buttonClasses("secondary", "sm")}>
          {t("signInButton")}
        </Link>
      </div>
    );
  if (problem) return <Alert>{problem}</Alert>;
  if (!line || (!line.files.length && line.options.format !== "digital")) return null; // a printed line's file comes later
  return (
    <div className="flex flex-col gap-2">
      {line.files.map((f) => (
        <FileRow key={`${f.book_id}-${f.kind}`} itemId={line.item_id} line={line.line} file={f} />
      ))}
      {line.status === "preparing" && line.options.format === "digital" && (
        <p className="text-caption text-ink-muted">{line.files.length ? t("moreComing") : t("waiting")}</p>
      )}
    </div>
  );
}

type Phase =
  | { at: "idle" }
  | { at: "asking" }
  | { at: "preparing"; polls: number }
  | { at: "ready"; url: string }
  | { at: "started"; url: string }
  | { at: "failed" }
  | { at: "slow" }
  | { at: "error"; message: string };

/** One file: asks for its home copy, follows it while the worker makes it, then downloads it. */
function FileRow({ itemId, line, file }: { itemId: string; line: string; file: DownloadFile }) {
  const t = useTranslations("downloads");
  const tl = useTranslations("orderPath.line");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [phase, setPhase] = useState<Phase>({ at: "idle" });
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mounted = useRef(true);

  const partKey = `${line}.${partOption(line)}.${file.part}`;
  const part = file.part && tl.has(partKey) ? tl(partKey) : "";
  const label = [part, t(`kind.${file.kind}`)].filter(Boolean).join(" · ");

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  /** The tap that asked for the file may still start its download; the link shown after stays for another try. */
  function save(url: string) {
    const a = document.createElement("a");
    a.href = url;
    a.download = file.name;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  /** While the worker makes the copy: its state every few seconds, for about three minutes. */
  function follow(polls: number) {
    timer.current = setTimeout(async () => {
      const r = await downloadsApi.state(itemId, file, locale);
      if (!mounted.current) return;
      if (r.ok && r.data.status === "ready" && r.data.url) return setPhase({ at: "ready", url: r.data.url });
      if (r.ok && r.data.status === "failed") return setPhase({ at: "failed" });
      if (polls + 1 >= POLL_LIMIT) return setPhase({ at: "slow" });
      setPhase({ at: "preparing", polls: polls + 1 });
      follow(polls + 1);
    }, POLL_MS);
  }

  async function start() {
    if (timer.current) clearTimeout(timer.current);
    setPhase({ at: "asking" });
    const r = await downloadsApi.prepare(itemId, file, locale);
    if (!r.ok) {
      const message = errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown"));
      return setPhase({ at: "error", message });
    }
    if (r.data.status === "ready" && r.data.url) {
      save(r.data.url);
      return setPhase({ at: "started", url: r.data.url });
    }
    setPhase({ at: "preparing", polls: 0 });
    follow(0);
  }

  return (
    <div className="flex flex-col gap-1.5 rounded-md border border-line bg-paper-raised p-3" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-small font-semibold text-ink">{label}</span>
        {(phase.at === "idle" || phase.at === "asking") && (
          <Button
            size="sm"
            variant="solid"
            onClick={start}
            loading={phase.at === "asking"}
            aria-label={`${t("download")}: ${label}`}
          >
            {t("download")}
          </Button>
        )}
        {phase.at === "ready" && (
          <a href={phase.url} download={file.name} className={buttonClasses("primary", "sm")}>
            {t("readyNow")}
          </a>
        )}
      </div>
      {phase.at === "preparing" && (
        <p className="flex items-center gap-2 text-caption text-ink-muted">
          <Spinner />
          {t("preparing")}
        </p>
      )}
      {phase.at === "started" && (
        <p className="text-caption text-success">
          {t("started")}{" "}
          <a href={phase.url} download={file.name} className="font-semibold text-night-900 underline">
            {t("again")}
          </a>
        </p>
      )}
      {(phase.at === "failed" || phase.at === "slow" || phase.at === "error") && (
        <div className="flex flex-col items-start gap-2">
          <Alert tone={phase.at === "slow" ? "info" : "error"}>
            {phase.at === "error" ? phase.message : t(phase.at)}
          </Alert>
          <Button size="sm" variant="secondary" onClick={start}>
            {t("retry")}
          </Button>
        </div>
      )}
    </div>
  );
}

/**
 * The account page's «ملفات للتنزيل»: each downloadable line with its title, its order and its files. The
 * "ready to download" email links here (`/account#downloads`).
 */
export function DownloadsSection({ lines }: { lines: DownloadLine[] }) {
  const t = useTranslations("downloads");
  const text = useSummaryText();
  const locale = useLocale();
  const section = useRef<HTMLElement>(null);

  useEffect(() => {
    if (lines.length && window.location.hash === "#downloads") section.current?.scrollIntoView({ block: "start" });
  }, [lines.length]);

  if (!lines.length) return null;
  return (
    <section
      id="downloads"
      ref={section}
      aria-labelledby="downloads-title"
      className="flex scroll-mt-4 flex-col gap-3 rounded-xl border border-line bg-paper-raised p-4"
    >
      <div className="flex flex-col gap-1">
        <h2 id="downloads-title" className="text-[18px] text-night-900">
          {t("title")}
        </h2>
        <p className="text-caption text-ink-muted">{t("hint")}</p>
      </div>
      {lines.map((l) => {
        const summary = lineSummary(
          { line: l.line, options: l.options, child_name: l.child_name, book_title: l.book_title },
          { product: locale === "ar" ? l.name_ar : l.name_en },
        );
        const details = summary.details.map(text).filter(Boolean).join(" · ");
        return (
          <div key={l.item_id} className="flex flex-col gap-2 border-t border-line/60 pt-3 first-of-type:border-0">
            <div className="flex flex-col gap-0.5">
              <strong className="text-body text-ink">{text(summary.title)}</strong>
              <span className="text-caption text-ink-muted">
                {[details, t("order", { code: l.order_code })].filter(Boolean).join(" · ")}
              </span>
            </div>
            <DownloadButton itemId={l.item_id} line={l} />
          </div>
        );
      })}
    </section>
  );
}
