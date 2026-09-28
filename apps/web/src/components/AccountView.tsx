"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";
import { Scene } from "@/components/art/Scene";
import { ChangePassword } from "@/components/ChangePassword";
import { Alert } from "@/components/ui/Alert";
import { Button, buttonClasses } from "@/components/ui/Button";
import { brandName } from "@/config/brand";
import { Link, useRouter } from "@/i18n/navigation";
import { api, errorText, type User } from "@/lib/api";

type Child = { id: string; first_name: string; gender: "m" | "f"; birth_year: number };
type Book = {
  id: string;
  child_id: string;
  title: string | null;
  theme_slug: string;
  status: "draft" | "generating" | "preview" | "approved" | "ordered" | "printed" | "failed";
};

const STATUS_CHIP: Record<Book["status"], string> = {
  draft: "bg-paper-sunk text-ink",
  generating: "bg-night-100 text-night-900",
  preview: "bg-amber-100 text-amber-700",
  approved: "bg-success-bg text-success",
  ordered: "bg-paper-sunk text-ink",
  printed: "bg-success-bg text-success",
  failed: "bg-danger-bg text-danger",
};
const THEME_SCENE: Record<string, "night" | "garden" | "sea" | "space" | "grad"> = {
  "first-day": "garden",
  graduation: "grad",
  "new-sibling": "night",
};

function Avatar({ name, active }: { name: string; active: boolean }) {
  return (
    <span
      className={`flex size-[72px] items-center justify-center rounded-full border-[3px] font-display text-[28px] font-extrabold ${active ? "border-amber-500 bg-amber-100 text-night-900" : "border-transparent bg-night-100 text-night-700"}`}
      aria-hidden="true"
    >
      {name.trim().charAt(0)}
    </span>
  );
}

