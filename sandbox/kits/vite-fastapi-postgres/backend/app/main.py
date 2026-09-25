from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note
from app.schemas import NoteIn, NoteOut

app = FastAPI()
Db = Annotated[Session, Depends(get_db)]


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/notes")
def list_notes(db: Db) -> list[NoteOut]:
    notes = db.scalars(select(Note).order_by(Note.created_at.desc(), Note.id.desc()))
    return [NoteOut.model_validate(n) for n in notes]


@app.post("/api/notes", status_code=201)
def create_note(body: NoteIn, db: Db) -> NoteOut:
    note = Note(text=body.text)
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteOut.model_validate(note)
