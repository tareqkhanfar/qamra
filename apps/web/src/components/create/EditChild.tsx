"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRef, useState, type ReactNode } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { nameCases, twoWordName } from "@/lib/arabicName";
import { createApi, type Child } from "@/lib/create";
import { isArabicName, type Kind } from "@/lib/flows";
import { Chip } from "./Frame";

/** The ages the flow offers (the API accepts 2–10). */
export const AGES = [2, 3, 4, 5, 6, 7, 8, 9, 10];

export const inputClass =
  "min-h-14 rounded-[14px] border-[1.5px] border-line bg-white px-4 text-body-l text-ink outline-none focus:border-night-900 focus:ring-4 focus:ring-night-100";

/** The `<ar>` tag of a message: Arabic the book prints, quoted in an English sentence (kept right to left). */
export const arabic = (chunks: ReactNode) => (
  <bdi lang="ar" dir="rtl">
    {chunks}
  </bdi>
);

/** The hint under a question: why we ask it, in one plain sentence. */
export function Hint({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} className="text-caption text-ink-muted">
      {children}
    </p>
  );
}

/** The message key of a name hint: an activity book says where it prints the name. */
function nameHint(kind: Kind, line: string | null): string {
  if (kind === "story") return "child.nameHint";
  return `who.nameHint.${line === "journey" || line === "family" || line === "islamic" ? line : "workbook"}`;
}

/**
 * The name, gender and age, each with why we ask it for this product (§c.4): the new-child form and «تعديل
 * البيانات» share them. A name typed as one word that is usually two («أبوبكر», «عبدالله») gets a gentle
 * suggestion under the field («أبو بكر» is what the book's sentences inflect: «يا أبا بكر»); the parent decides.
 */
