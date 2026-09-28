"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Alert } from "@/components/ui/Alert";
import { buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { createApi, type Book, type Child } from "@/lib/create";
import { Frame } from "./Frame";

const POLL_MS = 4000;

/** Step 8 (design Create8): the story is written and the preview pages drawn; the parent may leave and come back. */
export function WritingStep({
  child,
  book,
  back,
  onChange,
}: {
  child: Child;
  book: Book;
  back: () => void;
  onChange: (b: Book) => void;
}) {
  const t = useTranslations("create");
  const [tick, setTick] = useState(0);
  const failed = book.status === "failed";
  const messages = t.raw("writing.messages") as string[];
  const done = book.progress.done ?? 0;
  const total = book.progress.total ?? 0;

  useEffect(() => {
    if (failed) return;
    const timer = setInterval(async () => {
      setTick((n) => n + 1);
      const r = await createApi.book(book.id);
      if (r.ok) onChange(r.data);
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [failed, book.id, onChange]);

  return (
    <Frame title={t("bookOf", { name: child.name })} label={t("steps.writing")} n={8} back={failed ? back : undefined}>
      {failed ? (
        <Alert>{t("writing.failed")}</Alert>
      ) : (
        <div role="status" className="flex flex-col items-center gap-5 py-8 text-center">
          <MoonPhase p={total ? Math.max(0.08, done / total) : ((tick % 12) + 1) / 12} className="size-28" />
          <h1 className="text-[26px] text-night-900">{t("writing.title", { name: child.name })}</h1>
          <p className="min-h-7 text-body text-ink-muted">{messages[tick % messages.length]}</p>
          {total > 0 && (
            <div className="flex w-full max-w-xs flex-col gap-2">
              <div className="flex h-2 rounded-full bg-paper-sunk">
                <div
                  className="rounded-full bg-amber-500 transition-all"
                  style={{ width: `${Math.round((done / total) * 100)}%` }}
                />
              </div>
              <span className="text-caption text-ink-muted">{t("writing.progress", { done, total })}</span>
            </div>
          )}
        </div>
      )}
      <div className="flex flex-col gap-2 rounded-2xl border border-line bg-paper-raised p-4">
        <strong className="text-body">{t("writing.away")}</strong>
        <p className="text-small text-ink-muted">{t("writing.awayBody")}</p>
        <Link href="/account" className={buttonClasses("secondary", "sm", "self-start")}>
          {t("writing.account")}
        </Link>
      </div>
    </Frame>
  );
}
