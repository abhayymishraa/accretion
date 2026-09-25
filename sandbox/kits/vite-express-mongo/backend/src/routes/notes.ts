import { Router } from "express";
import { notes } from "../db.ts";

export const router = Router();

router.get("/", async (_req, res) => {
  res.json(await notes.find().sort({ createdAt: -1 }).limit(100).toArray());
});

router.post("/", async (req, res) => {
  const text = typeof req.body?.text === "string" ? req.body.text.trim() : "";
  if (text.length < 1 || text.length > 500) {
    res.status(400).json({ error: "text must be 1 to 500 characters" });
    return;
  }
  const note = { text, createdAt: new Date() };
  const { insertedId } = await notes.insertOne(note);
  res.status(201).json({ _id: insertedId, ...note });
});
