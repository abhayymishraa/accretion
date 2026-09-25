import { desc } from "drizzle-orm";
import { db } from "@/db/index.ts";
import { notes } from "@/db/schema.ts";

export async function GET() {
  const rows = await db.select().from(notes).orderBy(desc(notes.id));
  return Response.json(rows);
}

export async function POST(request: Request) {
  const body: unknown = await request.json().catch(() => null);
  const text = body && typeof body === "object" && "text" in body ? body.text : null;
  if (typeof text !== "string" || text.trim().length < 1 || text.length > 500) {
    return Response.json({ error: "text must be 1 to 500 characters" }, { status: 400 });
  }
  const [note] = await db.insert(notes).values({ text: text.trim() }).returning();
  return Response.json(note, { status: 201 });
}