export function ChildFields({
  id,
  kind,
  productLine,
  name,
  gender,
  age,
  onName,
  onGender,
  onAge,
  preview,
  nameError,
}: {
  id: string;
  kind: Kind;
  productLine: string | null;
  name: string;
  gender: "m" | "f" | null;
  age: number | null;
  onName: (v: string) => void;
  onGender: (v: "m" | "f") => void;
  onAge: (v: number) => void;
  preview?: ReactNode;
  nameError?: string | null;
}) {
  const t = useTranslations("create");
  const activity = kind === "activity";
  const input = useRef<HTMLInputElement>(null);
  const split = twoWordName(name);
  return (
    <>
      <div className="flex flex-col gap-1.5">
        <label htmlFor={`${id}-name`} className="text-body font-semibold">
          {activity ? t("who.name") : t("child.name", { gender: gender ?? "other" })}
        </label>
        <Hint id={`${id}-name-hint`}>{t(nameHint(kind, productLine))}</Hint>
        <input
          ref={input}
          id={`${id}-name`}
          value={name}
          maxLength={40}
          autoComplete="off"
          aria-describedby={split ? `${id}-name-hint ${id}-name-split` : `${id}-name-hint`}
          aria-invalid={nameError ? true : undefined}
          onChange={(e) => onName(e.target.value)}
          className={inputClass}
        />
        {nameError && <span className="text-caption font-semibold text-danger">{nameError}</span>}
        {split && (
          <div className="flex flex-col items-start gap-2 rounded-sm border border-info/20 bg-info-bg px-3 py-2.5">
            <p id={`${id}-name-split`} className="text-caption text-info">
              {t.rich("child.twoWords", { suggestion: split, ar: arabic })}
            </p>
            <button
              type="button"
              onClick={() => {
                onName(split);
                input.current?.focus();
              }}
              className="min-h-11 rounded-full border-2 border-night-900 bg-paper-raised px-4 py-1.5 text-start font-display text-small font-bold text-night-900 hover:bg-night-100"
            >
              {t.rich("child.twoWordsUse", { suggestion: split, ar: arabic })}
            </button>
          </div>
        )}
        {preview}
      </div>

      <fieldset className="flex flex-col gap-2" aria-describedby={`${id}-gender-hint`}>
        <legend className="text-body font-semibold">{t("child.gender")}</legend>
        <Hint id={`${id}-gender-hint`}>
          {activity
            ? t.rich(productLine === "islamic" ? "who.genderHint.islamic" : "who.genderHint.other", { ar: arabic })
            : t("child.genderHint")}
        </Hint>
        <div className="grid grid-cols-2 gap-3">
          {(["f", "m"] as const).map((value) => (
            <label
              key={value}
              className={`flex min-h-16 cursor-pointer items-center justify-center gap-2.5 rounded-2xl text-[17px] ${gender === value ? "border-2 border-night-900 bg-night-100 font-bold text-night-900" : "border-[1.5px] border-line bg-paper-raised"}`}
            >
              <input
                type="radio"
                name={`${id}-gender`}
                checked={gender === value}
                onChange={() => onGender(value)}
                className="size-5 accent-night-900"
              />
              {value === "f" ? t("child.girl") : t("child.boy")}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2" aria-describedby={`${id}-age-hint`}>
        <legend className="text-body font-semibold">{t("child.age")}</legend>
        <Hint id={`${id}-age-hint`}>{activity ? t("who.ageHint") : t("child.ageHint")}</Hint>
        <div className="flex flex-wrap gap-2">
          {AGES.map((n) => (
            <Chip key={n} on={age === n} onClick={() => onAge(n)} round={false}>
              {n}
            </Chip>
          ))}
        </div>
      </fieldset>
    </>
  );
}

/**
 * «تعديل البيانات»: correct a known child's name, gender or age (`PATCH /api/create/children/{id}`). The drawn
 * character stays as it is, and the form says so.
 */
export function EditChild({
  child,
  kind,
  productLine,
  traces,
  onSaved,
  onCancel,
}: {
  child: Child;
  kind: Kind;
  productLine: string | null;
  traces: boolean;
  onSaved: (child: Child) => void;
  onCancel: () => void;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const [name, setName] = useState(child.name);
  const [gender, setGender] = useState<"m" | "f">(child.gender);
  const [age, setAge] = useState<number | null>(AGES.includes(child.age) ? child.age : null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const badName = traces && !!name.trim() && !isArabicName(name);

  async function save() {
    if (!name.trim() || !age) return setError(t("child.invalid"));
    if (badName) return setError(t("who.arabicInvalid"));
    setBusy(true);
    setError(null);
    const r = await createApi.updateChild(child.id, {
      name: name.trim(),
      gender,
      age,
      ...(gender === "m" ? { hijab: false } : {}),
    });
    setBusy(false);
    if (r.ok) onSaved(r.data);
    else setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
  }

  return (
    <section
      aria-labelledby={`edit-${child.id}-title`}
      className="flex flex-col gap-5 rounded-[20px] border-[1.5px] border-night-900 bg-paper-raised p-4"
    >
      <div className="flex flex-col gap-1">
        <h2 id={`edit-${child.id}-title`} className="text-[20px] leading-snug text-night-900">
          {t("who.edit.title", nameCases(child.name))}
        </h2>
        <Hint>{t("who.edit.note")}</Hint>
      </div>
      <ChildFields
        id={`edit-${child.id}`}
        kind={kind}
        productLine={productLine}
        name={name}
        gender={gender}
        age={age}
        onName={setName}
        onGender={setGender}
        onAge={setAge}
        nameError={badName ? t("who.arabicInvalid") : null}
      />
      {error && <Alert>{error}</Alert>}
      <div className="flex flex-wrap gap-2">
        <Button onClick={save} loading={busy} variant="solid" size="md">
          {t("who.edit.save")}
        </Button>
        <Button onClick={onCancel} variant="ghost" size="md" disabled={busy}>
          {t("who.edit.cancel")}
        </Button>
      </div>
    </section>
  );
}
