import { ldJson } from "@/lib/seo";

/** Structured data for search engines (a data block: no script runs, so the page's CSP is unaffected). */
export function JsonLd({ data }: { data: object }) {
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: ldJson(data) }} />;
}
