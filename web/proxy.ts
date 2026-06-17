import { NextRequest, NextResponse } from "next/server";

const COOKIE = "svitch_auth";

export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Let the login page and non-dashboard routes through
  if (!pathname.startsWith("/dashboard") || pathname === "/dashboard/login") {
    return NextResponse.next();
  }

  const cookie = req.cookies.get(COOKIE);
  const expected = process.env.DASHBOARD_PASSWORD;

  // If no password is configured, allow access (local dev with no env set)
  if (!expected) return NextResponse.next();

  if (!cookie || cookie.value !== expected) {
    return NextResponse.redirect(new URL("/dashboard/login", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};
