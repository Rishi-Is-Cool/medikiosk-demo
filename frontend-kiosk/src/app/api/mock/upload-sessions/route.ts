/* MOCK document service — session creation. See mocks/uploadSessionStore.ts. */

import { NextResponse } from "next/server";
import { uploadSessions } from "@/mocks/uploadSessionStore";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as { session_id?: string; force_new?: boolean };
  return NextResponse.json(uploadSessions.create(body.session_id ?? "unknown", body.force_new ?? false));
}
