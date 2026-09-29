import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
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
