import type { ReactNode } from "react";

/** Small line icons for the contact links and the QR page (24×24, currentColor). */
export type ContactIconName =
  "phone" | "whatsapp" | "email" | "facebook" | "instagram" | "globe" | "bag" | "book" | "copy";

const PATHS: Record<ContactIconName, ReactNode> = {
  phone: (
    <path d="M6.6 3.5h2.6l1.4 4-2 1.4a12 12 0 0 0 6.5 6.5l1.4-2 4 1.4v2.6a2 2 0 0 1-2.2 2A16.5 16.5 0 0 1 4.6 5.7a2 2 0 0 1 2-2.2z" />
  ),
  whatsapp: (
    <>
      <path d="M4 20l1.2-4A8.5 8.5 0 1 1 8.4 19z" />
      <path d="M9.2 8.6c.3 2.7 2.4 4.9 5.2 5.3l.9-1.2 1.8.8-.4 1.4c-.2.5-.7.8-1.2.8A7.6 7.6 0 0 1 8.2 8.4c0-.5.3-1 .8-1.2l1.4-.4.8 1.8z" />
    </>
  ),
  email: (
    <>
      <rect x="3" y="5.5" width="18" height="13" rx="2" />
      <path d="M3.5 7l8.5 6 8.5-6" />
    </>
  ),
  facebook: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="4" />
      <path d="M15.5 8h-1.8A1.7 1.7 0 0 0 12 9.7V21M9.5 13h5.5" />
    </>
  ),
  instagram: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.2" cy="6.8" r="0.6" fill="currentColor" />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.7 3.6 5.7 3.6 9s-1.1 6.3-3.6 9c-2.5-2.7-3.6-5.7-3.6-9S9.5 5.7 12 3z" />
    </>
  ),
  bag: (
    <>
      <path d="M5 8h14l-1 12H6z" />
      <path d="M9 10V7a3 3 0 0 1 6 0v3" />
    </>
  ),
  book: (
    <>
      <path d="M3 5h6a3 3 0 0 1 3 3v12a2 2 0 0 0-2-2H3z" />
      <path d="M21 5h-6a3 3 0 0 0-3 3v12a2 2 0 0 1 2-2h7z" />
    </>
  ),
  copy: (
    <>
      <rect x="8" y="8" width="12" height="12" rx="2" />
      <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
    </>
  ),
};

export function ContactIcon({ name, className = "size-6" }: { name: ContactIconName; className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
