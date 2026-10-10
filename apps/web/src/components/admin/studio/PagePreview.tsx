"use client";

import { useTranslations } from "next-intl";
import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { naskh } from "@/components/book/fonts";
import { nameCases } from "@/lib/arabicName";
import { renderText, type TextContext, type TextPage } from "@/lib/studio";

// The print renderer's geometry (packages/pdf templates/_base.css.j2), in mm on a 216 mm page with bleed.
const PAGE = 216;
const SAFE = 13;
const LOW = 24; // above the folio
const PT = 0.3528; // mm per point
const mm = (n: number) => `calc(${n} * var(--mm))`;

/** The panel's box on the picture (double width for a spread): the renderer's CSS for its area. */
function panelPlace(area: string, spread: boolean): CSSProperties {
  if (area === "left" || area === "right") return { top: mm(SAFE), bottom: mm(LOW), width: mm(84), [area]: mm(SAFE) };
  const offset = spread && area.endsWith("right") ? PAGE : 0; // a spread's panel sits on the half read first
  const vertical: CSSProperties = area.startsWith("bottom") ? { bottom: mm(LOW) } : { top: mm(SAFE) };
  const right = (spread ? PAGE * 2 : PAGE) - (offset + PAGE) + SAFE;
  return { ...vertical, left: mm(offset + SAFE), right: mm(right), maxHeight: mm(78) };
}

/**
 * The page as the book prints it, as far as the renderer allows: the art, and the words in the cream panel at
 * the page's text area, in the story font at the size the child's age sets (it shrinks to fit, down to a
 * minimum, like the PDF). English books use the mirrored art. The cover shows the title. A theme (no art, both
 * looks) is previewed on a plain page, for a sample boy or girl.
 */
export function PagePreview({
  src,
  page,
  ar,
  en,
  texts,
}: {
  src: string | null;
  page: TextPage;
  ar: string;
  en: string;
  texts: TextContext;
}) {
  const t = useTranslations("studio.preview");
  const [lang, setLang] = useState<"ar" | "en">("ar");
  const [age, setAge] = useState<"young" | "older">("young");
  const [picked, setPicked] = useState<"m" | "f">("f");
  const gender = texts.gender ?? picked;
  const panel = useRef<HTMLDivElement>(null);
  const note = useRef<HTMLParagraphElement>(null);
  const [size, min] = texts.text_pt[age];
  const layout = page.beat === 0 ? "cover" : (page.layout ?? "full");
  const spread = layout === "spread";
  const mirrored = lang === "en";
  const name = texts.names[gender][lang];
  const companion = lang === "ar" ? texts.sample.companion_ar : texts.sample.companion_en;
  const vowelized = lang === "ar" && page.vowelized && ar === page.pinned.ar ? page.vowelized : null;
  const text = renderText(vowelized ?? (lang === "ar" ? ar : en), gender, name, companion);
  let area = page.area ?? (layout === "split" ? "none" : "top");
  if (mirrored) area = area.replace(/left|right/, (s) => (s === "left" ? "right" : "left"));

  useLayoutEffect(() => {
    const box = panel.current;
    const words = box?.querySelector("p");
    if (!box || !words) return;
    let pt = size;
    for (; pt >= min; pt -= 0.5) {
      words.style.fontSize = mm(pt * PT);
      if (box.scrollHeight <= box.clientHeight + 1) break;
    }
    if (note.current) {
      note.current.textContent = pt < min ? t("tooLong") : t("fits", { pt: Math.max(pt, min) });
      note.current.className = `text-caption ${pt < min ? "font-semibold text-danger" : "text-ink-muted"}`;
    }
  }, [text, size, min, area, layout, t]);

  const width = spread ? PAGE * 2 : PAGE;
  const story = `${lang === "ar" ? naskh.className : "font-body"} text-center text-ink`;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2" role="group" aria-label={t("options")}>
        {(["ar", "en"] as const).map((l) => (
          <Toggle key={l} on={lang === l} onClick={() => setLang(l)} label={t(`lang.${l}`)} />
        ))}
        {(["young", "older"] as const).map((a) => (
          <Toggle key={a} on={age === a} onClick={() => setAge(a)} label={t(`age.${a}`, { pt: texts.text_pt[a][0] })} />
        ))}
        {texts.gender === null &&
          (["f", "m"] as const).map((g) => (
            <Toggle key={g} on={picked === g} onClick={() => setPicked(g)} label={t(`gender.${g}`)} />
          ))}
      </div>
      <div style={{ containerType: "inline-size" }} className="overflow-hidden rounded-lg shadow-2">
        <div
          dir="ltr"
          className="relative bg-paper"
          style={{ ["--mm" as string]: `calc(100cqw / ${width})`, aspectRatio: `${width} / ${PAGE}` }}
        >
          {src && (
            // eslint-disable-next-line @next/next/no-img-element -- streamed from the admin API, private
            <img
              src={src}
              alt=""
              className={`absolute inset-x-0 top-0 w-full object-cover ${mirrored ? "-scale-x-100" : ""}`}
              style={{ height: layout === "split" ? mm(129) : "100%" }}
            />
          )}
          {layout === "cover" ? (
            <div
              className="absolute rounded-[3cqw] bg-paper-raised/90 px-[3cqw] py-[2cqw]"
              style={{ top: mm(18), left: mm(SAFE), right: mm(SAFE) }}
            >
              <p
                dir={lang === "ar" ? "rtl" : "ltr"}
                className="text-center font-display font-extrabold text-night-900"
                style={{ fontSize: mm(30 * PT), lineHeight: 1.3 }}
              >
                {text}
              </p>
            </div>
          ) : (
            text && (
              <div
                ref={panel}
                className={`absolute flex flex-col justify-center overflow-hidden ${area === "none" ? "" : "rounded-[calc(6*var(--mm))] shadow-1"}`}
                style={{
                  ...(area === "none"
                    ? { top: mm(133), bottom: mm(LOW), left: mm(SAFE), right: mm(SAFE) }
                    : panelPlace(area, spread)),
                  padding: `${mm(5)} ${mm(8)}`,
                  background: area === "none" ? undefined : "rgba(255,253,248,.88)",
                }}
              >
                <p
                  dir={lang === "ar" ? "rtl" : "ltr"}
                  lang={lang}
                  className={story}
                  style={{ fontSize: mm(size * PT), lineHeight: 1.9 }}
                >
                  {text}
                </p>
              </div>
            )
          )}
        </div>
      </div>
      <p ref={note} className="text-caption text-ink-muted" aria-live="polite" />
      <p className="text-caption text-ink-muted">{t("note", { ...nameCases(name), size, min })}</p>
    </div>
  );
}

function Toggle({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`min-h-10 rounded-full border px-3 text-small ${on ? "border-night-900 bg-night-900 text-paper" : "border-line bg-paper-raised"}`}
    >
      {label}
    </button>
  );
}
