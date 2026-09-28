import createMiddleware from "next-intl/middleware";
import { NextResponse, type NextRequest } from "next/server";
import { routing } from "./i18n/routing";

const intl = createMiddleware(routing);

/**
 * /api/* is forwarded to the FastAPI service at runtime (API_INTERNAL_URL), so auth cookies stay
 * first-party on the web origin. Everything else goes through locale routing.
 */
export default function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (pathname === "/api" || pathname.startsWith("/api/")) {
    const api = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
    return NextResponse.rewrite(new URL(pathname + search, api));
  }
  return intl(request);
}

export const config = {
  matcher: ["/api/:path*", "/((?!_next|_vercel|.*\\..*).*)"],
};
