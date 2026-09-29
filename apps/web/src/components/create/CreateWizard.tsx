"use client";

import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { Alert } from "@/components/ui/Alert";
import { useRouter } from "@/i18n/navigation";
import { api, errorText, type User } from "@/lib/api";
import type { ThemeCard } from "@/lib/catalog";
import { createApi, STEPS, type Book, type Character, type Child, type Line, type Step } from "@/lib/create";
import type { Catalog } from "@/lib/store";
import { CharacterStep } from "./CharacterStep";
import { ChildStep } from "./ChildStep";
import { ConsentStep } from "./ConsentStep";
import { FormatStep } from "./FormatStep";
import { LineStep } from "./LineStep";
import { PhotoStep } from "./PhotoStep";
import { ReviewStep } from "./ReviewStep";
import { StoryStep } from "./StoryStep";
import { StyleStep } from "./StyleStep";
import { WritingStep } from "./WritingStep";

type Query = Partial<Record<"step" | "child" | "character" | "book" | "line" | "theme" | "style", string | null>>;
/** What was fetched for an id in the URL (null: not found or not this parent's). */
type Loaded<T> = { id: string; value: T | null };

/** The furthest step the saved state allows: a reload or a link from the account page resumes here. */
function furthest(child: Child | undefined, character: Character | null, book: Book | null, line: Line | null): Step {
  if (!child) return "child";
  if (book) {
    if (book.status === "generating" || book.status === "failed") return "writing";
    return book.line === "magic" && book.pages.length ? "review" : "format";
  }
  if (!child.consent) return "consent";
  if (!child.photos && !child.characters.some((c) => c.approved)) return "photo";
  if (!line) return "line";
  if (character) return character.approved ? "story" : "character";
  return "style";
}

/** Whether a step asked for in the URL can be shown with what is loaded. */
function allowed(
  step: Step,
  child: Child | undefined,
  character: Character | null,
  book: Book | null,
  line: Line | null,
) {
  switch (step) {
    case "child":
      return true;
    case "consent":
      return !!child;
    case "photo":
      return !!child?.consent;
    case "line":
      return !!child?.consent && (child.photos > 0 || child.characters.some((c) => c.approved));
    case "style":
      return !!child?.consent && !!line;
    case "character":
      return !!child && !!character;
    case "story":
      return !!child && !!line && !!character?.approved;
    case "writing":
      return !!child && !!book && (book.status === "generating" || book.status === "failed");
    case "review":
      return !!child && !!book && book.line === "magic" && book.status === "preview";
    case "format":
      return !!child && !!book && book.status !== "generating" && book.status !== "failed";
  }
}

