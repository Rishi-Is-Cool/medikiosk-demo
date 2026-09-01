/* MOCK document service — the phone announcing that it opened the link. */

import { NextResponse } from "next/server";
import { uploadSessions } from "@/mocks/uploadSessionStore";

export const dynamic = "force-dynamic";

export async function POST(_request: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const session = uploadSessions.connect(token);

  if (!session) {
    return NextResponse.json({ error: "expired_or_unknown" }, { status: 410 });
  }

  return NextResponse.json(session);
}
