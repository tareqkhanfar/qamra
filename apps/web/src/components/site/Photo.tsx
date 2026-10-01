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

export function hasPhoto(name: PhotoName): boolean {
  try {
    return existsSync(path.join(DIR, `${name}.jpg`));
  } catch {
    return false;
  }
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
  const ratio = PHOTOS[name] === "1:1" ? "1 / 1" : "3 / 2";
  return (
    <div className={`relative overflow-hidden ${className}`} style={{ aspectRatio: ratio }}>
      <Image src={`/photos/${name}.jpg`} alt={alt} fill sizes={sizes} priority={priority} className="object-cover" />
    </div>
  );
}