/** The parent create flow (design Create1–Create9), then the store's checkout (Create10) and order page (Create11). */
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
  };
  const [children, setChildren] = useState<Child[] | null>(null);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [themes, setThemes] = useState<ThemeCard[]>([]);
  const [character, setCharacter] = useState<Loaded<Character> | null>(null);
  const [book, setBook] = useState<Loaded<Book> | null>(null);
  const [error, setError] = useState<string | null>(null);

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
        } else setError(errorText(me.error, locale, me.status === 0 ? te("network") : te("unknown")));
        return;
      }
      const [kids, store, worlds] = await Promise.all([
        createApi.children(),
        api<Catalog>("/api/store/catalog"),
        api<ThemeCard[]>(`/api/themes?lang=${locale}`),
      ]);
      if (!alive) return;
      if (store.ok) setCatalog(store.data);
      if (worlds.ok) setThemes(worlds.data);
      if (kids.ok) setChildren(kids.data);
      else setError(errorText(kids.error, locale, te("unknown")));
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
      if (alive) setCharacter({ id, value: r.ok ? r.data : null });
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

  const refreshChildren = useCallback(async () => {
    const r = await createApi.children();
    if (r.ok) setChildren(r.data);
  }, []);

  /** A step changed the child: keep the list current, then move on. */
  const saveChild = useCallback(
    (child: Child) => setChildren((list) => [...(list ?? []).filter((c) => c.id !== child.id), child]),
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

  if (error) {
    return (
      <div className="mx-auto flex min-h-dvh max-w-[640px] flex-col justify-center gap-4 px-4">
        <Alert>{error}</Alert>
      </div>
    );
  }

  const child = children?.find((c) => c.id === q.child);
  const shownCharacter = q.character && character?.id === q.character ? character.value : null;
  const shownBook = q.book && book?.id === q.book ? book.value : null;
  const loading =
    children === null || (!!q.character && character?.id !== q.character) || (!!q.book && book?.id !== q.book);
  if (loading) {
    return (
      <div role="status" className="flex min-h-dvh flex-col items-center justify-center gap-4 text-ink-muted">
        <MoonPhase p={0.5} className="size-16 animate-pulse" />
        {t("loading")}
      </div>
    );
  }

  const line = q.line ?? shownBook?.line ?? null;
  const wanted = (STEPS as readonly string[]).includes(q.step ?? "") ? (q.step as Step) : null;
  const step =
    wanted && allowed(wanted, child, shownCharacter, shownBook, line)
      ? wanted
      : furthest(child, shownCharacter, shownBook, line);
  const theme = themes.find((th) => th.slug === (shownBook?.theme ?? q.theme)) ?? null;

  /** After the book type: reuse an approved character that the type can draw, else choose a style. */
  function afterLine(value: Line) {
    if (!child) return;
    const styles = new Set((catalog?.styles ?? []).filter((s) => s.lines.includes(value)).map((s) => s.slug));
    const ready = [...child.characters].reverse().find((c) => c.approved && styles.has(c.style));
    if (ready) go({ step: "story", line: value, character: ready.id, style: ready.style });
    else if (!child.photos) go({ step: "photo", line: value });
    else go({ step: "style", line: value, character: null });
  }

  switch (step) {
    case "child":
      return (
        <ChildStep
          known={children ?? []}
          title={(theme ?? themes.find((th) => th.status === "available"))?.title ?? null}
          onPick={(c) => go({ step: c.consent ? "line" : "consent", child: c.id, character: null, book: null })}
          onAdded={(c) => {
            saveChild(c);
            go({ step: "consent", child: c.id, character: null, book: null });
          }}
        />
      );
    case "consent":
      return (
        <ConsentStep
          child={child!}
          back={() => go({ step: "child" })}
          onDone={(c) => {
            saveChild(c);
            go({ step: c.photos ? "line" : "photo" });
          }}
        />
      );
    case "photo":
      return (
        <PhotoStep
          child={child!}
          back={() => go({ step: "child" })}
          onDone={(c) => {
            saveChild(c);
            if (line) go({ step: "style", line, character: null });
            else go({ step: "line" });
          }}
        />
      );
    case "line":
      return (
        <LineStep
          child={child!}
          catalog={catalog}
          initial={line}
          back={() => go({ step: "photo" })}
          onDone={afterLine}
        />
      );
    case "style":
      return (
        <StyleStep
          child={child!}
          line={line!}
          catalog={catalog}
          themes={themes}
          theme={q.theme}
          initial={q.style}
          back={() => go({ step: "line" })}
          onDrawing={onCharacter}
        />
      );
    case "character":
      return (
        <CharacterStep
          child={child!}
          character={shownCharacter!}
          back={() => go({ step: "style" })}
          onChange={onCharacter}
          onApproved={(c) => {
            setCharacter({ id: c.id, value: c });
            void refreshChildren();
            go({ step: line ? "story" : "line" });
          }}
        />
      );
    case "story":
      return (
        <StoryStep
          child={child!}
          character={shownCharacter!}
          line={line!}
          themes={themes}
          catalog={catalog}
          initial={q.theme}
          back={() => go({ step: "character" })}
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
          theme={theme}
          catalog={catalog}
          back={() => go(shownBook?.line === "magic" ? { step: "review" } : { step: "story", book: null })}
          onAdded={() => router.push("/checkout")}
        />
      );
  }
}
