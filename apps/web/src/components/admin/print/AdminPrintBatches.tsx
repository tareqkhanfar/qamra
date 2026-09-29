"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { api, errorText } from "@/lib/api";
import { PrintBatchDetail } from "./PrintBatchDetail";
import { BATCH_TONE, type BatchDetail, type Batches, type OrderBrief } from "./types";

function OrderChips({ orders, tone }: { orders: OrderBrief[]; tone: string }) {
  return (
    <ul className="flex flex-wrap gap-2">
      {orders.map((o) => (
        <li key={o.id} className={`rounded-full px-3 py-1 text-caption font-semibold ${tone}`}>
          <span dir="ltr">{o.code}</span> · {o.approved}/{o.books}
          {o.organization ? ` · ${o.organization}` : ""}
        </li>
      ))}
    </ul>
  );
}

/** Print batches (CLAUDE.md §7 step 7, Phase 3): collect → send to the printer → printing → done → ship. */
export function AdminPrintBatches() {
  const t = useTranslations("printBatches");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [data, setData] = useState<Batches | null>(null);
  const [detail, setDetail] = useState<BatchDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fail = useCallback(
    (e: Parameters<typeof errorText>[0], status: number) =>
      setError(errorText(e, locale, status === 0 ? te("network") : te("unknown"))),
    [locale, te],
  );
  const load = useCallback(async () => {
    const r = await api<Batches>("/api/admin/print-batches");
    if (r.ok) setData(r.data);
    else fail(r.error, r.status);
  }, [fail]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  const run = async <T,>(path: string, init: { method?: string; json?: unknown }, done: (value: T) => void) => {
    setBusy(true);
    setError(null);
    const r = await api<T>(path, init);
    setBusy(false);
    if (!r.ok) return fail(r.error, r.status);
    done(r.data);
    void load();
  };
  const open = (id: string) => run<BatchDetail>(`/api/admin/print-batches/${id}`, {}, setDetail);
  const collect = () => run<Batches>("/api/admin/print-batches/collect", { json: {} }, setData);
  const act = (action: BatchDetail["actions"][number]) => {
    if (!detail) return;
    if (action === "send" && !window.confirm(t("sendConfirm", { code: detail.code }))) return;
    const base = `/api/admin/print-batches/${detail.id}`;
    const path = action === "printing" || action === "done" ? `${base}/status` : `${base}/${action}`;
    const json = action === "printing" || action === "done" ? { to: action } : {};
    void run<BatchDetail>(path, { json }, setDetail);
  };
  const remove = (orderId: string) =>
    detail &&
    void run<BatchDetail>(`/api/admin/print-batches/${detail.id}/orders/${orderId}`, { method: "DELETE" }, setDetail);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-h2 text-night-900">{t("title")}</h1>
          <p className="text-small text-ink-muted">{t("lead")}</p>
        </div>
        <Button variant="primary" onClick={() => void collect()} loading={busy} disabled={!data?.ready.length}>
          {t("collect", { count: data?.ready.length ?? 0 })}
        </Button>
      </div>
      {data && !data.printer_email_set && (
        <Alert tone="info">
          {t("noPrinterEmail")}{" "}
          <Link href="/admin/settings" className="font-bold underline">
            {t("settingsLink")}
          </Link>
        </Alert>
      )}
      {error && <Alert>{error}</Alert>}

      {data && (data.ready.length > 0 || data.waiting.length > 0) && (
        <section className="flex flex-col gap-3 rounded-lg border border-line bg-paper-raised p-4">
          {data.ready.length > 0 && (
            <>
              <h2 className="text-[18px] text-night-900">{t("ready")}</h2>
              <OrderChips orders={data.ready} tone="bg-success-bg text-success" />
            </>
          )}
          {data.waiting.length > 0 && (
            <>
              <h2 className="text-[18px] text-night-900">{t("waiting")}</h2>
              <p className="text-caption text-ink-muted">{t("waitingHint")}</p>
              <OrderChips orders={data.waiting} tone="bg-paper-sunk text-ink" />
            </>
          )}
        </section>
      )}

      <div className="grid gap-5 xl:grid-cols-[1fr_460px] xl:items-start">
        <div className="overflow-hidden rounded-lg border border-line bg-paper-raised">
          {data && data.batches.length === 0 && <p className="p-6 text-center text-ink-muted">{t("empty")}</p>}
          {data?.batches.map((b) => (
            <button
              key={b.id}
              type="button"
              onClick={() => void open(b.id)}
              className={`flex w-full items-center gap-3 border-b border-line/60 p-3 text-start hover:bg-paper-sunk ${detail?.id === b.id ? "bg-night-100" : ""}`}
            >
              <span className="flex grow flex-col">
                <strong dir="ltr" className="self-start text-night-900">
                  {b.code}
                </strong>
                <span className="text-small text-ink-muted">
                  {b.organization ?? t("families")} ·{" "}
                  {t("counts", { orders: b.orders, books: b.books, copies: b.copies })}
                </span>
              </span>
              <span className={`rounded-full px-2.5 py-1 text-caption font-bold ${BATCH_TONE[b.status]}`}>
                {t(`status.${b.status}`)}
              </span>
            </button>
          ))}
        </div>
        {detail && <PrintBatchDetail batch={detail} busy={busy} onAction={act} onRemove={remove} />}
      </div>
    </div>
  );
}
