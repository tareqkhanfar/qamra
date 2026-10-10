import type { CSSProperties } from "react";
import { Scene, fromArt, type SceneArt } from "@/components/art/Scene";
import type { Example } from "@/lib/examples";
import type { ThemeArt } from "@/lib/themeArt";
import { fillTitle, type TitleGender } from "@/lib/themeTitle";
import { ExampleImage } from "./ExampleImage";

/**
 * A book cover as the printed one looks: the art, a soft shade at the top and the title on it (the child's name
 * big, the rest in moon-gold). A published example's real cover when there is one; otherwise the story's
 * own cover illustration (`lib/themeArt`), else its illustrated placeholder, with the same title treatment. Sizes
 * follow the cover's own width.
 */
export function CoverArt({
  example,
  art,
  titleName,
  titleRest,
  alt,
  sizes,
  priority = false,
  artStyle,
  picture = null,
  className = "",
}: {
  example: Example | null;
  art: SceneArt;
  titleName: string;
  titleRest: string;
  alt: string;
  sizes: string;
  priority?: boolean;
  artStyle?: CSSProperties;
  /** The story's own cover illustration, used when there is no example. */
  picture?: ThemeArt | null;
  className?: string;
}) {
  const cover = example?.pages.find((p) => p.beat === 0);
  return (
    <div className={`@container relative aspect-square overflow-hidden ${className}`}>
      {cover ? (
        <ExampleImage
          page={cover}
          alt={alt}
          sizes={sizes}
          priority={priority}
          className="absolute inset-0 size-full object-cover"
        />
      ) : picture ? (
        // eslint-disable-next-line @next/next/no-img-element -- a static 900 px sample, with a 480 px one for cards
        <img
          src={picture.src}
          srcSet={`${picture.thumb} 480w, ${picture.src} 900w`}
          sizes={sizes}
          alt={alt}
          width={900}
          height={900}
          loading={priority ? "eager" : "lazy"}
          fetchPriority={priority ? "high" : undefined}
          className="absolute inset-0 size-full object-cover"
        />
      ) : (
        <div role="img" aria-label={alt} className="absolute inset-0" style={artStyle}>
          <Scene {...fromArt(art)} ratio={1} kidScale={Math.min(art.kid_scale ?? 0.5, 0.5)} className="size-full" />
        </div>
      )}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(14,21,48,0.45),rgba(14,21,48,0.12)_30%,transparent_45%)]"
      />
      <div aria-hidden="true" className="absolute inset-x-[7%] top-[7%] text-center font-display leading-[1.15]">
        <div className="text-[9cqw] font-extrabold text-paper-raised [text-shadow:0_0.5cqw_2cqw_rgba(14,21,48,0.55)]">
          {titleName}
        </div>
        {titleRest && (
          <div className="mt-[1cqw] text-[4.6cqw] font-extrabold text-amber-500 [text-shadow:0_0.4cqw_1.6cqw_rgba(14,21,48,0.6)]">
            {titleRest}
          </div>
        )}
      </div>
      {/* the spine: Arabic books are bound on the right, English ones on the left */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-y-0 start-0 w-[5%] bg-[linear-gradient(to_left,rgba(14,21,48,0.28),transparent)] ltr:bg-[linear-gradient(to_right,rgba(14,21,48,0.28),transparent)]"
      />
    </div>
  );
}

/** "{name} في أوّل يوم بالروضة" → ("يوسف", "في أوّل يوم بالروضة") for the placeholder cover. */
export function splitTemplate(title: string, name: string, gender: TitleGender = null): [string, string] {
  const filled = fillTitle(title, name, gender);
  if (filled.startsWith(name)) return [name, filled.slice(name.length).trim()];
  return [filled, ""];
}
