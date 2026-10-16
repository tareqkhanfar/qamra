"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { nameCases } from "@/lib/arabicName";
import type { Child } from "@/lib/create";
import { refillTime } from "@/lib/drawLimits";

/** The time now, again every half minute: the «تتجدّد بعد …» line counts down and the button comes back on time. */
export function useNow(every = 30_000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), every);
    return () => clearInterval(timer);
  }, [every]);
  return now;
}

/**
 * The line shown when no free drawing is left now (lib/drawLimits): when the next one comes back, in time left and
 * on the parent's clock, and (`earlier`) that one of the child's earlier drawings can be chosen meanwhile.
 */
export function DrawLimitNote({
  child,
  now,
  resetAt,
  earlier,
}: {
  child: Pick<Child, "name" | "gender">;
  now: number;
  resetAt: string | null | undefined;
  earlier: boolean;
}) {
  const t = useTranslations("create.drawLimit");
  const locale = useLocale();
  const who = { ...nameCases(child.name), gender: child.gender };
  const when = refillTime(resetAt, now, locale);
  return (
    <p role="status" className="rounded-2xl bg-amber-100 p-4 text-small text-night-900">
      {when ? t(earlier ? "noneLeft" : "noneLeftAlone", { ...who, ...when }) : t(earlier ? "soon" : "soonAlone", who)}
    </p>
  );
}
