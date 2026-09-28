import type { ReactNode } from "react";

export function AuthCard({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <section className="mx-auto mt-8 w-full max-w-md rounded-xl border border-line bg-paper-raised p-6 shadow-1 sm:mt-14 sm:p-8">
      <h1 className="text-h2 font-bold text-night-900">{title}</h1>
      <p className="mt-1 text-body text-ink-muted">{subtitle}</p>
      <div className="mt-6">{children}</div>
    </section>
  );
}
