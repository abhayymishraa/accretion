import { sql } from "drizzle-orm";
import { db } from "@/db/index.ts";

export async function GET() {
  await db.execute(sql`select 1`);
  return Response.json({ ok: true });
}
