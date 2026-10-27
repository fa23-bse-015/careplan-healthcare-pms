import { NextResponse } from "next/server";
import { hasSession } from "@/lib/auth";
import { getSnapshot } from "@/lib/data";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  if (!hasSession(request)) return NextResponse.json({ error: "Sign in to view this project." }, { status: 401 });
  try {
    return NextResponse.json(await getSnapshot(), { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    const message = error instanceof Error ? error.message : "The project database is unavailable.";
    const status = /database|TURSO_DATABASE_URL|SESSION_SECRET|APP_ADMIN_PASSWORD/i.test(message) ? 503 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
