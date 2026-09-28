"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { ArrowForward, Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { createApi, type Child } from "@/lib/create";
import { Chip, Frame, Lead } from "./Frame";

const AGES = [2, 3, 4, 5, 6, 7, 8, 9];

/** Step 1 (design Create1): who the hero is. A parent can also pick a child they added before. */
export function ChildStep({
  known,
  title,
  onPick,
  onAdded,
}: {
  known: Child[];
  title: string | null;
  onPick: (child: Child) => void;
  onAdded: (child: Child) => void;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [name, setName] = useState("");
  const [gender, setGender] = useState<"m" | "f" | null>(null);
  const [age, setAge] = useState<number | null>(null);
  const [likes, setLikes] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [hijab, setHijab] = useState(false);
  const [glasses, setGlasses] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const shown = name.trim() || (locale === "ar" ? "ليان" : "Layan");
  const g = gender ?? "f";

  function toggle(like: string) {
    setLikes((l) => (l.includes(like) ? l.filter((x) => x !== like) : l.length < 3 ? [...l, like] : l));
  }

  async function submit() {
    if (!name.trim() || !gender || !age) {
      setError(t("child.invalid"));
      return;
    }
    setBusy(true);
    setError(null);
    const r = await createApi.addChild({
      name: name.trim(),
      gender,
      age,
      interests: likes,
      note: note.trim() || undefined,
      hijab: gender === "f" && hijab,
      glasses,
    });
    setBusy(false);
    if (r.ok) onAdded(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <Frame
      title={t("newBook")}
      label={t("steps.child")}
      n={1}
      footer={
        <Button onClick={submit} loading={busy} size="lg" className="grow">
          {t("continue")} <ArrowForward />
        </Button>
      }
    >
      <Lead title={t("child.title")} body={t("child.body")} />

      {known.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-body font-semibold">{t("child.mine")}</span>
          <div className="flex flex-wrap gap-2">
            {known.map((c) => (
              <Chip key={c.id} on={false} onClick={() => onPick(c)}>
                {c.name}
              </Chip>
            ))}
          </div>
          <span className="pt-2 text-small text-ink-muted">{t("child.newChild")}</span>
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        <label htmlFor="kid-name" className="text-body font-semibold">
          {t("child.name")}
        </label>
        <input
          id="kid-name"
          value={name}
          maxLength={40}
          autoComplete="off"
          onChange={(e) => setName(e.target.value)}
          className="min-h-14 rounded-[14px] border-[1.5px] border-line bg-white px-4 text-body-l text-ink outline-none focus:border-night-900 focus:ring-4 focus:ring-night-100"
        />
        {title && (
          <span className="text-caption text-ink-muted">
            {t("child.namePreview")} <strong className="text-night-900">«{title.replace("{name}", shown)}»</strong>
          </span>
        )}
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-body font-semibold">{t("child.gender")}</legend>
        <div className="grid grid-cols-2 gap-3">
          {(["f", "m"] as const).map((value) => (
            <label
              key={value}
              className={`flex min-h-16 cursor-pointer items-center justify-center gap-2.5 rounded-2xl text-[17px] ${gender === value ? "border-2 border-night-900 bg-night-100 font-bold text-night-900" : "border-[1.5px] border-line bg-paper-raised"}`}
            >
              <input
                type="radio"
                name="gender"
                checked={gender === value}
                onChange={() => setGender(value)}
                className="size-5 accent-night-900"
              />
              {value === "f" ? t("child.girl") : t("child.boy")}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-body font-semibold">{t("child.age")}</legend>
        <div className="flex flex-wrap gap-2">
          {AGES.map((n) => (
            <Chip key={n} on={age === n} onClick={() => setAge(n)} round={false}>
              {n}
            </Chip>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-body font-semibold">
          {t("child.likes", { gender: g, name: shown })}{" "}
          <span className="font-normal text-ink-muted">{t("child.upTo3")}</span>
        </legend>
        <div className="flex flex-wrap gap-2">
          {(t.raw("child.likesList") as string[]).map((like) => (
            <Chip
              key={like}
              on={likes.includes(like)}
              onClick={() => toggle(like)}
              disabled={!likes.includes(like) && likes.length >= 3}
            >
              {like}
            </Chip>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-body font-semibold">{t("child.look")}</legend>
        <div className="flex flex-wrap gap-2">
          {gender === "f" && (
            <Chip on={hijab} onClick={() => setHijab((v) => !v)}>
              {t("child.hijab")}
            </Chip>
          )}
          <Chip on={glasses} onClick={() => setGlasses((v) => !v)}>
            {t("child.glasses", { gender: g })}
          </Chip>
        </div>
      </fieldset>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="kid-note" className="text-body font-semibold">
          {t("child.note", { gender: g })} <span className="font-normal text-ink-muted">{t("child.optional")}</span>
        </label>
        <input
          id="kid-note"
          value={note}
          maxLength={60}
          placeholder={t("child.notePlaceholder")}
          onChange={(e) => setNote(e.target.value)}
          className="min-h-14 rounded-[14px] border-[1.5px] border-line bg-white px-4 text-body outline-none placeholder:text-ink-faint focus:border-night-900 focus:ring-4 focus:ring-night-100"
        />
      </div>

      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