/** Parent account home (design: account-books — mobile). */
export function AccountView() {
  const t = useTranslations("account");
  const tn = useTranslations("nav");
  const te = useTranslations("errors");
  const ta = useTranslations("admin");
  const locale = useLocale();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [children, setChildren] = useState<Child[]>([]);
  const [books, setBooks] = useState<Book[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab] = useState<"books" | "orders">("books");
  const [error, setError] = useState<string | null>(null);
  const [leaving, setLeaving] = useState(false);
  const [hour] = useState(() => new Date().getHours());

  useEffect(() => {
    let alive = true;
    (async () => {
      const me = await api<User>("/api/auth/me");
      if (!alive) return;
      if (!me.ok) {
        if (me.status === 401) router.replace(`/login?next=${encodeURIComponent("/account")}`);
        else setError(errorText(me.error, locale, me.status === 0 ? te("network") : te("unknown")));
        return;
      }
      const [c, b] = await Promise.all([api<Child[]>("/api/children"), api<Book[]>("/api/books")]);
      if (!alive) return;
      setUser(me.data);
      if (c.ok) setChildren(c.data);
      if (b.ok) setBooks(b.data);
    })();
    return () => {
      alive = false;
    };
  }, [locale, router, te]);

  const active = selected ?? children[0]?.id ?? null;
  const activeChild = children.find((c) => c.id === active) ?? null;
  const shownBooks = useMemo(
    () => (activeChild ? books.filter((b) => b.child_id === activeChild.id) : books),
    [books, activeChild],
  );
  const generating = books.find((b) => b.status === "generating");

  async function logout() {
    setLeaving(true);
    await api("/api/auth/logout", { method: "POST", json: {} });
    router.replace("/");
    router.refresh();
  }

  if (error)
    return (
      <div className="mx-auto mt-10 max-w-md px-4">
        <Alert>{error}</Alert>
      </div>
    );
  if (!user)
    return (
      <div className="mx-auto mt-8 max-w-2xl animate-pulse space-y-4 px-4" aria-busy="true" aria-label={t("loading")}>
        <div className="h-10 w-1/2 rounded-sm bg-paper-sunk" />
        <div className="flex gap-3">
          <div className="size-[72px] rounded-full bg-paper-sunk" />
          <div className="size-[72px] rounded-full bg-paper-sunk" />
        </div>
        <div className="h-48 rounded-xl bg-paper-sunk" />
      </div>
    );

  const tabClass = (on: boolean) =>
    `min-h-12 border-b-[3px] px-3.5 text-[15px] ${on ? "border-amber-500 font-bold text-night-900" : "border-transparent text-ink-muted"}`;

  return (
    <div className="mx-auto flex max-w-2xl flex-col pb-28 md:pb-16">
      <header className="flex items-center justify-between px-4 pt-4 pb-2 md:pt-10">
        <div className="flex flex-col">
          <span className="text-small text-ink-muted">{hour < 12 ? t("greetingMorning") : t("greetingEvening")}</span>
          <h1 className="text-[26px] text-night-900 md:text-h1">{user.full_name}</h1>
        </div>
        <div className="flex items-center gap-1">
          {user.role === "admin" && (
            <Link href="/admin/settings" className={buttonClasses("solid", "sm")}>
              {ta("adminLink")}
            </Link>
          )}
          <Button variant="ghost" size="sm" onClick={logout} loading={leaving}>
            {tn("logout")}
          </Button>
        </div>
      </header>

      <section aria-label={t("children")} className="flex flex-col gap-2.5 pt-2 pb-4">
        <div className="flex items-center justify-between px-4">
          <h2 className="text-[18px] text-night-900">{t("children")}</h2>
        </div>
        <div className="flex gap-3.5 overflow-x-auto px-4">
          {children.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setSelected(c.id)}
              aria-pressed={c.id === active}
              className="flex flex-col items-center gap-1.5"
            >
              <Avatar name={c.first_name} active={c.id === active} />
              <span className={`text-small ${c.id === active ? "font-bold" : ""}`}>{c.first_name}</span>
            </button>
          ))}
          <Link href="/create" className="flex flex-col items-center gap-1.5">
            <span className="flex size-[72px] items-center justify-center rounded-full border-2 border-dashed border-amber-700 text-amber-700">
              <svg
                className="size-7"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="M12 5v14M5 12h14" />
              </svg>
            </span>
            <span className="text-small font-semibold text-amber-700">{t("newChild")}</span>
          </Link>
        </div>
      </section>

      <div role="tablist" className="flex gap-1 border-b border-line px-4">
        <button
          role="tab"
          type="button"
          aria-selected={tab === "books"}
          onClick={() => setTab("books")}
          className={tabClass(tab === "books")}
        >
          {activeChild
            ? t("booksOf", { name: activeChild.first_name, count: shownBooks.length })
            : t("allBooks", { count: books.length })}
        </button>
        <button
          role="tab"
          type="button"
          aria-selected={tab === "orders"}
          onClick={() => setTab("orders")}
          className={tabClass(tab === "orders")}
        >
          {t("orders")}
        </button>
      </div>

      <div className="flex flex-col gap-4 px-4 pt-4">
        {generating && (
          <div className="flex items-center gap-3 rounded-[18px] bg-night-900 p-3.5 text-paper">
            <span className="flex size-11 shrink-0 items-center justify-center rounded-sm bg-night-800 text-amber-500">
              ✦
            </span>
            <strong className="grow text-[15px]">{generating.title}</strong>
            <span className="text-caption text-amber-300">{t("status.generating")}</span>
          </div>
        )}

        {tab === "orders" ? (
          <p className="py-10 text-center text-body text-ink-muted">{t("ordersEmpty")}</p>
        ) : shownBooks.length ? (
          <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-3">
            {shownBooks.map((b) => (
              <div key={b.id} className="flex flex-col gap-2">
                <div className="flex justify-center rounded-[18px] bg-paper-sunk p-3.5">
                  <div className="w-full max-w-[120px] overflow-hidden rounded-s-[10px] rounded-e-[4px] border-s-[6px] border-night-950 shadow-[0_6px_16px_rgba(22,32,74,0.18)]">
                    <Scene theme={THEME_SCENE[b.theme_slug] ?? "night"} ratio={1} kidScale={0.62} outfit="#F2B33D" />
                  </div>
                </div>
                <strong className="text-[15px] leading-snug">{b.title ?? "—"}</strong>
                <span className={`self-start rounded-full px-2.5 py-1 text-xs font-bold ${STATUS_CHIP[b.status]}`}>
                  {t(`status.${b.status}`)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <section className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-line bg-paper-raised/60 px-6 py-10 text-center">
            <svg className="h-16 w-20" viewBox="0 0 80 64" fill="none" aria-hidden="true">
              <path
                d="M40 14 C30 8 16 8 6 12 V56 C16 52 30 52 40 58 C50 52 64 52 74 56 V12 C64 8 50 8 40 14 Z"
                fill="#F3EAD8"
                stroke="#16204A"
                strokeWidth="2.5"
                strokeLinejoin="round"
              />
              <path d="M40 14 V58" stroke="#16204A" strokeWidth="2.5" />
              <path
                d="M60 2 C60.6 5.2 61.8 6.4 65 7 C61.8 7.6 60.6 8.8 60 12 C59.4 8.8 58.2 7.6 55 7 C58.2 6.4 59.4 5.2 60 2 Z"
                fill="#F2B33D"
              />
            </svg>
            <h2 className="text-h3 text-night-900">{t("empty")}</h2>
            <p className="text-body text-ink-muted">{t("emptyHint")}</p>
            <Link href="/create" className={buttonClasses("primary", "md")}>
              {t("start")}
            </Link>
          </section>
        )}

        <dl className="mt-4 grid gap-4 rounded-xl border border-line bg-paper-raised p-5 sm:grid-cols-2">
          <div>
            <dt className="text-caption text-ink-muted">{t("email")}</dt>
            <dd dir="ltr" className="mt-1 font-semibold rtl:text-right">
              {user.email}
            </dd>
          </div>
          <div>
            <dt className="text-caption text-ink-muted">{t("role")}</dt>
            <dd className="mt-1 font-semibold">{t(`roles.${user.role}`, { brand: brandName(locale) })}</dd>
          </div>
        </dl>
        {user.has_password && <ChangePassword />}
      </div>

      <nav
        aria-label={tn("menu")}
        className="fixed inset-x-0 bottom-0 z-40 grid h-20 grid-cols-4 border-t border-line bg-paper-raised pb-3 md:hidden"
      >
        {[
          { href: "/", label: tn("home"), d: "M4 11l8-7 8 7v9h-5v-6H9v6H4z" },
          { href: "/account", label: tn("books"), d: "M4 5h7v14H4zM13 5h7v14h-7z", current: true },
          { href: "/create", label: tn("newBook"), d: "M12 5v14M5 12h14" },
          { href: "/account", label: tn("account"), d: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c0-4 4-6 8-6s8 2 8 6" },
        ].map((n) => (
          <Link
            key={n.label}
            href={n.href}
            aria-current={n.current ? "page" : undefined}
            className={`flex flex-col items-center justify-center gap-1 text-xs ${n.current ? "font-bold text-night-900" : "text-ink-muted"}`}
          >
            <svg
              className="size-6"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d={n.d} />
            </svg>
            {n.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
