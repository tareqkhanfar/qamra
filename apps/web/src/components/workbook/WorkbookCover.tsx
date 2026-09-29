/* eslint-disable @next/next/no-img-element -- small static preview and character images from /public */

/** Design WorkbookProduct: the book mock-up (pages fanned behind, the cover with the child's name and look). */
export function WorkbookCover({
  tone,
  title,
  line,
  character,
  binding,
}: {
  tone: string;
  title: string;
  line: string;
  character: string;
  binding: string | null;
}) {
  return (
    <div
      className={`relative mx-4 flex h-[260px] items-center justify-center overflow-hidden rounded-[24px] md:mx-0 ${tone}`}
    >
      <div className="absolute top-[34px] right-[calc(50%-38px)] h-[196px] w-[150px] rotate-[8deg] rounded-lg border border-line bg-white" />
      <div className="absolute top-[30px] right-[calc(50%-58px)] h-[196px] w-[150px] rotate-[3deg] rounded-lg border border-line bg-white" />
      <div className="relative flex h-[204px] w-[156px] flex-col items-center overflow-hidden rounded-s-[12px] rounded-e-[6px] border-s-[10px] border-amber-500 bg-night-900 pt-4 shadow-[0_12px_28px_rgba(22,32,74,0.25)]">
        <span className="px-2 text-center font-display text-[17px] leading-tight font-extrabold text-paper">
          {title}
        </span>
        <span className="mt-0.5 px-2 text-center text-[11px] font-semibold text-amber-300">{line}</span>
        <img
          src={character}
          alt=""
          width={64}
          height={128}
          decoding="async"
          className="mt-auto h-[128px] w-auto object-contain"
        />
      </div>
      {binding && (
        <span className="absolute bottom-3 left-3 rounded-full bg-paper-raised px-2.5 py-1 text-caption font-semibold">
          {binding}
        </span>
      )}
    </div>
  );
}
