import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  // Phase 5 performance: files in /public aren't content-hashed (Next sends max-age=0), so browsers
  // revalidate them on every page. Sample pages, the lullaby and the icon rarely change: cache a week.
  async headers() {
    const week = { key: "Cache-Control", value: "public, max-age=604800, stale-while-revalidate=86400" };
    return ["/workbooks/:path*", "/samples/:path*", "/audio/:path*", "/icon.svg"].map((source) => ({
      source,
      headers: [week],
    }));
  },
  // Addendum 9: the story pages moved from /themes to /stories (308, query strings kept)
  async redirects() {
    return [
      { source: "/:locale(ar|en)/themes", destination: "/:locale/stories", permanent: true },
      { source: "/:locale(ar|en)/themes/:slug", destination: "/:locale/stories/:slug", permanent: true },
      { source: "/themes", destination: "/stories", permanent: true },
      { source: "/themes/:slug", destination: "/stories/:slug", permanent: true },
    ];
  },
};

export default createNextIntlPlugin()(nextConfig);
