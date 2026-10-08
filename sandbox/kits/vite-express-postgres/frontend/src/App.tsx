import { useEffect, useState, type FormEvent } from "react";

type Note = { id: number; text: string; createdAt: string };

export default function App() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const res = await fetch("/api/notes");
    setNotes(await res.json());
  }

  useEffect(() => {
    load().catch(() => setError("Could not load notes"));
  }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) return setError((await res.json()).error ?? "Could not save");
    setText("");
    setError("");
    await load().catch(() => setError("Could not load notes"));
  }

  return (
    <main className="mx-auto max-w-xl p-6">
      <h1 className="mb-4 text-2xl font-semibold">Notes</h1>
      <form onSubmit={add} className="mb-6 flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          placeholder="Write a note"
          aria-label="Note text"
          className="flex-1 rounded border border-gray-300 px-3 py-2"
        />
        <button className="rounded bg-black px-4 py-2 text-white disabled:opacity-50" disabled={!text.trim()}>
          Add
        </button>
      </form>
      {error && <p className="mb-4 text-red-600">{error}</p>}
      <ul className="space-y-2">
        {notes.map((n) => (
          <li key={n.id} className="rounded border border-gray-200 p-3">
            {n.text}
          </li>
        ))}
      </ul>
    </main>
  );
}
