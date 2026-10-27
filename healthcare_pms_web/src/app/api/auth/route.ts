import { NextResponse } from "next/server";
import { clearSessionCookie, createSessionCookie, hasSession, verifyPassword } from "@/lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const failedLogins = new Map<string, { count: number; startedAt: number }>();

export async function GET(request: Request) {
  return NextResponse.json({ authenticated: hasSession(request) });
}

export async function POST(request: Request) {
  try {
    const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "local";
    const now = Date.now();
    const attempts = failedLogins.get(ip);
    if (attempts && now - attempts.startedAt < 15 * 60 * 1000 && attempts.count >= 10) {
      return NextResponse.json({ error: "Too many sign-in attempts. Wait 15 minutes and try again." }, { status: 429 });
    }
    if (attempts && now - attempts.startedAt >= 15 * 60 * 1000) failedLogins.delete(ip);
    const body = await request.json() as { password?: unknown };
    if (typeof body.password !== "string" || body.password.length < 1 || body.password.length > 256) {
      return NextResponse.json({ error: "Enter the app access password." }, { status: 400 });
    }
    if (!verifyPassword(body.password)) {
      const current = failedLogins.get(ip);
      failedLogins.set(ip, current ? { count: current.count + 1, startedAt: current.startedAt } : { count: 1, startedAt: now });
      return NextResponse.json({ error: "That password did not match." }, { status: 401 });
    }
    failedLogins.delete(ip);
    const response = NextResponse.json({ authenticated: true });
    response.headers.set("Set-Cookie", createSessionCookie());
    return response;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Sign in could not be completed.";
    return NextResponse.json({ error: message }, { status: 503 });
  }
}

export async function DELETE() {
  const response = NextResponse.json({ authenticated: false });
  response.headers.set("Set-Cookie", clearSessionCookie());
  return response;
}
