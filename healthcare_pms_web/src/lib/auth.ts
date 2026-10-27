import { createHmac, timingSafeEqual } from "node:crypto";

const COOKIE = "hspm_session";
const SESSION_SECONDS = 12 * 60 * 60;

function signature(value: string) {
  const secret = process.env.SESSION_SECRET;
  if (!secret || secret.length < 32) throw new Error("SESSION_SECRET must be set to at least 32 characters.");
  return createHmac("sha256", secret).update(value).digest("base64url");
}

function equal(a: string, b: string) {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left, right);
}

export function verifyPassword(candidate: string) {
  const expected = process.env.APP_ADMIN_PASSWORD;
  const minimumLength = process.env.VERCEL ? 12 : 8;
  if (!expected || expected.length < minimumLength) {
    throw new Error(`APP_ADMIN_PASSWORD must be configured with at least ${minimumLength} characters.`);
  }
  return equal(candidate, expected);
}

export function createSessionCookie() {
  const payload = String(Math.floor(Date.now() / 1000) + SESSION_SECONDS);
  const token = `${payload}.${signature(payload)}`;
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `${COOKIE}=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${SESSION_SECONDS}${secure}`;
}

export function clearSessionCookie() {
  const secure = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `${COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${secure}`;
}

export function hasSession(request: Request) {
  const cookie = request.headers.get("cookie") ?? "";
  const match = cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith(`${COOKIE}=`));
  if (!match) return false;
  const token = match.slice(COOKIE.length + 1);
  const [payload, supplied] = token.split(".");
  if (!payload || !supplied || !/^\d+$/.test(payload)) return false;
  if (Number(payload) <= Math.floor(Date.now() / 1000)) return false;
  try { return equal(signature(payload), supplied); } catch { return false; }
}
