import { cookies } from "next/headers";

const API = () => process.env.API_INTERNAL_URL ?? "http://localhost:8000";

/**
 * True when this request carries an admin session that passed two-step verification (what `AdminGate` and the
 * API's `require_admin` ask). Only then does /admin ship the staff's messages (costs, margins, printer prices);
 * an expired access cookie reads as false here, and the gate refreshes the page once the browser has renewed it.
 */
export async function isVerifiedAdmin(): Promise<boolean> {
  const token = (await cookies()).get("qamra_at")?.value;
  if (!token) return false;
  try {
    const res = await fetch(`${API()}/api/auth/me`, {
      headers: { cookie: `qamra_at=${token}` },
      cache: "no-store",
    });
    if (!res.ok) return false;
    const user = (await res.json()) as { role?: string; mfa_enabled?: boolean; mfa_verified?: boolean };
    return user.role === "admin" && user.mfa_enabled === true && user.mfa_verified === true;
  } catch {
    return false;
  }
}
