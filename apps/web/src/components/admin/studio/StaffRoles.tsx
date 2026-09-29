"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { api, errorText } from "@/lib/api";
import { when, type StaffList, type StaffMember } from "@/lib/studio";
import { inputClass } from "./parts";

type Notice = { ok: boolean; text: string } | null;

/**
 * Staff and their roles (Addendum 4 §3.6): roles come from the permissions map; admins add, change and remove
 * them, and every change is in the audit log. Only an owner hands out the owner role; nobody edits their own.
 */
export function StaffRoles() {
  const t = useTranslations("studio.staff");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [data, setData] = useState<StaffList | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string[]>>({});
  const [email, setEmail] = useState("");
  const [roles, setRoles] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);

  const load = useCallback(async () => {
    const r = await api<StaffList>("/api/admin/staff");
    if (!r.ok) return setNotice({ ok: false, text: errorText(r.error, locale, te("unknown")) });
    setData(r.data);
    setDrafts({});
  }, [locale, te]);

  useEffect(() => {
    void (async () => {
      await load();
    })();
  }, [load]);

  async function send(key: string, path: string, init: { method?: string; json?: unknown }, ask?: string) {
    if (ask && !window.confirm(ask)) return;
    setBusy(key);
    setNotice(null);
    const r = await api<unknown>(path, init);
    setBusy(null);
    if (!r.ok) return setNotice({ ok: false, text: errorText(r.error, locale, te("unknown")) });
    setNotice({ ok: true, text: t("saved") });
    if (key === "add") {
      setEmail("");
      setRoles([]);
    }
    await load();
  }

  const flip = (list: string[], role: string) =>
    list.includes(role) ? list.filter((r) => r !== role) : [...list, role];
  if (!data) {
    return notice ? (
      <Alert>{notice.text}</Alert>
    ) : (
      <div className="h-48 animate-pulse rounded-xl bg-paper-sunk" aria-busy="true" />
    );
  }
  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-1">
        <h1 className="text-h2 text-night-900">{t("title")}</h1>
        <p className="text-ink-muted">{t("lead")}</p>
      </header>
      {notice && <Alert tone={notice.ok ? "success" : "error"}>{notice.text}</Alert>}
      <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-xl border border-line bg-paper-raised">
        {data.staff.map((member) => (
          <StaffRow
            key={member.id}
            member={member}
            me={member.id === data.me}
            allRoles={data.roles.map((r) => r.role)}
            draft={drafts[member.id] ?? member.roles}
            onToggle={(role) => setDrafts((d) => ({ ...d, [member.id]: flip(d[member.id] ?? member.roles, role) }))}
            busy={busy}
            onSave={(list) =>
              void send(`save:${member.id}`, `/api/admin/staff/${member.id}/roles`, {
                method: "PUT",
                json: { roles: list },
              })
            }
            onRemove={() =>
              void send(
                `remove:${member.id}`,
                `/api/admin/staff/${member.id}`,
                { method: "DELETE" },
                t("confirmRemove", { name: member.full_name }),
              )
            }
            locale={locale}
          />
        ))}
      </ul>
      <section
        className="flex flex-col gap-3 rounded-xl border border-line bg-paper-raised p-4"
        aria-labelledby="add-staff"
      >
        <h2 id="add-staff" className="text-h3 text-night-900">
          {t("addTitle")}
        </h2>
        <p className="text-small text-ink-muted">{t("addLead")}</p>
        <label className="flex flex-col gap-1 text-small font-semibold">
          {t("email")}
          <input
            type="email"
            dir="ltr"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
          />
        </label>
        <RoleChecks
          all={data.roles.map((r) => r.role)}
          value={roles}
          onToggle={(role) => setRoles((l) => flip(l, role))}
        />
        <Button
          size="sm"
          className="self-start"
          disabled={!email.trim() || roles.length === 0}
          loading={busy === "add"}
          onClick={() => void send("add", "/api/admin/staff", { json: { email: email.trim(), roles } })}
        >
          {t("add")}
        </Button>
      </section>
      <section className="flex flex-col gap-2" aria-labelledby="roles-legend">
        <h2 id="roles-legend" className="text-h3 text-night-900">
          {t("legend")}
        </h2>
        <dl className="grid gap-2 md:grid-cols-2">
          {data.roles.map((r) => (
            <div key={r.role} className="rounded-md border border-line bg-paper-raised p-3">
              <dt className="font-semibold text-night-900">{t(`roles.${r.role}`)}</dt>
              <dd className="mt-1 flex flex-wrap gap-1" dir="ltr">
                {r.permissions.map((p) => (
                  <code key={p} className="rounded bg-paper-sunk px-1.5 text-caption">
                    {p === "*" ? t("everything") : p}
                  </code>
                ))}
              </dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}

function RoleChecks({
  all,
  value,
  onToggle,
  disabled,
}: {
  all: string[];
  value: string[];
  onToggle: (r: string) => void;
  disabled?: boolean;
}) {
  const t = useTranslations("studio.staff.roles");
  return (
    <div className="flex flex-wrap gap-2">
      {all.map((role) => (
        <label
          key={role}
          className={`flex min-h-10 items-center gap-2 rounded-full border px-3 text-small ${value.includes(role) ? "border-night-900 bg-night-100 font-semibold" : "border-line bg-paper"} ${disabled ? "opacity-60" : ""}`}
        >
          <input
            type="checkbox"
            checked={value.includes(role)}
            disabled={disabled}
            onChange={() => onToggle(role)}
            className="size-4 accent-night-900"
          />
          {t(role)}
        </label>
      ))}
    </div>
  );
}

function StaffRow({
  member,
  me,
  allRoles,
  draft,
  onToggle,
  busy,
  onSave,
  onRemove,
  locale,
}: {
  member: StaffMember;
  me: boolean;
  allRoles: string[];
  draft: string[];
  onToggle: (role: string) => void;
  busy: string | null;
  onSave: (roles: string[]) => void;
  onRemove: () => void;
  locale: string;
}) {
  const t = useTranslations("studio.staff");
  const changed = [...draft].sort().join() !== [...member.roles].sort().join();
  return (
    <li className="flex flex-col gap-2 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="min-w-0">
          <span className="font-semibold text-night-900">{member.full_name}</span>
          {me && <span className="ms-2 rounded-full bg-night-100 px-2 text-caption">{t("you")}</span>}
          <span className="block truncate text-small text-ink-muted" dir="ltr">
            {member.email}
          </span>
        </div>
        <span className="text-caption text-ink-muted">
          {member.mfa ? `✓ ${t("mfaOn")}` : `✗ ${t("mfaOff")}`} ·{" "}
          {t("lastLogin", { at: when(member.last_login_at, locale) })}
        </span>
      </div>
      <RoleChecks all={allRoles} value={draft} onToggle={onToggle} disabled={me} />
      {!me && (
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            disabled={!changed || draft.length === 0}
            loading={busy === `save:${member.id}`}
            onClick={() => onSave(draft)}
          >
            {t("save")}
          </Button>
          <Button size="sm" variant="ghost" loading={busy === `remove:${member.id}`} onClick={onRemove}>
            {t("remove")}
          </Button>
        </div>
      )}
    </li>
  );
}
