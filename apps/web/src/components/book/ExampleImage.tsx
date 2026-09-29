import { RATIO, type ExamplePage } from "@/lib/examples";

/**
 * A page of a published example: watermarked web copies from the API (same origin), in two sizes, lazy by
 * default. Width and height are set so nothing jumps while it loads.
 */
export function ExampleImage({
  page,
  alt,
  sizes,
  priority = false,
  className = "",
}: {
  page: Pick<ExamplePage, "image" | "thumb" | "aspect">;
  alt: string;
  sizes: string;
  priority?: boolean;
  className?: string;
}) {
  const height = Math.round(1280 / RATIO[page.aspect]);
  return (
    // eslint-disable-next-line @next/next/no-img-element -- fixed-size watermarked copies from our own API
    <img
      src={page.image}
      srcSet={`${page.thumb} 560w, ${page.image} 1280w`}
      sizes={sizes}
      width={1280}
      height={height}
      alt={alt}
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : "auto"}
      decoding="async"
      draggable={false}
      className={className}
    />
  );
}
