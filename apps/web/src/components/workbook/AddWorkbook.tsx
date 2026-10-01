"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Link, useRouter } from "@/i18n/navigation";
import { api, errorText, type User } from "@/lib/api";
import type { Child } from "@/lib/create";
import type { Cart } from "@/lib/store";
import { emptyFamily, FamilyDetails, familyPayload } from "./FamilyDetails";

/** Where a parent without a ready character goes: the create flow draws one, then adds this book. */
export const createFor = (sku: string, child?: string) =>
  `/create?${new URLSearchParams({ product: sku, line: "magic", style: "watercolor", ...(child ? { child } : {}) })}`;

/**
 * «أضف للسلة» on an activity book: the book is drawn with the child's approved character (Addendum 9 §1.6),
 * so the parent picks which child («شخصية ليان جاهزة»); without one, the create flow draws it first.
 */
export function AddWorkbook({
  sku,
  family: askFamily = false,
}: {
  sku: string | null;
  family?: boolean; // «مغامراتي مع عائلتي»: ask who is in the family (optional)
}) {
  const t = useTranslations("workbook");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const [ready, setReady] = useState<Child[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [family, setFamily] = useState(emptyFamily);

  async function start() {
    if (!sku) return;
    setBusy(true);
    setError(null);
    const me = await api<User>("/api/auth/me");
    if (!me.ok) {
      setBusy(false);
      router.push(createFor(sku));
      return;
    }
    const kids = await api<Child[]>("/api/create/children");
    setBusy(false);
    const approved = kids.ok ? kids.data.filter((c) => c.characters.some((ch) => ch.approved)) : [];
    if (!approved.length) {
      router.push(createFor(sku, kids.ok && kids.data.length === 1 ? kids.data[0]!.id : undefined));
      return;
    }
    setReady(approved);
    dialog.current?.showModal();
  }

  async function add(child: Child) {
    if (!sku) return;
    setBusy(true);
    setError(null);
    const details = askFamily ? familyPayload(family) : undefined;
    const r = await api<Cart>("/api/shop/workbooks/cart", {
      json: { sku, child_id: child.id, ...(details ? { family: details } : {}) },
    });
    setBusy(false);
    if (r.ok) {
      dialog.current?.close();
      router.push("/cart");
    } else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <>
      <button
        type="button"
        onClick={() => void start()}
        disabled={busy || !sku}
        className="flex min-h-14 grow items-center justify-center rounded-full bg-amber-500 px-6 text-[17px] font-bold text-night-950 hover:shadow-lamp disabled:bg-paper-sunk disabled:text-ink-faint disabled:shadow-none md:max-w-[360px] md:grow-0 md:px-12 ltr:md:ml-auto rtl:md:mr-auto"
      >
        {t("add")}
      </button>
      <dialog
        ref={dialog}
        aria-labelledby="who-title"
        className="m-auto w-[min(92vw,420px)] rounded-[24px] bg-paper p-5 text-ink backdrop:bg-night-950/55"
      >
        <div className="flex flex-col gap-3">
          <h2 id="who-title" className="text-[22px] text-night-900">
            {t("chooser.title")}
          </h2>
          {error && <Alert>{error}</Alert>}
          {askFamily && <FamilyDetails value={family} onChange={setFamily} />}
          {ready.map((c) => (
            <button
              key={c.id}
              type="button"
              disabled={busy}
              onClick={() => void add(c)}
              className="flex min-h-14 items-center justify-between gap-3 rounded-[18px] border-[1.5px] border-line bg-paper-raised px-4 text-start hover:border-night-500"
            >
              <strong className="text-body text-night-900">{c.name}</strong>
              <span className="rounded-full bg-success-bg px-2.5 py-1 text-caption font-bold text-success">
                ✓ {t("chooser.ready", { name: c.name })}
              </span>
            </button>
          ))}
          <Link
            href={createFor(sku ?? "")}
            className="min-h-11 content-center text-small font-bold text-amber-700 underline"
          >
            {t("chooser.other")}
          </Link>
          <button
            type="button"
            onClick={() => dialog.current?.close()}
            className="min-h-11 self-start px-1 text-small font-semibold text-night-900"
          >
            {t("chooser.close")}
          </button>
        </div>
      </dialog>
    </>
  );
}
