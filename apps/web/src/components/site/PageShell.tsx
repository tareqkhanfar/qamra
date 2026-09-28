import type { ReactNode } from "react";
import { SiteFooter } from "./SiteFooter";
import { SiteNav } from "./SiteNav";

/** Light header + content + footer: every page except the landing (which has its own hero header). */
export function PageShell({ children, footer = true }: { children: ReactNode; footer?: boolean }) {
  return (
    <>
      <SiteNav variant="light" />
      <main className="min-h-[60dvh]">{children}</main>
      {footer && <SiteFooter />}
    </>
  );
}
