"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { ArrowForward, Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import { accusativeName } from "@/lib/arabicName";
import { createApi, missingEndpoint, type Character, type Child, type ChildPatch } from "@/lib/create";
import { isArabicName, isLatinName, type Kind } from "@/lib/flows";
import { ChildFields, EditChild, Hint, inputClass } from "./EditChild";
import { Chip, Frame, Lead } from "./Frame";
import { KnownChild, type Look } from "./KnownChild";

/**
 * Step 1 (design Create1): who the book is for. It asks only what this product prints or checks, and says why
 * under each question (docs/plans/order-flows.md §c.4): a story asks the hero's name, gender and age; an activity
 * book asks the name as printed, the gender for its grammar, the age for the level check, and the name in
 * English letters when it prints one. The look is asked only when a new character will be drawn. A child added
 * before is a confirmation card that can be corrected.
 */
export function ChildStep({
  kind,
  productLine,
  known,
  initial,
  preview,
  asksNameEn,
  traces,
  ready,
  nameEnOf,
  onSelect,
  onEdited,
  onDone,
}: {
  kind: Kind;
  productLine: string | null;
  known: Child[];
  /** The child chosen before (back from a later step), shown selected. */
  initial: string | null;
  /** The story's title or the book's cover with this name, for the preview under the name; null: none. */
  preview: (name: string, gender: "m" | "f" | null) => string | null;
  asksNameEn: boolean;
  /** The book has the child trace their Arabic name, so it must be in Arabic letters. */
  traces: boolean;
  /** The character this book would use for a child (null: a new one is drawn). */
  ready: (child: Child) => Character | null;
  /** The English name saved for a child (or kept for this visit). */
  nameEnOf: (child: Child) => string;
  /** The chosen known child changed (the step count follows it). */
  onSelect: (child: Child | null) => void;
  onEdited: (child: Child) => void;
  /** The child is confirmed or added: the flow goes on (or returns why it could not). */
  onDone: (child: Child, extra: { nameEn?: string }) => Promise<string | null>;
}) {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const activity = kind === "activity";
  const [selectedId, setSelectedId] = useState<string | null>(
    initial && known.some((c) => c.id === initial) ? initial : null,
  );
  const selected = known.find((c) => c.id === selectedId) ?? null;
  const [editing, setEditing] = useState(false);
  // the known child's English name and look, as the card shows them
  const [knownEn, setKnownEn] = useState(selected ? nameEnOf(selected) : "");
  const [look, setLook] = useState<Look>({ hijab: !!selected?.hijab, glasses: !!selected?.glasses });
  // a new child
  const [name, setName] = useState("");
  const [nameEn, setNameEn] = useState("");
  const [gender, setGender] = useState<"m" | "f" | null>(null);
  const [age, setAge] = useState<number | null>(null);
  const [hijab, setHijab] = useState(false);
  const [glasses, setGlasses] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => onSelect(selected), [onSelect, selected]);

  /** A name being corrected: the error said about the previous one no longer holds. */
  function edited<T>(set: (v: T) => void): (v: T) => void {
    return (v) => {
      set(v);
      setError(null);
    };
  }

  function pick(c: Child | null) {
    setSelectedId(c?.id ?? null);
    setEditing(false);
    setError(null);
    setShowErrors(false);
    setKnownEn(c ? nameEnOf(c) : "");
    setLook({ hijab: !!c?.hijab, glasses: !!c?.glasses });
  }

  const shown = name.trim() || (locale === "ar" ? "ليان" : "Layan");
  const g = gender ?? "f";
  const sample = preview(shown, gender ?? (name.trim() ? null : "f"));
  const badName = traces && !!name.trim() && !isArabicName(name);
  const badEn = asksNameEn && showErrors && !isLatinName(nameEn);

  /** Save what the card changed (the English name; the look before a drawing), then go on. */
  async function confirm(c: Child) {
    setShowErrors(true);
    if (traces && !isArabicName(c.name)) return setError(t("who.arabicInvalid"));
    if (asksNameEn && !isLatinName(knownEn)) return setError(t("who.nameEnInvalid"));
    const patch: ChildPatch = {};
    if (asksNameEn && knownEn.trim() !== (c.name_latin ?? "")) patch.name_latin = knownEn.trim();
    if (!ready(c) && (look.hijab !== c.hijab || look.glasses !== c.glasses)) {
      patch.hijab = c.gender === "f" && look.hijab;
      patch.glasses = look.glasses;
    }
    setBusy(true);
    setError(null);
    let child = c;
    if (Object.keys(patch).length) {
      const r = await createApi.updateChild(c.id, patch);
      if (r.ok) {
        child = r.data;
        onEdited(r.data);
      } else if (!missingEndpoint(r)) {
        setBusy(false);
        return setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
      }
      // FALLBACK until `PATCH /children/{id}` is deployed (§d chunk 8): the English name goes with the cart line
    }
    const failed = await onDone(child, { nameEn: asksNameEn ? knownEn.trim() : undefined });
    setBusy(false);
    if (failed) setError(failed);
  }

  async function add() {
    setShowErrors(true);
    if (!name.trim() || !gender || !age) return setError(t("child.invalid"));
    if (badName) return setError(t("who.arabicInvalid"));
    if (asksNameEn && !isLatinName(nameEn)) return setError(t("who.nameEnInvalid"));
    setBusy(true);
    setError(null);
    const r = await createApi.addChild({
      name: name.trim(),
      gender,
      age,
      interests: [], // Magic asks what the child likes on its story step
      hijab: gender === "f" && hijab,
      glasses,
    });
    if (!r.ok) {
      setBusy(false);
      return setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
    }
    let child = r.data;
    onEdited(child);
    setSelectedId(child.id); // a retry goes on with this child, never adds it twice
    setKnownEn(nameEn.trim());
    setLook({ hijab: child.hijab, glasses: child.glasses });
    if (asksNameEn) {
      const saved = await createApi.updateChild(child.id, { name_latin: nameEn.trim() });
      if (saved.ok) {
        child = saved.data;
        onEdited(child);
      } // else (an older API) the English name goes with the cart line
    }
    const failed = await onDone(child, { nameEn: asksNameEn ? nameEn.trim() : undefined });
    setBusy(false);
    if (failed) setError(failed);
  }

  return (
    <Frame
      title={t("newBook")}
      label={activity ? t("steps.who") : t("steps.child")}
      footer={
        <Button
          onClick={() => (selected ? confirm(selected) : add())}
          loading={busy}
          disabled={editing}
          size="lg"
          className="grow"
        >
          {selected ? t("who.known.confirm", { name: selected.name }) : t("continue")} <ArrowForward />
        </Button>
      }
    >
      <Lead title={activity ? t("who.title") : t("child.title")} body={activity ? t("who.body") : t("child.body")} />

      {known.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-body font-semibold">{t("child.mine")}</span>
          <div className="flex flex-wrap gap-2">
            {known.map((c) => (
              <Chip key={c.id} on={c.id === selectedId} onClick={() => pick(c)}>
                {c.name}
              </Chip>
            ))}
            <Chip on={!selected} onClick={() => pick(null)}>
              + {t("child.newChild")}
            </Chip>
          </div>
        </div>
      )}

      {selected && editing && (
        <EditChild
          child={selected}
          kind={kind}
          productLine={productLine}
          traces={traces}
          onCancel={() => setEditing(false)}
          onSaved={(c) => {
            onEdited(c);
            setEditing(false);
            setError(null);
          }}
        />
      )}

      {selected && !editing && (
        <KnownChild
          child={selected}
          ready={ready(selected)}
          asksNameEn={asksNameEn}
          traces={traces}
          nameEn={knownEn}
          onNameEn={edited(setKnownEn)}
          look={look}
          onLook={setLook}
          onEdit={() => {
            setEditing(true);
            setError(null);
          }}
          showErrors={showErrors}
        />
      )}

      {!selected && (
        <>
          <ChildFields
            id="kid"
            kind={kind}
            productLine={productLine}
            name={name}
            gender={gender}
            age={age}
            onName={edited(setName)}
            onGender={setGender}
            onAge={setAge}
            nameError={badName ? t("who.arabicInvalid") : null}
            preview={
              sample && (
                <span className="text-caption text-ink-muted">
                  {activity ? t("who.coverPreview") : t("child.namePreview")}{" "}
                  <strong className="text-night-900">«{sample}»</strong>
                </span>
              )
            }
          />

          {asksNameEn && (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="kid-name-en" className="text-body font-semibold">
                {t("who.nameEn")}
              </label>
              <Hint id="kid-name-en-hint">{t("who.nameEnHint")}</Hint>
              <input
                id="kid-name-en"
                dir="auto"
                lang="en"
                value={nameEn}
                maxLength={40}
                autoComplete="off"
                autoCapitalize="words"
                spellCheck={false}
                placeholder={t("who.nameEnPlaceholder")}
                aria-describedby="kid-name-en-hint"
                aria-invalid={badEn ? true : undefined}
                onChange={(e) => edited(setNameEn)(e.target.value)}
                className={`${inputClass} text-start placeholder:text-ink-faint`}
              />
              {badEn && <span className="text-caption font-semibold text-danger">{t("who.nameEnInvalid")}</span>}
            </div>
          )}

          <fieldset className="flex flex-col gap-2" aria-describedby="kid-look-hint">
            <legend className="text-body font-semibold">
              {t("child.drawAs", { name: shown, nameAcc: accusativeName(shown) })}
            </legend>
            <Hint id="kid-look-hint">{t("child.lookHint")}</Hint>
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
        </>
      )}

      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
