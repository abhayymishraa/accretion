import express from "express";
import { sql } from "drizzle-orm";
import { db } from "./db/index.ts";
import { router as notes } from "./routes/notes.ts";

const app = express();
app.use(express.json());

app.get("/api/health", async (_req, res) => {
  await db.execute(sql`select 1`);
  res.json({ ok: true });
});
app.use("/api/notes", notes);

// Migrations run from the host (`npm run migrate`), never at startup, so a change that deletes
// data waits for the user's approval.
app.listen(4000, "0.0.0.0", () => console.log("api listening on 4000"));
