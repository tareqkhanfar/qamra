"use client";

import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { AddOnsStep } from "@/components/order/AddOnsStep";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { emptyFamily, familyPayload, type Family, type Relation } from "@/components/workbook/FamilyDetails";
import { Link, useRouter } from "@/i18n/navigation";
import { api, errorText, type User } from "@/lib/api";
import { nameCases } from "@/lib/arabicName";
import type { ThemeCard } from "@/lib/catalog";
import { classicStyles, classicVariant, type ClassicVariant } from "@/lib/classic";
import { companionAddOn } from "@/lib/companion";
import { lastApproved } from "@/lib/drawings";
import {
  createApi,
  missingEndpoint,
  STEPS,
  type Book,
  type Character,
  type Child,
  type FamilyPayload,
  type Line,
  type Needs,
  type Step,
} from "@/lib/create";
import {
  agesFor,
  asksNameEn,
  canShow,
  formatPlan,
  isActivityLine,
  isArabicName,
  parsePlan,
  planFor,
  progress,
  resumeAt,
  stepsFor,
  tracesName,
  type FlowState,
  type PlanToken,
} from "@/lib/flows";
import { cartApi, type Catalog, type CatalogProduct, type CatalogVariant } from "@/lib/store";
import { fillTitle } from "@/lib/themeTitle";
import { FamilyStep } from "./activity/FamilyStep";
import { SummaryStep } from "./activity/SummaryStep";
import { CharacterStep } from "./CharacterStep";
import { ChildStep } from "./ChildStep";
import { ConsentStep } from "./ConsentStep";
import { FormatStep } from "./FormatStep";
import { FlowFrameContext } from "./Frame";
import { LineStep } from "./LineStep";
import { PhotoStep } from "./PhotoStep";
import { ReviewStep } from "./ReviewStep";
import { StoryStep } from "./StoryStep";
import { StyleStep } from "./StyleStep";
import { WritingStep } from "./WritingStep";
import { CompanionStep } from "./companion/CompanionStep";

type Query = Partial<
  Record<
    | "step"
    | "child"
    | "character"
    | "book"
    | "line"
    | "theme"
    | "style"
    | "product"
    | "companion"
    | "cstep"
    | "item"
    | "plan",
    string | null
  >
>;
/** What was fetched for an id in the URL (null: not found or not this parent's). */
type Loaded<T> = { id: string; value: T | null };
/** A variant of the catalog with its product. */
type Found = { product: CatalogProduct; variant: CatalogVariant };

function findVariant(catalog: Catalog | null, sku: string | null): Found | null {
  if (!catalog || !sku) return null;
  for (const product of catalog.products) {
    const variant = product.variants.find((v) => v.sku === sku);
    if (variant) return { product, variant };
  }
  return null;
}

/** The styles an activity book can reuse a character in (never the black-and-white `coloring`). */
function activityStyles(catalog: Catalog | null, line: string): string[] {
  const own = (catalog?.styles ?? []).filter((s) => s.lines.includes(line) && s.slug !== "coloring").map((s) => s.slug);
  // «قلبي يعرف الله» is in no style's `lines` until the API's migration (§d chunk 8): the owner's rule applies
  return own.length ? own : ["3d", "watercolor", "cartoon"];
}

/**
 * FALLBACK until `GET /api/shop/workbooks/needs` is deployed (§d chunk 8): the same rules, from the catalog
 * and the child (lib/flows.ts mirrors the server's). The server's answer always wins when it comes.
 */
function localNeeds(found: Found, catalog: Catalog | null, child: Child | null): Needs {
  const line = found.product.line as string;
  const options = found.variant.options;
  const styles = activityStyles(catalog, line);
  const reuse = child ? lastApproved(child.characters, (c) => styles.includes(c.style)) : null;
  return {
    line,
    product: found.product.slug,
    ages: agesFor(line, options),
    asks: { name_en: asksNameEn(line, options), family: line === "family" },
    character: { reuse_id: reuse?.id ?? null, draw_style: styles.includes("3d") ? "3d" : styles[0]!, styles },
    child: child
      ? { name_traceable: !tracesName(line) || isArabicName(child.name), name_latin: child.name_latin ?? null }
      : null,
  };
}

