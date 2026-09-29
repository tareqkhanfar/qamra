"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { MoonPhase } from "@/components/art/MoonPhase";
import { errorText } from "@/lib/api";
import { companionAddOn, companionApi, type Companion, type MyCompanion } from "@/lib/companion";
import type { Child, Line } from "@/lib/create";
import type { Catalog } from "@/lib/store";
import { CompanionChoose } from "./CompanionChoose";
import { CompanionGen } from "./CompanionGen";
import { CompanionIntro } from "./CompanionIntro";
import { CompanionName } from "./CompanionName";
import { DrawingCrop } from "./DrawingCrop";
import { DrawingUpload } from "./DrawingUpload";

export type CompanionNav = { companion?: string | null; cstep?: string | null };

/**
 * «ارسم صاحبك» (Addendum 1 §1, design CompIntro → CompUpload → CompCrop → CompName → CompGen → CompChoose):
 * optional sub-steps of step 6, between the character and the story. The companion's id and the sub-step
 * (`cstep`: upload | name) stay in the URL; the rest follows the companion's status on the server.
 */
export function CompanionStep({
  child,
  line,
  catalog,
  style,
  companionId,
  sub,
  go,
  back,
  onDone,
}: {
  child: Child;
  line: Line;
  catalog: Catalog | null;
  style: string | null;
  companionId: string | null;
  sub: string | null;
  go: (patch: CompanionNav) => void;
  back: () => void;
  onDone: (companionId: string | null) => void;
}) {
  const te = useTranslations("errors");
  const t = useTranslations("create");
  const locale = useLocale();
  const [comp, setComp] = useState<Companion | null>(null);
  const [mine, setMine] = useState<MyCompanion[]>([]);
  const [picked, setPicked] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const offer = companionAddOn(catalog, line);

  useEffect(() => {
    let alive = true;
    (async () => {
      const r = await companionApi.mine();
      if (alive && r.ok) setMine(r.data.filter((c) => c.child_id === child.id));
    })();
    return () => {
      alive = false;
    };
  }, [child.id]);

  useEffect(() => {
    if (!companionId) return;
    let alive = true;
    (async () => {
      const r = await companionApi.get(companionId);
      if (alive) setComp(r.ok ? r.data : null);
    })();
    return () => {
      alive = false;
    };
  }, [companionId]);

  const onChange = useCallback((c: Companion) => setComp(c), []);
  const fail = (r: { error: Parameters<typeof errorText>[0]; status: number }) =>
    setError(errorText(r.error, locale, r.status === 0 ? te("network") : te("unknown")));

  async function uploaded(file: File) {
    setBusy(true);
    setError(null);
    const r = await companionApi.upload(child.id, file);
    setBusy(false);
    if (!r.ok) return fail(r);
    setComp(r.data);
    go({ companion: r.data.id, cstep: null });
  }

  async function redraw(c: Companion) {
    setError(null);
    const r = await companionApi.draw(c.id, {
      name: c.name,
      type: c.type,
      type_other: c.type_other ?? undefined,
      traits: c.traits,
      style: style ?? undefined,
    });
    if (r.ok) setComp(r.data);
    else fail(r);
  }

  const shown = comp && comp.id === companionId ? comp : null;
  if (sub === "upload") {
    return (
      <DrawingUpload back={() => go({ cstep: null, companion: null })} onFile={uploaded} busy={busy} error={error} />
    );
  }
  if (companionId && !shown) {
    return (
      <div role="status" className="flex min-h-dvh flex-col items-center justify-center gap-4 text-ink-muted">
        <MoonPhase p={0.5} className="size-16 animate-pulse" />
        {t("loading")}
      </div>
    );
  }
  if (!shown || shown.status === "approved") {
    return (
      <CompanionIntro
        child={child}
        price={offer && !offer.free ? offer.price : null}
        currency={catalog?.currency ?? "ILS"}
        mine={mine}
        chosen={picked ?? shown?.id ?? null}
        onPick={setPicked}
        back={back}
        onStart={() => go({ cstep: "upload", companion: null })}
        onUse={onDone}
        onSkip={() => onDone(null)}
      />
    );
  }
  if (sub === "name" && shown.status !== "generating") {
    return (
      <CompanionName
        child={child}
        companion={shown}
        style={style}
        back={() => go({ cstep: null })}
        onDrawing={(c) => {
          setComp(c);
          go({ cstep: null });
        }}
      />
    );
  }
  if (shown.status === "draft") {
    return (
      <DrawingCrop
        companion={shown}
        back={() => go({ cstep: "upload", companion: null })}
        onChange={onChange}
        onDone={() => go({ cstep: "name" })}
      />
    );
  }
  if (shown.status === "ready") {
    return (
      <CompanionChoose
        child={child}
        companion={shown}
        back={() => go({ cstep: "name" })}
        onRedraw={() => void redraw(shown)}
        onChosen={(c) => onDone(c.id)}
        redrawError={error}
      />
    );
  }
  return (
    <CompanionGen
      child={child}
      companion={shown}
      onChange={onChange}
      onRetry={() => void redraw(shown)}
      onNewDrawing={() => go({ cstep: "upload", companion: null })}
      onSkip={() => onDone(null)}
      retryError={error}
    />
  );
}
