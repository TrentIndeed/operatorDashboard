import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Public pages that don't require auth
const PUBLIC_PATHS = ["/landing", "/login", "/signup", "/pricing"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow static assets
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // Allow public pages
  if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    return NextResponse.next();
  }

  // Check for auth cookie
  const token = request.cookies.get("operator_token")?.value;

  // Root path: redirect to landing if not logged in, dashboard if logged in
  if (pathname === "/") {
    if (token) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return NextResponse.redirect(new URL("/landing", request.url));
  }

  // Protected pages: redirect to landing if not logged in
  if (!token) {
    return NextResponse.redirect(new URL("/landing", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
