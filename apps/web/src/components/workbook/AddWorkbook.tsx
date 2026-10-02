"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { useRouter } from "@/i18n/navigation";
import { errorText } from "@/lib/api";
import { cartApi } from "@/lib/store";
import { familyPayload, type Family } from "./FamilyDetails";

/**
 * «أضيفوا للسلة» on an activity book: one tap puts the chosen variant in the cart, for guests too. The child
 * (and their character, reused when approved) comes after, from the cart's «أكملوا بيانات الطفل».
 */
export function AddWorkbook({
  sku,
  family,
}: {
  sku: string | null;
  family?: Family; // «مغامراتي مع عائلتي»: who is in the family, as the page collected it (optional)
}) {
  const t = useTranslations("workbook");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add() {
    if (!sku) return;
    setBusy(true);
    setError(null);
    const details = family ? familyPayload(family) : undefined;
    const r = await cartApi.add({ sku, ...(details ? { family: details } : {}) });
    if (r.ok) return router.push("/cart");
    setBusy(false);
    setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <>
      {error && (
        <p
          role="alert"
          className="absolute inset-x-0 bottom-full border-t border-line bg-paper px-4 py-2 text-center text-small font-semibold text-danger"
        >
          {error}
        </p>
      )}
      <button
        type="button"
        onClick={() => void add()}
        disabled={busy || !sku}
        className="flex min-h-14 grow items-center justify-center rounded-full bg-amber-500 px-6 text-[17px] font-bold text-night-950 hover:shadow-lamp disabled:bg-paper-sunk disabled:text-ink-faint disabled:shadow-none md:max-w-[360px] md:grow-0 md:px-12 ltr:md:ml-auto rtl:md:mr-auto"
      >
        {t("add")}
      </button>
    </>
  );
}