/** The family the cart line kept (the API's `family` on the line, §d chunk 8) as the step's form. */
function toFamily(given: FamilyPayload): Family {
  return {
    name: given.name ?? "",
    city: given.city ?? "",
    members: (given.members ?? []).map((m) => ({
      relation: m.relation as Relation,
      name: m.name ?? "",
      adult: m.adult ?? true,
      scarf: !!m.scarf,
    })),
  };
}

const EMPTY_FAMILY: FamilyPayload = { name: "", city: "", members: [] };

/** The server's "needs" answer is for a product, a child and the characters it has approved (and when). */
function needsKeyOf(sku: string | null, child: Child | null): string {
  const approved = (child?.characters ?? []).filter((c) => c.approved).map((c) => `${c.id}@${c.approved_at ?? ""}`);
  return `${sku}|${child?.id ?? ""}|${approved.join(",")}`;
}

/**
 * The parent create flow, one flow per product (docs/plans/order-flows.md §c): lib/flows.ts decides the steps
 * for this product and child, and the real «الخطوة n من N». Stories: the child, the type, the drawing, the story,
 * the preview, the format and the add-ons (design Create1–Create9, then the cart). Activity books
 * (`?product=<sku>[&item=<cart line>]`): the child, a drawing only when no character can be reused or the parent
 * asks for a new one in another style (consent, photo, the style step, the character: owner's decision of
 * 2026-10-09), the family for «مغامراتي مع عائلتي», and the review of what will print.
 */
