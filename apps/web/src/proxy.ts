import createMiddleware from "next-intl/middleware";
import { NextRequest, NextResponse } from "next/server";
import { routing } from "./i18n/routing";

const intl = createMiddleware(routing);

/** Strict per-request CSP: scripts only with this request's nonce (Next.js applies it automatically). */
function contentSecurityPolicy(nonce: string): string {
  const dev = process.env.NODE_ENV === "development";
  const https = process.env.QAMRA_HTTPS === "1";
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    `style-src 'self' 'nonce-${nonce}'`,
    "style-src-attr 'unsafe-inline'", // React style={{…}} attributes (no script execution possible)
    "img-src 'self' blob: data:",
    "font-src 'self'",
    "media-src 'self' blob:",
    "connect-src 'self'",
    "worker-src 'self' blob:",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    ...(https ? ["upgrade-insecure-requests"] : []),
  ].join("; ");
}

/**
 * - /api/* is forwarded to the API at runtime (local dev without the nginx edge; in compose the edge
 *   routes /api straight to the API).
 * - Pages get locale routing plus a fresh CSP nonce.
 */
export default function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (pathname === "/api" || pathname.startsWith("/api/")) {
    const api = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
    return NextResponse.rewrite(new URL(pathname + search, api));
  }
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const csp = contentSecurityPolicy(nonce);
  const headers = new Headers(request.headers);
  headers.set("x-nonce", nonce);
  headers.set("Content-Security-Policy", csp);
  const response = intl(new NextRequest(request, { headers }));
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  matcher: ["/api/:path*", "/((?!_next|_vercel|audio|.*\\..*).*)"],
};
