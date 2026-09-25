import { Router } from "express";
import { desc } from "drizzle-orm";
import { db } from "../db/index.ts";
import { notes } from "../db/schema.ts";

export const router = Router();

router.get("/", async (_req, res) => {
  res.json(await db.select().from(notes).orderBy(desc(notes.id)).limit(100));
});

router.post("/", async (req, res) => {
  const text = typeof req.body?.text === "string" ? req.body.text.trim() : "";
  if (text.length < 1 || text.length > 500) {
    res.status(400).json({ error: "text must be 1 to 500 characters" });
    return;
  }
  const [note] = await db.insert(notes).values({ text }).returning();
  res.status(201).json(note);
});
