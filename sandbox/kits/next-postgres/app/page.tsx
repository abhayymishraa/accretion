"use client";

import { useEffect, useState } from "react";

type Note = { id: number; text: string; createdAt: string };

export default function Home() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const res = await fetch("/api/notes");
    setNotes(await res.json());
  }

  useEffect(() => {
    load();
  }, []);

  async function add(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const res = await fetch("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      setError((await res.json()).error);
      return;
    }
    setError("");
    setText("");
    load();
  }

  return (
    <main className="mx-auto max-w-xl p-6">
      <h1 className="mb-4 text-2xl font-semibold">Notes</h1>
      <form onSubmit={add} className="mb-6 flex gap-2">
        <label htmlFor="note" className="sr-only">New note</label>
        <input
          id="note"
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          placeholder="Write a note"
          className="flex-1 rounded border border-neutral-300 px-3 py-2"
        />
        <button className="rounded bg-neutral-900 px-4 py-2 text-white">Add</button>
      </form>
      {error && <p className="mb-4 text-red-600">{error}</p>}
      <ul className="space-y-2">
        {notes.map((note) => (
          <li key={note.id} className="rounded border border-neutral-200 px-3 py-2">
            {note.text}
          </li>
        ))}
      </ul>
    </main>
  );
}
