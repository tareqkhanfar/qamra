import { existsSync } from "node:fs";
import path from "node:path";
import Image from "next/image";
import type { ReactNode } from "react";

/**
 * Lifestyle photo slots (public/photos/README.md). Tareq drops the files in; until a file exists, the slot
 * renders its fallback (the current art) or nothing, so a missing photo never breaks a page. Server-only.
 */
export const PHOTOS = {
  "hero-reading": "3:2",
  "first-day": "3:2",
  "graduation-class": "3:2",
  "family-book-table": "3:2",
  "workbook-tracing": "1:1",
  "journey-qr": "3:2",
  "grandma-voice": "3:2",
  "gift-box": "1:1",
  "books-stack": "1:1",
  "kindergarten-teacher": "3:2",
} as const;

export type PhotoName = keyof typeof PHOTOS;

const DIR = path.join(process.cwd(), "public", "photos");

function has(file: string): boolean {
  try {
    return existsSync(path.join(DIR, file));
  } catch {
    return false;
  }
}

export function hasPhoto(name: PhotoName): boolean {
  return has(`${name}.jpg`);
}

/**
 * A short loop over the photo when `<name>.mp4` (and optionally `.webm`) exists, e.g. the home hero. It always
 * plays muted (the hero film carries the brand soundtrack for sharing; the site's own music is MusicPlayer). The
 * photo stays underneath as the poster and for reduced motion. Written as HTML because React's server render
 * does not emit `muted`, and browsers only autoplay muted video. `name` is one of the fixed slot names.
 */
function loop(name: PhotoName): string | null {
  if (!has(`${name}.mp4`)) return null;
  const webm = has(`${name}.webm`) ? `<source src="/photos/${name}.webm" type="video/webm">` : "";
  const poster = has(`${name}-poster.jpg`) ? `/photos/${name}-poster.jpg` : `/photos/${name}.jpg`; // the film's first frame
  return (
    `<video class="h-full w-full object-cover" autoplay muted loop playsinline preload="auto" ` +
    `poster="${poster}">${webm}<source src="/photos/${name}.mp4" type="video/mp4"></video>`
  );
}

export function Photo({
  name,
  alt,
  sizes,
  priority = false,
  className = "",
  fallback = null,
}: {
  name: PhotoName;
  alt: string;
  sizes: string;
  priority?: boolean;
  className?: string;
  fallback?: ReactNode;
}) {
  if (!hasPhoto(name)) return <>{fallback}</>;
  const video = loop(name);
  const ratio = PHOTOS[name] === "1:1" ? "1 / 1" : "3 / 2";
  return (
    <div className={`relative overflow-hidden ${className}`} style={{ aspectRatio: ratio }}>
      <Image src={`/photos/${name}.jpg`} alt={alt} fill sizes={sizes} priority={priority} className="object-cover" />
      {video && (
        <div
          aria-hidden
          className="absolute inset-0 motion-reduce:hidden"
          dangerouslySetInnerHTML={{ __html: video }}
        />
      )}
    </div>
  );
}
