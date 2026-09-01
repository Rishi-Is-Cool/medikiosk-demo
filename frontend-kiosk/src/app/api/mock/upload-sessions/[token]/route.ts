/* MOCK document service — session status polling. */

import { NextResponse } from "next/server";
import { uploadSessions } from "@/mocks/uploadSessionStore";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const session = uploadSessions.get(token);

  if (!session) {
    return NextResponse.json({ error: "unknown_session" }, { status: 404 });
  }

  return NextResponse.json(session, {
    headers: { "Cache-Control": "no-store" },
  });
}
