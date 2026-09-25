import { useEffect, useState, type FormEvent } from "react";

type Note = { id: number; text: string; created_at: string };

export default function App() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [text, setText] = useState("");

  const load = () =>
    fetch("/api/notes")
      .then((r) => r.json())
      .then(setNotes);

  useEffect(() => {
    load();
  }, []);

  async function add(e: FormEvent) {
    e.preventDefault();
    const res = await fetch("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (res.ok) {
      setText("");
      load();
    }
  }

  return (
    <main className="mx-auto max-w-xl p-6">
      <h1 className="mb-4 text-2xl font-semibold">Notes</h1>
      <form onSubmit={add} className="mb-6 flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          required
          placeholder="Write a note"
          className="flex-1 rounded border border-gray-300 px-3 py-2"
        />
        <button className="rounded bg-black px-4 py-2 text-white">Add</button>
      </form>
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
