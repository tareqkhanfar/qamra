"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Link } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { accusativeName } from "@/lib/arabicName";
import { companionApi, companionImage, drawingImage, type MyCompanion } from "@/lib/companion";

const STAGES = ["bg-night-100", "bg-amber-100", "bg-success-bg"];

/** Design MyCompanions («أصحابي»): every companion the parent chose, ready for a new story with its child. */
export function MyCompanions() {
  const t = useTranslations("companion.mine");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [list, setList] = useState<MyCompanion[] | null>(null);
  const [child, setChild] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      const r = await companionApi.mine();
      if (alive) setList(r.ok ? r.data : []);
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function remove(c: MyCompanion) {
    if (!window.confirm(t("confirm", { name: c.name }))) return;
    const r = await companionApi.remove(c.id);
    if (r.ok) {
      setList((l) => (l ?? []).filter((x) => x.id !== c.id));
      setNotice(t("deleted", { name: c.name, nameAcc: accusativeName(c.name) }));
    } else setNotice(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  if (list === null) return <div className="h-48 animate-pulse rounded-xl bg-paper-sunk" aria-busy="true" />;
  const kids = [...new Map(list.map((c) => [c.child_id, c.child_name])).entries()];
  const shown = child ? list.filter((c) => c.child_id === child) : list;
  const tab = (on: boolean) =>
    `min-h-11 shrink-0 rounded-full px-4 text-small ${on ? "bg-night-900 font-bold text-paper" : "border-[1.5px] border-line bg-paper-raised"}`;

  return (
    <section className="flex flex-col gap-3" aria-labelledby="companions-title">
      <div className="flex flex-col gap-1">
        <h2 id="companions-title" className="text-[22px] text-night-900">
          {t("title")}
        </h2>
        <p className="text-small text-ink-muted">{t("body")}</p>
      </div>
      {kids.length > 1 && (
        <div role="tablist" className="flex gap-2 overflow-x-auto">
          <button
            type="button"
            role="tab"
            aria-selected={!child}
            onClick={() => setChild(null)}
            className={tab(!child)}
          >
            {t("all", { count: list.length })}
          </button>
          {kids.map(([id, name]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={child === id}
              onClick={() => setChild(id)}
              className={tab(child === id)}
            >
              {t("of", { name })}
            </button>
          ))}
        </div>
      )}
      {notice && <Alert tone="info">{notice}</Alert>}
      <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-3">
        {shown.map((c, i) => (
          <article key={c.id} className="flex flex-col gap-2 rounded-[22px] border border-line bg-paper-raised p-2.5">
            <div
              className={`relative flex h-[150px] items-center justify-center overflow-hidden rounded-2xl ${STAGES[i % STAGES.length]}`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API */}
              <img
                src={companionImage(c.id)}
                alt={t("alt", { name: c.name })}
                className="max-h-full max-w-full object-contain"
              />
              <div className="absolute bottom-1.5 left-1.5 w-11 -rotate-6 overflow-hidden rounded-md border-2 border-white bg-white shadow-[0_2px_6px_rgba(22,32,74,0.2)]">
                {/* eslint-disable-next-line @next/next/no-img-element -- private image through the API */}
                <img src={drawingImage(c.id, "cleaned")} alt="" className="block w-full" />
              </div>
            </div>
            <strong className="font-display text-[20px] text-night-900">{c.name}</strong>
            <span className="text-caption text-ink-muted">{t("meta", { name: c.child_name, books: c.books })}</span>
            <Link
              href={`/create?child=${c.child_id}&companion=${c.id}`}
              className="flex min-h-11 items-center justify-center rounded-full border-[1.5px] border-night-900 text-caption font-bold"
            >
              {t("newStory")}
            </Link>
            <button
              type="button"
              onClick={() => void remove(c)}
              className="min-h-11 text-caption text-danger underline-offset-4 hover:underline"
            >
              {t("delete")}
            </button>
          </article>
        ))}
        <Link
          href="/create"
          className="flex min-h-[250px] flex-col items-center justify-center gap-2 rounded-[22px] border-2 border-dashed border-amber-700 p-3 text-center text-amber-700"
        >
          <svg
            className="size-9"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M12 5v14M5 12h14" />
          </svg>
          <strong className="text-[15px]">{t("new")}</strong>
        </Link>
      </div>
    </section>
  );
}
