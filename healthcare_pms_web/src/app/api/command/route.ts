import { NextResponse } from "next/server";
import { hasSession } from "@/lib/auth";
import { runCommand } from "@/lib/commands";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (!hasSession(request)) return NextResponse.json({ error: "Your session expired. Sign in again." }, { status: 401 });
  try {
    const body = await request.json() as { type?: unknown; payload?: unknown };
    if (typeof body.type !== "string" || body.type.length > 64 || !body.payload || typeof body.payload !== "object" || Array.isArray(body.payload)) {
      return NextResponse.json({ error: "Invalid command payload." }, { status: 400 });
    }
    const result = await runCommand({ type: body.type, payload: body.payload as Record<string, unknown> });
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "The change could not be saved.";
    const status = /database|TURSO_DATABASE_URL|APP_ADMIN_PASSWORD|SESSION_SECRET/i.test(message) ? 503 : 400;
    return NextResponse.json({ error: message }, { status });
  }
}
