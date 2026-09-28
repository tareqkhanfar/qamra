"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { MfaSetup } from "@/components/MfaSetup";
import { Button } from "@/components/ui/Button";
import { usePathname, useRouter } from "@/i18n/navigation";
import { api, type User } from "@/lib/api";

type State =
  { kind: "loading" } | { kind: "ok" } | { kind: "setup"; user: User } | { kind: "again" } | { kind: "forbidden" };

/**
 * Admin pages need an admin session that passed two-step verification (Addendum 3 §6). The API enforces
 * it on every admin endpoint; this gate shows the right next step instead of a blank page.
 */
export function AdminGate({ children }: { children: ReactNode }) {
  const t = useTranslations("mfa");
  const ta = useTranslations("admin");
  const router = useRouter();
  const pathname = usePathname();
  const [state, setState] = useState<State>({ kind: "loading" });

  const check = useCallback(async () => {
    const res = await api<User>("/api/auth/me");
    if (!res.ok) {
      if (res.status === 401) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      else setState({ kind: "forbidden" });
      return;
    }
    const user = res.data;
    if (user.role !== "admin") setState({ kind: "forbidden" });
    else if (!user.mfa_enabled) setState({ kind: "setup", user });
    else if (!user.mfa_verified) setState({ kind: "again" });
    else setState({ kind: "ok" });
  }, [pathname, router]);

  useEffect(() => {
    void (async () => {
      await check();
    })();
  }, [check]);

  if (state.kind === "loading") return <div className="h-64 animate-pulse rounded-xl bg-paper-sunk" aria-busy="true" />;
  if (state.kind === "setup") return <MfaSetup hasPassword={state.user.has_password} onDone={() => void check()} />;
  if (state.kind === "again")
    return (
      <div className="mx-auto mt-10 flex max-w-md flex-col items-center gap-3 text-center">
        <h1 className="text-h2 text-night-900">{t("againTitle")}</h1>
        <p className="text-ink-muted">{t("againLead")}</p>
        <Button
          variant="solid"
          onClick={async () => {
            await api("/api/auth/logout", { method: "POST" });
            router.replace(`/login?next=${encodeURIComponent(pathname)}`);
          }}
        >
          {t("signInAgain")}
        </Button>
      </div>
    );
  if (state.kind === "forbidden")
    return (
      <div className="mx-auto mt-10 flex max-w-md flex-col gap-2 text-center">
        <h1 className="text-h2 text-night-900">{ta("forbiddenTitle")}</h1>
        <p className="text-ink-muted">{ta("forbiddenBody")}</p>
      </div>
    );
  return <>{children}</>;
}
