import { MongoClient } from "mongodb";

const url = process.env.MONGO_URL;
if (!url) throw new Error("MONGO_URL is not set");

export const client = new MongoClient(url);
export const db = client.db();

export type Note = { text: string; createdAt: Date };
export const notes = db.collection<Note>("notes");

// Base migration: every collection's indexes go here. createIndex is idempotent.
export async function migrate() {
  await notes.createIndex({ createdAt: -1 });
}

// `npm run migrate` runs this file directly: migrate, then exit.
if (import.meta.main) {
  await migrate();
  await client.close();
  console.log("migrate: ok");
}
