/* eslint-disable @next/next/no-img-element -- the books' exported preview pages (static files in /public) */
import { imageSources, type ColoringBinding, type ColoringImage, type ColoringTitle } from "@/lib/coloring";
import { ColoringArt } from "./ColoringArt";

/** Each book's card colour (the printed cover is a colour card; the inside is black and white). */
export const COLORING_TONE: Record<ColoringTitle, string> = {
  letters: "bg-night-100",
  palestine: "bg-success-bg",
  ramadan: "bg-amber-100",
  sketchbook: "bg-lav-300/45",
};

/** The Wire-O rings along the top edge of «دفتري». */
function WireO({ count }: { count: number }) {
  return (
    <span aria-hidden="true" className="absolute inset-x-[8%] top-[1.5%] flex justify-between">
      {Array.from({ length: count }, (_, i) => (
        <span key={i} className="h-[9px] w-[5px] rounded-full border-[1.5px] border-night-900 bg-paper-raised" />
      ))}
    </span>
  );
}

/**
 * A book's cover: the real exported one when it exists, else a drawn stand-in (the cover's colour card, the title,
 * a line-art page and the page count) so the page never shows an empty box while the previews are missing.
 */
export function ColoringCover({
  cover,
  title,
  name,
  pagesLabel,
  binding,
  alt,
  nameSlot,
  size = "sm",
  sizes = "(min-width: 768px) 220px, 150px",
  priority = false,
  className = "",
}: {
  cover: ColoringImage | null;
  title: ColoringTitle;
  name: string;
  pagesLabel: string;
  binding: ColoringBinding;
  alt: string;
  nameSlot?: string; // the dashed slot where the child's name goes (the hero cover)
  size?: "sm" | "lg";
  sizes?: string;
  priority?: boolean;
  className?: string;
}) {
  if (cover) {
    return (
      <img
        {...imageSources(cover)}
        sizes={sizes}
        alt={alt}
        width={cover.w}
        height={cover.h}
        loading={priority ? "eager" : "lazy"}
        decoding="async"
        className={`aspect-[1/1.414] w-full rounded-[8px] object-cover object-top ${className}`}
      />
    );
  }
  const lg = size === "lg";
  return (
    <div
      role="img"
      aria-label={alt}
      className={`relative flex aspect-[1/1.414] w-full flex-col items-center overflow-hidden rounded-s-[6px] rounded-e-[12px] border border-line ${COLORING_TONE[title]} ${lg ? "gap-3 px-5 pt-8 pb-5" : "gap-1.5 px-2.5 pt-5 pb-2.5"} ${className}`}
    >
      {binding === "wire-o" && <WireO count={lg ? 12 : 8} />}
      <span
        className={`text-center font-display leading-tight font-extrabold text-night-900 ${lg ? "text-[28px]" : "text-[15px] md:text-[18px]"}`}
      >
        {name}
      </span>
      {nameSlot && (
        <span className="border-b-2 border-dashed border-night-500 px-2 text-small font-semibold text-night-700">
          {nameSlot}
        </span>
      )}
      <span className="flex min-h-0 w-full grow items-center justify-center rounded-[6px] border border-dashed border-night-500/40 bg-white p-1.5">
        <ColoringArt title={title} className="size-full" />
      </span>
      <span
        className={`rounded-full bg-paper-raised font-semibold text-night-900 ${lg ? "px-3 py-1 text-small" : "px-2 py-0.5 text-[11px] md:text-caption"}`}
      >
        {pagesLabel}
      </span>
    </div>
  );
}
