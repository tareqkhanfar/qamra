"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Device = { name: string; vram_gb: number; free_gb: number };
type SelfHosted = {
  provider: "fal" | "self_hosted";
  configured: boolean;
  workflow: string;
  approved: boolean;
  health: { ok: boolean; latency_ms?: number; devices?: Device[]; error?: string } | null;
  spend_usd: string;
  images: number;
  gpu_monthly_usd: string;
  recommendation: "no_data" | "stay_on_api" | "consider_gpu";
};

const usd = (v: string) => `$${Number(v).toFixed(2)}`;

/** Addendum 4 §8: the self-hosted GPU option — is the server up, and does it pay off yet? */
export function SelfHostedCard() {
  const t = useTranslations("selfHosted");
  const locale = useLocale();
  const [data, setData] = useState<SelfHosted | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    void (async () => {
      const r = await api<SelfHosted>("/api/admin/self-hosted");
      if (r.ok) setData(r.data);
      else setFailed(true); // staff without the settings permission don't see the card
    })();
  }, []);

  if (failed || !data) return null;
  const status = !data.configured ? "off" : data.health?.ok ? "up" : "down";
  const chip = {
    off: "bg-paper-sunk text-ink-muted",
    up: "bg-success-bg text-success",
    down: "bg-danger-bg text-danger",
  }[status];
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-4 md:p-6" lang={locale}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-h3 text-night-900">{t("title")}</h2>
        <span className={`rounded-full px-3 py-1 text-caption font-bold ${chip}`}>{t(`status.${status}`)}</span>
      </div>
      <p className="text-small text-ink-muted">
        {t("now", { provider: data.provider === "self_hosted" ? t("self") : "fal" })}{" "}
        {data.workflow && !data.approved && t("unapproved", { workflow: data.workflow })}
      </p>
      {data.health?.ok && (
        <ul className="flex flex-col gap-1 text-small">
          {(data.health.devices ?? []).map((d) => (
            <li key={d.name} dir="ltr" className="font-mono text-caption rtl:text-right">
              {d.name} · {d.free_gb}/{d.vram_gb} GB free · {data.health?.latency_ms} ms
            </li>
          ))}
        </ul>
      )}
      <dl className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-paper-sunk p-3">
          <dt className="text-caption text-ink-muted">{t("spend")}</dt>
          <dd className="font-display text-[22px] font-bold text-night-900 tabular-nums">{usd(data.spend_usd)}</dd>
          <dd className="text-caption text-ink-muted">{t("images", { n: data.images })}</dd>
        </div>
        <div className="rounded-lg bg-paper-sunk p-3">
          <dt className="text-caption text-ink-muted">{t("gpu")}</dt>
          <dd className="font-display text-[22px] font-bold text-night-900 tabular-nums">
            {Number(data.gpu_monthly_usd) ? usd(data.gpu_monthly_usd) : "—"}
          </dd>
        </div>
        <div className="rounded-lg bg-paper-sunk p-3">
          <dt className="text-caption text-ink-muted">{t("advice")}</dt>
          <dd className="text-small font-semibold text-night-900">{t(`recommendation.${data.recommendation}`)}</dd>
        </div>
      </dl>
    </section>
  );
}
