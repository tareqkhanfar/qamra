"use client";

import { useLocale, useTranslations } from "next-intl";
import { Button, buttonClasses } from "@/components/ui/Button";
import { BATCH_TONE, type BatchDetail } from "./types";

type Props = {
  batch: BatchDetail;
  busy: boolean;
  onAction: (action: BatchDetail["actions"][number]) => void;
  onRemove: (orderId: string) => void;
};

/** One batch: its orders and books, the printer email's outcome, and the next step. */
export function PrintBatchDetail({ batch, busy, onAction, onRemove }: Props) {
  const t = useTranslations("printBatches");
  const to = useTranslations("orders");
  const locale = useLocale();
  const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString(locale) : "—");

  return (
    <aside className="flex flex-col gap-4 rounded-lg border border-line bg-paper-raised p-4 xl:sticky xl:top-6">
      <div className="flex items-center justify-between gap-2">
        <strong dir="ltr" className="text-[20px] text-night-900">
          {batch.code}
        </strong>
        <span className={`rounded-full px-2.5 py-1 text-caption font-bold ${BATCH_TONE[batch.status]}`}>
          {t(`status.${batch.status}`)}
        </span>
      </div>
      <p className="text-small text-ink-muted">
        {batch.organization ?? t("families")} ·{" "}
        {t("counts", { orders: batch.orders, books: batch.books, copies: batch.copies })}
      </p>
      <dl className="grid grid-cols-2 gap-2 text-small">
        <dt className="text-ink-muted">{t("sentAt")}</dt>
        <dd>{when(batch.sent_at)}</dd>
        <dt className="text-ink-muted">{t("email")}</dt>
        <dd>{batch.email ? t(`emailStatus.${batch.email}`) : "—"}</dd>
        <dt className="text-ink-muted">{t("linkUntil")}</dt>
        <dd>{when(batch.link_expires_at)}</dd>
        <dt className="text-ink-muted">{t("doneAt")}</dt>
        <dd>{when(batch.done_at)}</dd>
      </dl>

      <div className="flex flex-wrap gap-2">
        {batch.actions.map((a) => (
          <Button
            key={a}
            variant={a === "resend" ? "secondary" : "solid"}
            size="sm"
            loading={busy}
            onClick={() => onAction(a)}
          >
            {t(`actions.${a}`)}
          </Button>
        ))}
        <a href={`/api/admin/print-batches/${batch.id}/manifest.csv`} className={buttonClasses("ghost", "sm")}>
          {t("csv")}
        </a>
      </div>
      {batch.actions.includes("send") && <p className="text-caption text-ink-muted">{t("sendHint")}</p>}

      <ul className="flex flex-col gap-3">
        {batch.items.map((o) => (
          <li key={o.id} className="rounded-md border border-line p-3">
            <div className="flex items-center justify-between gap-2">
              <strong dir="ltr">{o.code}</strong>
              <span className="text-caption text-ink-muted">
                {to(`statuses.${o.status}`)} · {o.city ?? "—"}
              </span>
            </div>
            <ul className="mt-2 flex flex-col gap-1.5 text-small">
              {o.items.map((i, k) => (
                <li key={k} className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  {i.n !== null && (
                    <span dir="ltr" className="font-mono text-caption text-ink-muted">
                      {String(i.n).padStart(3, "0")}
                    </span>
                  )}
                  <span className="grow">
                    {i.title}
                    {i.child_name ? ` · ${i.child_name}` : ""} · {t(`formats.${i.format}`)} × {i.copies}
                  </span>
                  {i.book_id && i.files && (
                    <>
                      <a
                        className="text-caption font-semibold text-amber-700 underline"
                        href={`/api/admin/books/${i.book_id}/files/interior.pdf`}
                      >
                        {t("interior")}
                      </a>
                      <a
                        className="text-caption font-semibold text-amber-700 underline"
                        href={`/api/admin/books/${i.book_id}/files/cover.pdf`}
                      >
                        {t("cover")}
                      </a>
                    </>
                  )}
                </li>
              ))}
            </ul>
            {batch.status === "open" && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-1 text-danger hover:text-danger"
                disabled={busy}
                onClick={() => onRemove(o.id)}
              >
                {t("remove")}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
}
