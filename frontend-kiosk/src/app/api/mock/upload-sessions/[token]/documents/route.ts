/* MOCK document service — receiving a document from the patient's phone.

   The bytes are measured and discarded on purpose (build spec §11): the real
   service streams them to object storage. Keeping them in a Node process
   would encourage the wrong architecture downstream. */

import { NextResponse } from "next/server";
import { uploadSessions } from "@/mocks/uploadSessionStore";

export const dynamic = "force-dynamic";

const MAX_BYTES = 12 * 1024 * 1024;
const ALLOWED = [
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
  "application/pdf",
];

export async function POST(request: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;

  const form = await request.formData().catch(() => null);
  const file = form?.get("file");

  if (!(file instanceof File)) {
    return NextResponse.json({ error: "no_file" }, { status: 400 });
  }

  if (file.size > MAX_BYTES) {
    return NextResponse.json({ error: "too_large" }, { status: 413 });
  }

  const mime = file.type?.toLowerCase() || "";
  // HEIC from iPhones sometimes arrives with an empty type; accept it rather
  // than blocking a patient over a MIME-sniffing quirk.
  if (mime && !ALLOWED.includes(mime)) {
    return NextResponse.json({ error: "unsupported_type" }, { status: 415 });
  }

  const result = uploadSessions.addDocument(token, { name: file.name, size: file.size });

  if (result === "unknown") {
    return NextResponse.json({ error: "unknown_session" }, { status: 404 });
  }
  if (result === "expired") {
    return NextResponse.json({ error: "expired" }, { status: 410 });
  }

  return NextResponse.json(result);
}
