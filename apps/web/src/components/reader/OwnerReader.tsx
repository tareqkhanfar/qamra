"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { buttonClasses } from "@/components/ui/Button";
import { Link, useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { readerApi, type OwnerBook } from "@/lib/reader";
import { BookReader } from "./BookReader";
import { ReaderMessage, ReaderSkeleton } from "./ReaderStates";
import { SharePanel } from "./SharePanel";

const round =
  "flex size-11 shrink-0 items-center justify-center rounded-full bg-night-900 text-paper hover:bg-night-800";

/** «كتبي» → the reader for the parent's own book, with the share link (a finished book only). */
export function OwnerReader({ id }: { id: string }) {
  const t = useTranslations("reader");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [book, setBook] = useState<OwnerBook | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);

  useEffect(() => {
    let alive = true;
    void readerApi.book(id).then((r) => {
      if (!alive) return;
      if (r.ok) return setBook(r.data);
      if (r.status === 401) return router.replace(`/login?next=${encodeURIComponent(`/books/${id}`)}`);
      setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    });
    return () => {
      alive = false;
    };
  }, [id, locale, router, te]);

  if (error) return <ReaderMessage title={t("unavailable")} body={error} href="/account" cta={t("backToBooks")} />;
  if (!book) return <ReaderSkeleton label={t("loading")} />;

  const close = (
    <Link href="/account" aria-label={t("close")} className={round}>
      <svg
        className="size-5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <path d="M6 6l12 12M18 6L6 18" />
      </svg>
    </Link>
  );
  const shareButton = book.can_share && (
    <button type="button" onClick={() => setSharing(true)} aria-label={t("share.open")} className={round}>
      <svg
        className="size-5"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="18" cy="5" r="3" />
        <circle cx="6" cy="12" r="3" />
        <circle cx="18" cy="19" r="3" />
        <path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4" />
      </svg>
    </button>
  );
  const end =
    book.kind === "preview" ? (
      <>
        <p className="text-body text-ink-muted">{t("previewEnd", { name: book.child_name })}</p>
        <Link href={`/create?child=${book.child_id}&book=${book.id}`} className={buttonClasses("primary", "md")}>
          {t("continueOrder")}
        </Link>
      </>
    ) : (
      <>
        <p className="text-body text-ink-muted">{t("ownerEnd", { name: book.child_name })}</p>
        {book.can_share && (
          <button type="button" onClick={() => setSharing(true)} className={buttonClasses("primary", "md")}>
            {t("share.open")}
          </button>
        )}
        <Link href="/account" className={buttonClasses("ghost", "sm")}>
          {t("backToBooks")}
        </Link>
      </>
    );

  return (
    <>
      <BookReader book={book} lead={close} actions={shareButton} end={end} keysEnabled={!sharing} />
      {book.can_share && (
        <SharePanel
          bookId={book.id}
          share={book.share}
          onChange={(share) => setBook((b) => (b ? { ...b, share } : b))}
          open={sharing}
          onOpenChange={setSharing}
        />
      )}
    </>
  );
}
