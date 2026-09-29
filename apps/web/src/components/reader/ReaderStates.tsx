import { MoonMark } from "@/components/Logo";
import { buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";

/** Loading (design: States 2 — a skeleton of the page) on the reader's night background. */
export function ReaderSkeleton({ label }: { label: string }) {
  return (
    <div className="flex min-h-dvh flex-col bg-night-950" aria-busy="true" aria-label={label}>
      <div className="flex h-16 items-center gap-3 px-4 md:h-[72px] md:px-8">
        <div className="size-11 animate-pulse rounded-full bg-night-900" />
        <div className="h-5 w-1/2 max-w-xs animate-pulse rounded-full bg-night-900" />
      </div>
      <div className="flex grow items-center justify-center px-4">
        <div className="aspect-square w-full max-w-[440px] animate-pulse rounded-[10px] bg-night-900 md:max-w-[560px]" />
      </div>
    </div>
  );
}

/** A friendly stop (design: States 3): the book isn't there, isn't ready, or the link was turned off. */
export function ReaderMessage({ title, body, href, cta }: { title: string; body: string; href: string; cta: string }) {
  return (
    <div role="alert" className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-paper px-6 text-center">
      <span className="flex size-24 items-center justify-center rounded-[28px] bg-night-100">
        <MoonMark className="size-14" />
      </span>
      <h1 className="text-[26px] text-night-900">{title}</h1>
      <p className="max-w-sm text-[15px] leading-relaxed text-ink-muted">{body}</p>
      <Link href={href} className={buttonClasses("solid", "lg")}>
        {cta}
      </Link>
    </div>
  );
}