export function CreateWizard() {
  const t = useTranslations("create");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const params = useSearchParams();
  const q = {
    step: params.get("step"),
    child: params.get("child"),
    character: params.get("character"),
    book: params.get("book"),
    line: (["classic", "magic"].includes(params.get("line") ?? "") ? params.get("line") : null) as Line | null,
    theme: params.get("theme"),
    style: params.get("style"),
    product: params.get("product"), // a variant SKU: an activity book's flow (a story's line comes from `line`)
    companion: params.get("companion"), // the drawn companion for this book, and the companion sub-step
    cstep: params.get("cstep"),
    item: params.get("item"), // «أكملوا بيانات الطفل»: the cart line added in one tap that this flow fills
    plan: params.get("plan"), // the optional steps this flow pinned (lib/flows.ts), so the count holds
  };
  const [children, setChildren] = useState<Child[] | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [catalogDone, setCatalogDone] = useState(false);
  const [themes, setThemes] = useState<ThemeCard[]>([]);
  const [character, setCharacter] = useState<Loaded<Character> | null>(null);
  const [book, setBook] = useState<Loaded<Book> | null>(null);
  // the server's answer for this activity book and child (null: none yet or no endpoint: the local rules)
  const [served, setServed] = useState<{ key: string; value: Needs | null } | null>(null);
  // the child picked on the child step before it is confirmed: the step count follows it
  const [picked, setPicked] = useState<Child | null>(null);
  // activity books: the parent asked for a new character in another style for the picked child (the who card)
  const [redraw, setRedraw] = useState(false);
  // FALLBACK until `PATCH /children/{id}` is deployed: the English name kept for this visit, sent with the line
  const [pendingEn, setPendingEn] = useState<Record<string, string>>({});
  // «مغامراتي مع عائلتي»: the family step's form (`known`: the line's own family could be read)
  const [family, setFamily] = useState<{ key: string; value: Family; known: boolean } | null>(null);
  // a failed load or a failed add: the error with a way to try again and a way back to the cart
  const [failure, setFailure] = useState<{ message: string; retry: () => void } | null>(null);

  const go = useCallback(
    (patch: Query) => {
      const next = new URLSearchParams(params.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (value === null || value === undefined) next.delete(key);
        else next.set(key, value);
      }
      router.push(`/create?${next.toString()}`);
      window.scrollTo({ top: 0 });
    },
    [params, router],
  );

  useEffect(() => {
    let alive = true;
    (async () => {
      const me = await api<User>("/api/auth/me");
      if (!alive) return;
      if (!me.ok) {
        if (me.status === 401) {
          const here = `/create${window.location.search}`;
          router.replace(`/login?next=${encodeURIComponent(here)}`);
        } else {
          const message = errorText(me.error, locale, me.status === 0 ? te("network") : te("unknown"));
          setFailure({ message, retry: () => window.location.reload() });
        }
        return;
      }
      const [kids, store, worlds] = await Promise.all([
        createApi.children(),
        api<Catalog>("/api/store/catalog"),
        api<ThemeCard[]>(`/api/themes?lang=${locale}`),
      ]);
      if (!alive) return;
      if (store.ok) setCatalog(store.data);
      setCatalogDone(true);
      if (worlds.ok) setThemes(worlds.data);
      if (kids.ok) setChildren(kids.data);
      else {
        const message = errorText(kids.error, locale, kids.status === 0 ? te("network") : te("unknown"));
        setFailure({ message, retry: () => window.location.reload() });
      }
    })();
    return () => {
      alive = false;
    };
  }, [locale, router, te]);

  useEffect(() => {
    if (!q.character) return;
    let alive = true;
    (async () => {
      const id = q.character as string;
      const r = await createApi.character(id);
      // a drawing the cleanup removed (never approved, 30 days on) is as good as gone: the flow starts it again
      if (alive) setCharacter({ id, value: r.ok && r.data.status !== "discarded" ? r.data : null });
    })();
    return () => {
      alive = false;
    };
  }, [q.character]);

  useEffect(() => {
    if (!q.book) return;
    let alive = true;
    (async () => {
      const id = q.book as string;
      const r = await createApi.book(id);
      if (alive) setBook({ id, value: r.ok ? r.data : null });
    })();
    return () => {
      alive = false;
    };
  }, [q.book]);

  const child = children?.find((c) => c.id === q.child);
  const found = findVariant(catalog, q.product);
  const activity = !!found && isActivityLine(found.product.line);
  const needsKey = needsKeyOf(q.product, child ?? null);

  useEffect(() => {
    if (!activity || !q.product) return;
    let alive = true;
    (async () => {
      const r = await createApi.needs(q.product as string, child?.id);
      if (alive) setServed({ key: needsKey, value: r.ok ? r.data : null });
    })();
    return () => {
      alive = false;
    };
    // the key holds the product, the child and its approved characters
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activity, needsKey]);

  const asksFamily = activity && found?.product.line === "family";
  const familyKey = `qamra-family:${q.item ?? q.product ?? ""}`;
  useEffect(() => {
    if (!asksFamily) return;
    let alive = true;
    (async () => {
      let value: Family | null = null;
      let known = !q.item; // a new line has no family of its own
      try {
        const raw = sessionStorage.getItem(familyKey);
        if (raw) [value, known] = [JSON.parse(raw) as Family, true];
      } catch {
        /* private mode: start from the line */
      }
      if (!value && q.item) {
        const r = await cartApi.get();
        const line = r.ok ? (r.data.items.find((i) => i.id === q.item) as { family?: FamilyPayload | null }) : null;
        if (line && "family" in line) {
          known = true;
          if (line.family) value = toFamily(line.family); // given on the product page
        }
      }
      if (alive) setFamily({ key: familyKey, value: value ?? emptyFamily(), known });
    })();
    return () => {
      alive = false;
    };
  }, [asksFamily, familyKey, q.item]);

  const refreshChildren = useCallback(async () => {
    const r = await createApi.children();
    if (r.ok) setChildren(r.data);
  }, []);

  /** A step changed the child: keep the list current, then move on. */
  const saveChild = useCallback(
    (c: Child) => setChildren((list) => [...(list ?? []).filter((x) => x.id !== c.id), c]),
    [],
  );

  const onCharacter = useCallback(
    (c: Character) => {
      setCharacter({ id: c.id, value: c });
      void refreshChildren(); // redraws left
      if (c.id !== q.character) go({ step: "character", character: c.id, style: c.style });
    },
    [go, q.character, refreshChildren],
  );
  const onBook = useCallback((b: Book) => setBook({ id: b.id, value: b }), []);

  if (failure) {
    return (
      <div className="mx-auto flex min-h-dvh max-w-[640px] flex-col justify-center gap-4 px-4">
        <Alert>{failure.message}</Alert>
        <Button variant="primary" size="lg" onClick={failure.retry}>
          {t("retry")}
        </Button>
        <Link href="/cart" className="min-h-11 content-center text-center font-semibold text-night-900 underline">
          {t("toCart")}
        </Link>
      </div>
    );
  }

  const shownCharacter = q.character && character?.id === q.character ? character.value : null;
  const shownBook = q.book && book?.id === q.book ? book.value : null;
  const loading =
    children === null ||
    (!!q.product && !catalogDone) ||
    (!!q.character && character?.id !== q.character) ||
    (!!q.book && book?.id !== q.book) ||
    (asksFamily && family?.key !== familyKey);
  if (loading) {
    return (
      <div role="status" className="flex min-h-dvh flex-col items-center justify-center gap-4 text-ink-muted">
        <MoonPhase p={0.5} className="size-16 animate-pulse" />
        {t("loading")}
      </div>
    );
  }
  if (q.product && !found) {
    // an old link, or a variant that is no longer sold
    return (
      <div className="mx-auto flex min-h-dvh max-w-[640px] flex-col justify-center gap-4 px-4">
        <Alert>{t("activity.unknown")}</Alert>
        <Link href="/cart" className="min-h-11 content-center text-center font-semibold text-night-900 underline">
          {t("toCart")}
        </Link>
      </div>
    );
  }

  const plan = parsePlan(q.plan);
  // a story's type: the URL's, the book's, or a story SKU's; an activity book never has one
  const storyLine: Line | null = activity
    ? null
    : (q.line ??
      shownBook?.line ??
      (found && ["classic", "magic"].includes(found.product.line) ? (found.product.line as Line) : null));
  const productLine: string | null = activity ? (found!.product.line as string) : storyLine;

  /** The styles a story type draws in (both types while it is not chosen). */
  function storyStyles(value: Line | null): Set<string> {
    const lines = value ? [value] : ["classic", "magic"];
    return new Set((catalog?.styles ?? []).filter((s) => lines.some((l) => s.lines.includes(l))).map((s) => s.slug));
  }

  /**
   * The approved character a story reuses: in a style the type draws, and the style the story page chose; the one
   * approved last (a parent can go back to an earlier drawing).
   */
  function readyStory(c: Child, value: Line | null): Character | null {
    const styles = storyStyles(value);
    return lastApproved(c.characters, (ch) => styles.has(ch.style) && (!q.style || ch.style === q.style));
  }

  /**
   * The styles this book can use for a child (the style step's list): the character step offers the earlier
   * drawings in these only. Null while the catalog is unknown (then every drawing is offered).
   */
  function usableStyles(c: Child): string[] | null {
    if (!catalog) return null;
    if (activity) return needs?.character.styles ?? activityStyles(catalog, productLine!);
    const ready = classicStyles(themes, classicVariant(c), q.theme);
    return [...storyStyles(storyLine)].filter((s) => storyLine !== "classic" || ready.has(s));
  }

  /** What this activity book needs from a child: the server's answer when it came, else the same local rules. */
  function needsOf(c: Child | null): Needs {
    return (served?.key === needsKeyOf(q.product, c) && served.value) || localNeeds(found!, catalog, c);
  }

  /** The character an activity book would use for a child (shown on the child's card). */
  function readyActivity(c: Child): Character | null {
    const id = needsOf(c).character.reuse_id;
    return c.characters.find((ch) => ch.id === id) ?? null;
  }

  /**
   * The style picked on the story page (Addendum 9), when this line can draw it for this child: then the
   * style step is already answered and the character is drawn right away. Before the child is known (a new
   * child on the child step), when the line can draw it for some look, so «n من N» doesn't count a style step
   * that the story page already answered.
   */
  function presetStyle(value: Line, c: Child | null): string | null {
    const s = catalog?.styles.find((x) => x.slug === q.style);
    if (!s || !s.lines.includes(value)) return null;
    const looks: ClassicVariant[] = c ? [classicVariant(c)] : ["girl", "girl_hijab", "boy"];
    if (value === "classic" && !looks.some((look) => classicStyles(themes, look, q.theme).has(s.slug))) return null;
    return s.slug;
  }

  // a story reuses its ready character even when the URL doesn't name it (e.g. from the free cover)
  const storyReady = !activity && child ? readyStory(child, storyLine) : null;
  const usedCharacter = shownCharacter ?? (!activity && !q.character ? storyReady : null);
  const needs = activity ? needsOf(child ?? null) : null;

  /** The flow's state for a child (the URL's, or the one picked on the child step). */
  function stateFor(c: Child | null | undefined): FlowState {
    const fresh = activity && redraw && !!c && c.id === picked?.id; // «ارسموا شخصية جديدة بأسلوب آخر»
    const reusable = activity ? !!c && !fresh && !!needsOf(c).character.reuse_id : !!c && !!readyStory(c, storyLine);
    return {
      kind: activity ? "activity" : "story",
      productLine,
      child: c ? { consent: c.consent, photos: c.photos } : null,
      reusable,
      character: c && c.id === child?.id && usedCharacter ? { approved: usedCharacter.approved } : null,
      book: shownBook ? { status: shownBook.status, line: shownBook.line } : null,
      stylePreset: !activity && !!storyLine && !!presetStyle(storyLine, c ?? null),
      companionOffered: !activity && !!companionAddOn(catalog, storyLine ?? "magic"),
      asksFamily,
      plan: c && c.id === child?.id ? plan : null,
    };
  }

  const state = stateFor(child);
  const wanted = (STEPS as readonly string[]).includes(q.step ?? "") ? (q.step as Step) : null;
  const step: Step = wanted && canShow(wanted, state) ? wanted : resumeAt(state);
  const steps = stepsFor(step === "child" ? stateFor(picked ?? null) : state);
  const count = progress(steps, step);
  const shownName = step === "child" ? (picked?.name ?? null) : (child?.name ?? null);
  const productName = found ? (locale === "ar" ? found.product.name_ar : found.product.name_en) : null;
  const frameTitle = activity
    ? shownName
      ? t(`titles.${productLine}`, nameCases(shownName))
      : productName!
    : shownName
      ? t("titles.story", nameCases(shownName))
      : t("newBook");
  const frame = { title: frameTitle, ...count, close: q.item ? "/cart" : "/account" };

  /** Back: the step before this one in this flow (or the child step). */
  function previous(from: Step): Step {
    const i = steps.indexOf(from);
    return i > 0 ? steps[i - 1]! : "child";
  }

  /** After the character: «ارسم صاحبك» when the catalog offers a drawn companion for this line, else the story. */
  const storyOrCompanion = (value: Line): Step => (companionAddOn(catalog, value) ? "companion" : "story");

  function fail(r: { error: Parameters<typeof errorText>[0]; status: number }): string {
    return errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown"));
  }

  /** Draw the story's character in the preset style, else show the style step. */
  async function styleOrDraw(c: Child, value: Line, pin?: PlanToken[]) {
    const preset = presetStyle(value, c);
    const planned = pin ? { plan: formatPlan(pin) } : {};
    if (preset) {
      const r = await createApi.draw(c.id, preset);
      if (r.ok) {
        setCharacter({ id: r.data.id, value: r.data });
        void refreshChildren();
        go({ step: "character", child: c.id, line: value, character: r.data.id, style: r.data.style, ...planned });
        return;
      }
    }
    go({ step: "style", child: c.id, line: value, character: null, ...planned });
  }

  /** A story with its type known: reuse a ready character, else the drawing steps (pinned for the count). */
  function continueWith(c: Child, value: Line, lineAsked: boolean) {
    const ready = readyStory(c, value);
    const pin = planFor(
      {
        ...stateFor(c),
        productLine: value,
        reusable: !!ready,
        stylePreset: !!presetStyle(value, c),
        companionOffered: !!companionAddOn(catalog, value),
      },
      lineAsked,
    );
    const base = { child: c.id, line: value, book: null, plan: formatPlan(pin) };
    if (ready) go({ ...base, step: storyOrCompanion(value), character: ready.id, style: ready.style });
    else if (!c.consent) go({ ...base, step: "consent", character: null });
    else if (!c.photos) go({ ...base, step: "photo", character: null });
    else void styleOrDraw(c, value, pin);
  }

  /** An activity book: what it needs from this child, from the server (or the same rules here). */
  async function neededFor(c: Child): Promise<Needs | string> {
    const r = await createApi.needs(q.product as string, c.id);
    if (r.ok) return r.data;
    if (missingEndpoint(r)) return localNeeds(found!, catalog, c); // FALLBACK until §d chunk 8 is deployed
    return fail(r);
  }

  /** The child step is done: the activity book's next step, or the story's type, drawing or story. */
  async function afterChild(c: Child, extra: { nameEn?: string; redraw?: boolean }): Promise<string | null> {
    saveChild(c);
    if (extra.nameEn !== undefined && extra.nameEn !== (c.name_latin ?? "")) {
      setPendingEn((m) => ({ ...m, [c.id]: extra.nameEn! })); // not saved on the child: goes with the cart line
    }
    if (!activity) {
      if (!storyLine) go({ step: "line", child: c.id, character: null, book: null, plan: "line" });
      else continueWith(c, storyLine, plan.includes("line")); // back on the child step: the type stays counted
      return null;
    }
    const n = await neededFor(c);
    if (typeof n === "string") return n;
    if (n.child?.name_problem) return t("who.arabicInvalid"); // the tracing pages can't write this name
    // the ready character, unless the parent asked for a new one in another style
    const reuse = extra.redraw ? null : n.character.reuse_id;
    const pin = planFor({ ...stateFor(c), reusable: !!reuse }, false);
    const base = { child: c.id, book: null, plan: formatPlan(pin) };
    if (reuse) go({ ...base, step: asksFamily ? "family" : "summary", character: reuse, style: null });
    else if (!c.consent) go({ ...base, step: "consent", character: null, style: null });
    else if (!c.photos) go({ ...base, step: "photo", character: null, style: null });
    else go({ ...base, step: "style", character: null, style: null }); // a photo saved in the last 24 hours
    return null;
  }

  /** Consent given: the photo, or the drawing (a story's type is chosen before the consent now). */
  function afterConsent(c: Child) {
    if (activity) go({ step: c.photos ? "style" : "photo", child: c.id });
    else if (!storyLine) go({ step: "line", child: c.id });
    else if (!c.photos && !readyStory(c, storyLine)) go({ step: "photo", child: c.id });
    else void styleOrDraw(c, storyLine);
  }

  /** «أضيفوا للسلة»: the activity book for this child, with what the flow collected; then the cart. */
  async function addProduct(c: Child): Promise<string | null> {
    const n = needs!;
    const nameEn = n.asks.name_en ? (pendingEn[c.id] ?? c.name_latin ?? undefined) : undefined;
    // a line opened from the cart's «تعديل» may predate these questions: they are asked before it is saved
    if (tracesName(productLine) && !isArabicName(c.name)) return t("who.arabicInvalid");
    if (n.asks.name_en && !nameEn) return t("who.nameEnInvalid");
    const given = asksFamily && family ? familyPayload(family.value) : undefined;
    // an empty family overrides the product page's only when the line's own family could be read
    const sentFamily = asksFamily ? (given ?? (family?.known ? EMPTY_FAMILY : undefined)) : undefined;
    const r = await createApi.addWorkbook({
      sku: q.product as string,
      child_id: c.id,
      ...(q.item ? { item_id: q.item } : {}),
      ...((usedCharacter?.id ?? n.character.reuse_id)
        ? { character_id: usedCharacter?.id ?? n.character.reuse_id! }
        : {}),
      ...(nameEn ? { name_en: nameEn } : {}),
      ...(sentFamily ? { family: sentFamily } : {}),
    });
    if (!r.ok) return fail(r);
    try {
      sessionStorage.removeItem(familyKey);
    } catch {
      /* nothing kept */
    }
    router.push("/cart");
    return null;
  }

  function setFamilyValue(value: Family) {
    setFamily((f) => (f ? { ...f, value } : f));
    try {
      sessionStorage.setItem(familyKey, JSON.stringify(value));
    } catch {
      /* private mode: kept for this page only */
    }
  }

  const body = (() => {
    switch (step) {
      case "child":
        return (
          <ChildStep
            kind={activity ? "activity" : "story"}
            productLine={productLine}
            known={children ?? []}
            initial={q.child}
            asksNameEn={activity && needsOf(child ?? null).asks.name_en}
            traces={tracesName(productLine)}
            ready={(c) => (activity ? readyActivity(c) : readyStory(c, storyLine))}
            nameEnOf={(c) => pendingEn[c.id] ?? c.name_latin ?? ""}
            preview={(name, gender) => {
              if (activity) return t(`titles.${productLine}`, nameCases(name)); // «دوسية {nameGen}»
              const theme = themes.find((th) => th.slug === q.theme);
              return theme ? fillTitle(theme.title, name, gender) : null;
            }}
            onSelect={setPicked}
            onRedraw={activity ? setRedraw : undefined}
            onEdited={saveChild}
            onDone={afterChild}
          />
        );
      case "line":
        return (
          <LineStep
            child={child!}
            catalog={catalog}
            themes={themes}
            theme={q.theme}
            initial={storyLine}
            back={() => go({ step: "child" })}
            onDone={(value) => continueWith(child!, value, true)}
          />
        );
      case "consent":
        return (
          <ConsentStep
            child={child!}
            productLine={productLine}
            back={() => go({ step: previous("consent") })}
            onDone={(c) => {
              saveChild(c);
              afterConsent(c);
            }}
          />
        );
      case "photo":
        return (
          <PhotoStep
            child={child!}
            productLine={productLine}
            back={() => go({ step: previous("photo") })}
            onDone={(c) => {
              saveChild(c);
              if (activity) go({ step: "style" });
              else if (storyLine) void styleOrDraw(c, storyLine);
              else go({ step: "line" });
            }}
          />
        );
      case "style":
        return activity ? (
          <StyleStep
            kind="activity"
            child={child!}
            line={productLine!}
            sku={q.product}
            accepted={needs?.character.styles ?? null}
            catalog={catalog}
            themes={themes}
            theme={null}
            initial={q.style}
            back={() => go({ step: previous("style") })}
            onDrawing={onCharacter}
          />
        ) : (
          <StyleStep
            child={child!}
            line={storyLine!}
            catalog={catalog}
            themes={themes}
            theme={q.theme}
            initial={q.style}
            back={() => go({ step: previous("style") })}
            onDrawing={onCharacter}
          />
        );
      case "character":
        return (
          <CharacterStep
            child={child!}
            character={shownCharacter!}
            productLine={productLine}
            usable={usableStyles(child!)}
            back={() => go({ step: "style" })}
            onChange={onCharacter}
            onApproved={(c) => {
              // maybe an earlier drawing, in another style: the book then uses that drawing and its style
              setCharacter({ id: c.id, value: c });
              void refreshChildren();
              const chosen = { character: c.id, style: c.style };
              if (activity) go({ step: asksFamily ? "family" : "summary", ...chosen });
              else go({ step: storyLine ? storyOrCompanion(storyLine) : "line", ...chosen });
            }}
          />
        );
      case "companion":
        return (
          <CompanionStep
            child={child!}
            line={storyLine!}
            catalog={catalog}
            style={usedCharacter?.style ?? q.style}
            companionId={q.companion}
            sub={q.cstep}
            go={(patch) => go(patch)}
            back={() => go({ step: previous("companion"), cstep: null })}
            onDone={(id) => go({ step: "story", companion: id, cstep: null })}
          />
        );
      case "story":
        return (
          <StoryStep
            child={child!}
            character={usedCharacter!}
            line={storyLine!}
            themes={themes}
            catalog={catalog}
            initial={q.theme}
            back={() => go({ step: previous("story") })}
            companion={companionAddOn(catalog, storyLine!) ? q.companion : null}
            onCompanion={companionAddOn(catalog, storyLine!) ? () => go({ step: "companion" }) : undefined}
            onStarted={(b) => {
              setBook({ id: b.id, value: b });
              go({ step: b.status === "generating" ? "writing" : "format", book: b.id, theme: b.theme });
            }}
          />
        );
      case "writing":
        return (
          <WritingStep
            child={child!}
            book={shownBook!}
            back={() => go({ step: "story", book: null })}
            onChange={onBook}
          />
        );
      case "review":
        return (
          <ReviewStep
            child={child!}
            book={shownBook!}
            back={() => go({ step: "story", book: null })}
            onChange={onBook}
            onDone={() => go({ step: "format" })}
          />
        );
      case "format":
        return (
          <FormatStep
            child={child!}
            book={shownBook!}
            theme={themes.find((th) => th.slug === shownBook?.theme) ?? null}
            catalog={catalog}
            back={() => go(shownBook?.line === "magic" ? { step: "review" } : { step: "story", book: null })}
            onAdded={() => go({ step: "addons" })}
          />
        );
      case "addons":
        return (
          <AddOnsStep
            child={child!}
            book={shownBook!}
            theme={themes.find((th) => th.slug === shownBook?.theme) ?? null}
            catalog={catalog}
            back={() => go({ step: "format" })}
          />
        );
      case "family":
        return (
          <FamilyStep
            child={child!}
            value={family?.value ?? emptyFamily()}
            onChange={setFamilyValue}
            back={() => go({ step: previous("family") })}
            onDone={() => go({ step: "summary" })}
            onSkip={() => {
              setFamilyValue(emptyFamily());
              go({ step: "summary" });
            }}
          />
        );
      case "summary": {
        const n = needs!;
        return (
          <SummaryStep
            child={child!}
            product={found!.product}
            variant={found!.variant}
            currency={catalog!.currency}
            characterId={usedCharacter?.id ?? n.character.reuse_id}
            nameEn={n.asks.name_en ? (pendingEn[child!.id] ?? child!.name_latin ?? "") : null}
            family={asksFamily ? (family ? (familyPayload(family.value) ?? null) : null) : undefined}
            ages={n.ages}
            itemId={q.item}
            back={() => go({ step: previous("summary") })}
            onEditChild={() => go({ step: "child" })}
            onEditFamily={asksFamily ? () => go({ step: "family" }) : undefined}
            onNewCharacter={() => {
              // a new drawing, in a style the parent picks: a new photo unless one was saved in the last 24 hours
              const c = child!;
              const pin: PlanToken[] = [
                ...(c.consent ? [] : (["consent"] as PlanToken[])),
                ...(c.photos ? [] : (["photo"] as PlanToken[])),
                "style",
                "character",
              ];
              go({
                step: !c.consent ? "consent" : !c.photos ? "photo" : "style",
                character: null,
                style: null,
                plan: formatPlan(pin),
              });
            }}
            onAdd={() => addProduct(child!)}
          />
        );
      }
    }
  })();

  return <FlowFrameContext.Provider value={frame}>{body}</FlowFrameContext.Provider>;
}
