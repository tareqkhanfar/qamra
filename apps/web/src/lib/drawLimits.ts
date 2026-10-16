/**
 * The child's free drawings (owner, 2026-10-16; the API's qamra_api.draw_limits): they come back with time instead
 * of running out for good. The API sends how many are left now (`redraws_left`), when the next one comes back
 * (`redraws_reset_at`), how many there are (`redraws_total`) and after how long each one comes back
 * (`redraws_window_hours`); a staff account is never limited (`redraws_unlimited`).
 */

/** What these rules read of a child (lib/create `Child`). */
export type FreeDraws = {
  redraws_left: number;
  redraws_reset_at?: string | null;
  redraws_total?: number;
  redraws_window_hours?: number;
  redraws_unlimited?: boolean;
};

/** The free drawings the parent may ask for at `now`: one is back once its time has passed (the API decides). */
export function drawsLeft(child: FreeDraws, now: number, blockedUntil: string | null = null): number {
  if (child.redraws_unlimited) return Math.max(1, child.redraws_total ?? 1);
  if (blockedUntil && Date.parse(blockedUntil) > now) return 0; // the API just said none are left
  if (child.redraws_left > 0) return child.redraws_left;
  const until = blockedUntil ?? child.redraws_reset_at;
  return until && Date.parse(until) <= now ? 1 : 0;
}

/** Whole hours and minutes until `resetAt`, rounded up to the minute (never under one minute). */
export function waitParts(resetAt: string | Date, now: number): { hours: number; minutes: number } {
  const ms = new Date(resetAt).getTime() - now;
  const total = Math.max(1, Math.ceil(ms / 60_000));
  return { hours: Math.floor(total / 60), minutes: total % 60 };
}

/** Arabic counted nouns after a preposition («بعد ساعتين»): 1, 2, 3–10, then 11 and up. */
function arabicCount(n: number, one: string, two: string, few: string, many: string): string {
  if (n === 1) return one;
  if (n === 2) return two;
  const rest = n % 100;
  if (rest >= 3 && rest <= 10) return `${n} ${few}`;
  return `${n} ${many}`;
}

/**
 * How long until the next free drawing, as a parent reads it after «بعد» / "in": «ساعة و20 دقيقة», «ساعتين»,
 * «5 دقائق»; "1 hour and 20 minutes", "an hour", "2 hours", "5 minutes".
 */
export function formatWait(parts: { hours: number; minutes: number }, locale: string): string {
  const { hours, minutes } = parts;
  if (locale === "ar") {
    const h = hours ? arabicCount(hours, "ساعة", "ساعتين", "ساعات", "ساعة") : "";
    const m = minutes ? arabicCount(minutes, "دقيقة", "دقيقتين", "دقائق", "دقيقة") : "";
    return h && m ? `${h} و${m}` : h || m;
  }
  if (!minutes) return hours === 1 ? "an hour" : `${hours} hours`;
  if (!hours) return minutes === 1 ? "a minute" : `${minutes} minutes`;
  return `${hours} ${hours === 1 ? "hour" : "hours"} and ${minutes} ${minutes === 1 ? "minute" : "minutes"}`;
}

/** The clock time on the parent's own device: «3:40 م», "3:40 PM". */
export function formatClock(resetAt: string | Date, locale: string, timeZone?: string): string {
  return new Intl.DateTimeFormat(locale === "ar" ? "ar-EG-u-nu-latn" : "en-US", {
    hour: "numeric",
    minute: "2-digit",
    ...(timeZone ? { timeZone } : {}),
  }).format(new Date(resetAt));
}

/** `{time}` and `{clock}` for the «تتجدّد بعد {time} (عند الساعة {clock})» line, or null when the time is unknown or past. */
export function refillTime(
  resetAt: string | null | undefined,
  now: number,
  locale: string,
  timeZone?: string,
): { time: string; clock: string } | null {
  if (!resetAt || Number.isNaN(Date.parse(resetAt)) || Date.parse(resetAt) <= now) return null;
  return { time: formatWait(waitParts(resetAt, now), locale), clock: formatClock(resetAt, locale, timeZone) };
}

/** `details.reset_at` of the API's «free_draws_used» answer (the moment the next free drawing comes back). */
export function blockedUntilOf(
  error: { code: string; details?: Record<string, unknown> } | null | undefined,
): string | null {
  if (error?.code !== "free_draws_used") return null;
  const at = error.details?.reset_at;
  return typeof at === "string" ? at : null;
}
