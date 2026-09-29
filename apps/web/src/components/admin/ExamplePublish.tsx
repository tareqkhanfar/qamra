"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";

/**
 * Approval queue: show an approved sample book on the public site, or take it off (docs/decisions.md,
 * "Public examples"). Only sample books of invented children: the API refuses anything else, and the admin
 * confirms the child is invented before publishing.
 */
export function ExamplePublish({
  bookId,
  status,
  published,
  onChange,
  onError,
}: {
  bookId: string;
  status: string;
  published: boolean;
  onChange: () => void;
  onError: (text: string) => void;
}) {
  const t = useTranslations("examples.admin");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [busy, setBusy] = useState(false);
  const approved = status === "approved" || status === "ordered" || status === "printed";

  async function toggle() {
    if (!published && !window.confirm(t("confirm"))) return;
    setBusy(true);
    const r = await api<unknown>(`/api/admin/books/${bookId}/example`, {
      method: published ? "DELETE" : "POST",
      json: published ? {} : { synthetic_child: true },
    });
    setBusy(false);
    if (r.ok) onChange();
    else onError(errorText(r.error, locale, te("unknown")));
  }

  return (
    <Button
      variant={published ? "secondary" : "solid"}
      size="sm"
      disabled={busy || (!published && !approved)}
      title={!published && !approved ? t("needsApproval") : undefined}
      onClick={() => void toggle()}
    >
      {published ? t("unpublish") : t("publish")}
    </Button>
  );
}
