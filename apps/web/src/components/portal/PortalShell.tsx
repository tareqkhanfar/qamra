"use client";

import { useLocale, useTranslations } from "next-intl";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { MoonMark } from "@/components/Logo";
import { Button, buttonClasses } from "@/components/ui/Button";
import { brandName } from "@/config/brand";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { portalApi, type Me } from "@/lib/portal";

type Ctx = { me: Me; reload: () => Promise<void> };
const PortalContext = createContext<Ctx | null>(null);

export function usePortal(): Ctx {
  const ctx = useContext(PortalContext);
  if (!ctx) throw new Error("usePortal outside PortalShell");
  return ctx;
}

export type Section = "dashboard" | "board" | "import" | "book" | "planner" | "review" | "order";
const CLASS_SECTIONS: { id: Section; href: string }[] = [
  { id: "board", href: "" },
  { id: "import", href: "/import" },
  { id: "book", href: "/book" },
  { id: "planner", href: "/planner" },
  { id: "review", href: "/review" },
  { id: "order", href: "/order" },
];

type State = { kind: "loading" } | { kind: "ok"; me: Me } | { kind: "not_school" } | { kind: "error" };

/** Portal chrome (design PortalDashboard): the school's sidebar, then the page. Loads the school once. */
export function PortalShell({ active, classId, children }: { active: Section; classId?: string; children: ReactNode }) {
  const t = useTranslations("portal");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [state, setState] = useState<State>({ kind: "loading" });

  const load = useCallback(async () => {
    const r = await portalApi.me();
    if (r.ok) setState({ kind: "ok", me: r.data });
    else if (r.status === 401) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (r.error?.code === "not_school") setState({ kind: "not_school" });
    else setState({ kind: "error" });
  }, [pathname, router]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  if (state.kind === "loading")
    return <div className="m-6 h-64 animate-pulse rounded-xl bg-paper-sunk" aria-busy="true" />;
  if (state.kind !== "ok")
    return (
      <Notice
        title={t(state.kind === "not_school" ? "notSchoolTitle" : "errorTitle")}
        body={t(state.kind === "not_school" ? "notSchoolBody" : "errorBody")}
        action={
          state.kind === "not_school" ? (
            <Link href="/portal/signup" className={buttonClasses("solid")}>
              {t("signup.cta")}
            </Link>
          ) : (
            <Button onClick={() => void load()}>{t("retry")}</Button>
          )
        }
      />
    );
  const me = state.me;
  if (me.org.status !== "approved")
    return (
      <Notice
        title={t(me.org.status === "pending" ? "pendingTitle" : "rejectedTitle", { name: me.org.name })}
        body={t(me.org.status === "pending" ? "pendingBody" : "rejectedBody")}
      />
    );
  const room = classId ? me.classes.find((c) => c.id === classId) : undefined;
  const item = (on: boolean) =>
    `flex min-h-11 items-center rounded-sm px-3.5 whitespace-nowrap ${on ? "bg-night-900 font-bold text-paper" : "text-ink hover:bg-paper-sunk"}`;

  return (
    <PortalContext.Provider value={{ me, reload: load }}>
      <div className="min-h-dvh bg-paper lg:grid lg:grid-cols-[264px_1fr]">
        <aside className="flex flex-col gap-4 border-b border-line bg-paper-raised px-4 py-4 lg:min-h-dvh lg:border-e lg:border-b-0 lg:py-6">
          <Link href="/" className="flex items-center gap-2 px-2">
            <MoonMark className="size-8" />
            <span className="font-display text-[22px] font-extrabold text-night-900">{brandName(locale)}</span>
            <span className="rounded-full bg-night-900 px-2 py-0.5 text-[11px] font-bold text-paper">{t("badge")}</span>
          </Link>
          <div className="flex items-center gap-2.5 rounded-md bg-paper-sunk p-3">
            {me.org.has_logo ? (
              // eslint-disable-next-line @next/next/no-img-element -- the school's own logo, private, through the API
              <img src="/api/portal/logo" alt="" className="size-10 rounded-sm bg-paper-raised object-contain" />
            ) : (
              <span className="size-10 shrink-0 rounded-sm border-[1.5px] border-dashed border-amber-700 bg-paper-raised" />
            )}
            <div className="flex min-w-0 flex-col">
              <strong className="truncate text-small">{me.org.name}</strong>
              <span className="truncate text-caption text-ink-muted">{me.name}</span>
            </div>
          </div>
          <nav aria-label={t("navLabel")} className="flex gap-1 overflow-x-auto lg:flex-col">
            <Link
              href="/portal"
              aria-current={active === "dashboard" ? "page" : undefined}
              className={item(active === "dashboard")}
            >
              {t("nav.dashboard")}
            </Link>
            {room && (
              <>
                <span className="hidden px-3.5 pt-3 text-caption font-bold text-ink-muted lg:block">{room.name}</span>
                {CLASS_SECTIONS.map((s) => (
                  <Link
                    key={s.id}
                    href={`/portal/classes/${room.id}${s.href}`}
                    aria-current={active === s.id ? "page" : undefined}
                    className={item(active === s.id)}
                  >
                    {t(`nav.${s.id}`)}
                  </Link>
                ))}
              </>
            )}
          </nav>
          <button
            type="button"
            onClick={async () => {
              await api("/api/auth/logout", { method: "POST" });
              router.replace("/");
            }}
            className="mt-auto hidden min-h-11 px-3.5 text-start text-small text-ink-muted hover:text-ink lg:block"
          >
            {t("logout")}
          </button>
        </aside>
        <main className="min-w-0 px-4 py-6 md:px-10 md:py-8">{children}</main>
      </div>
    </PortalContext.Provider>
  );
}

function Notice({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="mx-auto mt-16 flex max-w-md flex-col items-center gap-3 px-4 text-center">
      <MoonMark className="size-14" />
      <h1 className="text-h2 text-night-900">{title}</h1>
      <p className="text-body text-ink-muted">{body}</p>
      {action}
    </div>
  );
}
