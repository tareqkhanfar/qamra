"use client";

import type { ReaderPage as Page } from "@/lib/reader";

type Props = { page: Page; title: string; dir: "rtl" | "ltr"; pageLabel: string; coverLabel: string };

function Picture({ src, alt }: { src: string; alt: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- private page picture streamed by the API (owner or share link)
    <img
      src={src}
      alt={alt}
      draggable={false}
      className="aspect-square w-full bg-night-900 object-cover select-none md:w-[min(42vw,520px)]"
    />
  );
}

/** One page of the book (design: Reader): the picture and, beside it on wide screens, the text on paper. */
export function ReaderPage({ page, title, dir, pageLabel, coverLabel }: Props) {
  const paragraphs = (page.text ?? "").split(/\n+/).filter(Boolean);
  const cover = page.beat === 0;
  return (
    <div
      dir={dir}
      className="flex w-full max-w-[440px] flex-col overflow-hidden rounded-[10px] shadow-[0_30px_80px_rgba(0,0,0,0.45)] md:w-auto md:max-w-none md:flex-row"
    >
      {page.image && <Picture src={page.image} alt={cover ? title : pageLabel} />}
      <div
        className={`flex min-h-44 w-full flex-col justify-center gap-5 bg-paper-raised px-6 py-7 text-ink md:aspect-square md:w-[min(42vw,520px)] md:gap-6 md:px-14 ${
          dir === "rtl"
            ? "bg-[linear-gradient(to_left,rgba(22,32,74,0.10),transparent_40px)]"
            : "bg-[linear-gradient(to_right,rgba(22,32,74,0.10),transparent_40px)]"
        }`}
      >
        {cover ? (
          <>
            <span className="text-caption font-semibold tracking-wide text-amber-700">{coverLabel}</span>
            <h2 className="font-display text-[28px] leading-snug font-extrabold text-night-900 md:text-[40px]">
              {title}
            </h2>
          </>
        ) : (
          paragraphs.map((text, i) => (
            <p
              key={i}
              className={
                i === 0
                  ? "font-display text-[21px] leading-[1.8] font-semibold md:text-[28px]"
                  : "text-[17px] leading-[1.8] text-ink-muted md:text-[20px]"
              }
            >
              {text}
            </p>
          ))
        )}
        {!cover && <span className="self-center text-small text-ink-muted">— {page.beat} —</span>}
      </div>
    </div>
  );
}
