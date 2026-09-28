import type { ReactNode } from "react";

export function AuthCard({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <section className="border-line bg-paper-raised shadow-1 mx-auto mt-8 w-full max-w-md rounded-xl border p-6 sm:mt-14 sm:p-8">
      <h1 className="text-h2 text-night-900 font-bold">{title}</h1>
      <p className="text-body text-ink-muted mt-1">{subtitle}</p>
      <div className="mt-6">{children}</div>
    </section>
  );
}
