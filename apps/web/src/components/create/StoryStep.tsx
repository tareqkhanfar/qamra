"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Scene, fromArt } from "@/components/art/Scene";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { errorText } from "@/lib/api";
import type { ThemeCard } from "@/lib/catalog";
import { createApi, missingEndpoint, type Book, type Character, type Child, type Line } from "@/lib/create";
import { briefBody, briefReady, CUSTOM_THEME, customExtra, useCustomBrief } from "@/lib/customStory";
import { money, type Catalog } from "@/lib/store";
import { fillTitle } from "@/lib/themeTitle";
import { CompanionSummary } from "./companion/CompanionSummary";
import { CustomStoryForm } from "./CustomStoryForm";
import { Check, Chip, Frame, Lead } from "./Frame";

type Language = "ar" | "en";
const MAX_LIKES = 3;

/**
 * Step 7 (design Create6): the story, then an optional dedication. A story chosen on its page shows as one card
 * with «تغيير»; otherwise the list, stories for the child's age first. Magic also asks what the child loves and
 * one special thing (order-flows §c.6: they colour one or two pages, and only Magic's writer reads them), and on
 * the English site the book's language. Classic stays Arabic: its تشكيل is Arabic only.
 */
export function StoryStep({
  child,
  character,
  line,
  themes,
  catalog,
  initial,
  title,
  back,
  onStarted,
  companion = null,
  onCompanion,
}: {
  child: Child;
  character: Character;
  line: Line;
  themes: ThemeCard[];
  catalog: Catalog | null;
  initial: string | null;
  title?: string; // the frame title; the wizard's FlowFrameContext wins when present
  back: () => void;
  onStarted: (book: Book) => void;
  companion?: string | null; // «ارسم صاحبك»: the chosen companion's id (none: the theme's own)
  onCompanion?: () => void; // back to the companion step, to add or change it
}) {
  const t = useTranslations("create");
  const tcs = useTranslations("customStory");
  const te = useTranslations("errors");
  const locale = useLocale();
  const who = { name: child.name, gender: child.gender };
  const magic = line === "magic";
  const fits = (th: ThemeCard) => th.age_min <= child.age && child.age <= th.age_max;
  const list = themes.filter((th) => th.status === "available").sort((a, b) => Number(fits(b)) - Number(fits(a)));
  // «حكاية خاصة» (Magic): a story of their own instead of a ready theme, when the catalog sells it
  const extra = magic ? customExtra(catalog) : null;
  const known = (slug: string | null) =>
    (slug === CUSTOM_THEME && extra !== null) || (!!slug && list.some((th) => th.slug === slug));
  const [theme, setTheme] = useState<string | null>(known(initial) ? initial : (list[0]?.slug ?? null));
  // a story chosen on its page (or earlier in this flow) is one card with «تغيير», not the whole list again
  const [browsing, setBrowsing] = useState(!known(initial));
  const custom = theme === CUSTOM_THEME;
  const [brief, setBrief] = useCustomBrief(child.id);
  const [bad, setBad] = useState<string[]>([]);
  const [dedication, setDedication] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const page = catalog?.addons.find((a) => a.slug === "dedication-page");

  // Magic: the likes (chips) and the note, prefilled from the child; a custom story asks its own questions
  const choices = t.raw("story.likesList") as string[];
  const [before] = useState(() => {
    const saved = child.interests ?? []; // the chosen likes, then the free note, as the API keeps them
    return {
      likes: saved.filter((x) => choices.includes(x)).slice(0, MAX_LIKES),
      note: saved.filter((x) => !choices.includes(x)).at(-1) ?? "",
    };
  });
  const [likes, setLikes] = useState<string[]>(before.likes);
  const [note, setNote] = useState(before.note);
  const asksLikes = magic && !custom;
  const changed =
    note.trim() !== before.note || likes.length !== before.likes.length || likes.some((x) => !before.likes.includes(x));
  // the book's language: Magic follows the site (a choice on the English site), Classic is always Arabic
  const [language, setLanguage] = useState<Language>(magic && locale === "en" ? "en" : "ar");
  const asksLanguage = magic && locale === "en";

  function toggle(like: string) {
    setLikes((l) => (l.includes(like) ? l.filter((x) => x !== like) : l.length < MAX_LIKES ? [...l, like] : l));
  }

  async function start() {
    if (!theme) return;
    setBusy(true);
    setError(null);
    if (asksLikes && changed) {
      const saved = await createApi.updateChild(child.id, { interests: likes, note: note.trim() });
      // an API without `PATCH /children/{id}` yet (§d chunk 8): the story is still written, without the likes
      if (!saved.ok && !missingEndpoint(saved)) {
        setBusy(false);
        setError(errorText(saved.error, locale, saved.status === 0 ? te("network") : te("unknown")));
        return;
      }
    }
    const r = await createApi.startBook({
      child_id: child.id,
      character_id: character.id,
      theme,
      line,
      language: magic ? language : "ar",
      dedication: dedication.trim() || undefined,
      companion_id: companion ?? undefined,
      custom: custom ? briefBody(brief) : undefined,
    });
    setBusy(false);
    setBad([]);
    if (r.ok) onStarted(r.data);
    else {
      setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));
      setBad(((r.error?.details as { fields?: string[] } | undefined)?.fields ?? []).map(String));
    }
  }

  const customCard = extra !== null && (browsing || custom) && (
    <button
      type="button"
      role="radio"
      aria-checked={custom}
      onClick={() => setTheme(CUSTOM_THEME)}
      className={`flex items-center gap-3 rounded-[20px] bg-night-900 p-2.5 text-start text-paper ${custom ? "ring-[3px] ring-amber-500" : ""}`}
    >
      <span
        aria-hidden="true"
        className="flex size-[104px] shrink-0 items-center justify-center rounded-2xl bg-night-800 text-[44px] text-amber-300"
      >
        ✦
      </span>
      <div className="flex grow flex-col gap-1">
        <span className="self-start rounded-full bg-amber-500 px-2 py-0.5 text-[11px] font-bold text-night-950">
          {extra > 0 ? `+${money(extra, catalog?.currency ?? "ILS", locale)}` : tcs("badge")}
        </span>
        <h2 className="text-[18px] leading-snug text-paper">{tcs("title")}</h2>
        <p className="text-caption text-night-100">{tcs("tagline", { name: child.name })}</p>
      </div>
      <Check on={custom} />
    </button>
  );

  return (
    <Frame
      title={title ?? t("bookOf", { name: child.name })}
      label={t("steps.story")}
      back={back}
      footer={
        <Button
          onClick={start}
          loading={busy}
          size="lg"
          className="grow"
          disabled={!theme || (custom && !briefReady(brief))}
        >
          {t("story.cta")}
        </Button>
      }
    >
      <Lead
        title={t(browsing ? "story.title" : "story.chosenTitle", who)}
        body={`${browsing ? t("story.body", who) : ""} ${t("story.next")}`.trim()}
      />
      <div className="flex flex-col gap-3" role="radiogroup" aria-label={t("steps.story")}>
        {customCard}
        {custom && <CustomStoryForm child={child} value={brief} onChange={setBrief} bad={bad} />}
        {list
          .filter((th) => browsing || th.slug === theme)
          .map((th) => {
            const on = theme === th.slug;
            return (
              <button
                key={th.slug}
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => setTheme(th.slug)}
                className={`flex items-center gap-3 rounded-[20px] bg-paper-raised p-2.5 text-start ${on ? "border-[3px] border-amber-500" : "border-[1.5px] border-line"}`}
              >
                <div className="w-[104px] shrink-0 overflow-hidden rounded-2xl">
                  <Scene
                    {...fromArt({ ...th.art, hijab: child.hijab })}
                    ratio={1}
                    kidScale={th.art.kid_scale ?? 0.72}
                  />
                </div>
                <div className="flex grow flex-col gap-1">
                  {fits(th) && (
                    <span className="self-start rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-700">
                      {t("story.suggested", { name: child.name })}
                    </span>
                  )}
                  <h2 className="text-[18px] leading-snug text-night-900">
                    {fillTitle(th.title, child.name, child.gender)}
                  </h2>
                  <p className="text-caption text-ink-muted">
                    {th.tagline} · {t("story.pages", { pages: th.pages })}
                  </p>
                </div>
                <Check on={on} />
              </button>
            );
          })}
      </div>
      {!browsing && (
        <button
          type="button"
          onClick={() => setBrowsing(true)}
          className="-mt-3 min-h-11 self-start font-semibold text-night-900 underline underline-offset-4"
        >
          {t("story.change")}
        </button>
      )}
      {onCompanion && (
        <CompanionSummary child={child} line={line} catalog={catalog} companionId={companion} onChange={onCompanion} />
      )}

      {asksLikes && (
        <section aria-labelledby="likes" className="flex flex-col gap-4 rounded-3xl border border-line p-4">
          <fieldset className="flex flex-col gap-2">
            <legend id="likes" className="mb-1 text-body font-semibold">
              {t("story.likes", who)} <span className="font-normal text-ink-muted">{t("story.upTo3")}</span>
            </legend>
            <p className="text-small text-ink-muted">{t("story.likesHint")}</p>
            <div className="flex flex-wrap gap-2">
              {choices.map((like) => (
                <Chip
                  key={like}
                  on={likes.includes(like)}
                  onClick={() => toggle(like)}
                  disabled={!likes.includes(like) && likes.length >= MAX_LIKES}
                >
                  {like}
                </Chip>
              ))}
            </div>
          </fieldset>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="kid-note" className="text-body font-semibold">
              {t("story.note", who)} <span className="font-normal text-ink-muted">{t("story.optional")}</span>
            </label>
            <input
              id="kid-note"
              value={note}
              maxLength={60}
              placeholder={t("story.notePlaceholder", who)}
              onChange={(e) => setNote(e.target.value)}
              className="min-h-14 rounded-[14px] border-[1.5px] border-line bg-white px-4 text-body outline-none placeholder:text-ink-faint focus:border-night-900 focus:ring-4 focus:ring-night-100"
            />
          </div>
        </section>
      )}

      {asksLanguage ? (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-body font-semibold">{t("story.language")}</legend>
          <div className="flex flex-wrap gap-2">
            {(["ar", "en"] as const).map((l) => (
              <Chip key={l} on={language === l} onClick={() => setLanguage(l)}>
                <span lang={l}>{t(`story.languages.${l}`)}</span>
              </Chip>
            ))}
          </div>
          <span className="text-caption text-ink-muted">{t(`story.languageHint.${language}`)}</span>
        </fieldset>
      ) : (
        !magic && locale === "en" && <p className="text-small text-ink-muted">{t("story.classicArabic")}</p>
      )}

      <div className="flex flex-col gap-1.5">
        <label htmlFor="dedication" className="flex flex-wrap items-baseline justify-between gap-2">
          <span className="text-body font-semibold">
            {t("story.dedication")} <span className="font-normal text-ink-muted">{t("story.optional")}</span>
          </span>
          <span className="text-caption text-ink-muted">
            {magic
              ? t("story.dedicationFree")
              : page?.price
                ? t("story.dedicationPaid", { amount: money(page.price, catalog?.currency ?? "ILS", locale) })
                : null}
          </span>
        </label>
        <textarea
          id="dedication"
          rows={2}
          maxLength={120}
          value={dedication}
          placeholder={t("story.dedicationPlaceholder", { gender: child.gender })}
          onChange={(e) => setDedication(e.target.value)}
          className="rounded-[14px] border-[1.5px] border-line bg-white px-4 py-3 text-body outline-none placeholder:text-ink-faint focus:border-night-900 focus:ring-4 focus:ring-night-100"
        />
      </div>
      {error && <Alert>{error}</Alert>}
    </Frame>
  );
}
