"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { UserData } from "@/types/auth.type";
import { Check, Pencil, ShieldAlert, ShieldCheck } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";

type Props = {
    user: UserData;
    busy: boolean;
    onSave: (name: string, bio: string) => Promise<boolean>;
};

export function ProfileIdentityCard({ user, busy, onSave }: Props) {
    const [editing, setEditing] = useState(false);
    const [name, setName] = useState(user.name);
    const [bio, setBio] = useState(user.bio || "");
    const restoreFocus = useRef(false);
    const dirty = name.trim() !== user.name || bio.trim() !== (user.bio || "");
    const initials = user.name
        .trim()
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((word) => Array.from(word)[0])
        .join("")
        .toLocaleUpperCase();
    const joined = user.created_at ? new Date(user.created_at) : null;
    const validJoined = joined && !Number.isNaN(joined.getTime());
    const VerificationIcon = user.email_verified ? ShieldCheck : ShieldAlert;

    function close() {
        restoreFocus.current = true;
        setEditing(false);
    }

    async function save(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (busy || !dirty || !name.trim()) return;
        if (await onSave(name.trim(), bio.trim())) close();
    }

    return (
        <section
            aria-label="Your profile overview"
            className="overflow-hidden border border-border bg-card"
        >
            <div className="grid sm:grid-cols-[minmax(0,1fr)_180px]">
                <div className="min-w-0 p-6 sm:p-8">
                    {editing ? (
                        <form
                            onSubmit={save}
                            aria-busy={busy}
                            className="space-y-5"
                            onKeyDown={(event) => {
                                if (event.key === "Escape" && !busy) close();
                            }}
                        >
                            <div className="space-y-2">
                                <label
                                    htmlFor="profile-name"
                                    className="text-xs text-muted-foreground"
                                >
                                    Name
                                </label>
                                <Input
                                    id="profile-name"
                                    autoFocus
                                    value={name}
                                    onChange={(event) => setName(event.target.value)}
                                    maxLength={100}
                                    required
                                    autoComplete="name"
                                    disabled={busy}
                                    className="rounded-none"
                                />
                            </div>
                            <div className="space-y-2">
                                <div className="flex items-center justify-between gap-3">
                                    <label
                                        htmlFor="profile-bio"
                                        className="text-xs text-muted-foreground"
                                    >
                                        About you (optional)
                                    </label>
                                    <span
                                        id="profile-bio-count"
                                        className="text-[11px] tabular-nums text-muted-foreground"
                                    >
                                        {bio.length}/280
                                    </span>
                                </div>
                                <textarea
                                    id="profile-bio"
                                    value={bio}
                                    onChange={(event) => setBio(event.target.value)}
                                    rows={3}
                                    maxLength={280}
                                    placeholder="What do you like to make?"
                                    disabled={busy}
                                    aria-describedby="profile-bio-count"
                                    className="block min-h-24 max-h-55 w-full resize-y rounded-none border border-input bg-card p-3 text-base leading-relaxed text-foreground placeholder:text-muted-foreground disabled:opacity-50"
                                />
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <Button
                                    type="submit"
                                    disabled={busy || !dirty || !name.trim()}
                                    className="rounded-none"
                                >
                                    <Check size={15} aria-hidden="true" />
                                    {busy ? "Saving…" : "Save changes"}
                                </Button>
                                <Button
                                    type="button"
                                    variant="secondary"
                                    disabled={busy}
                                    onClick={close}
                                    className="rounded-none"
                                >
                                    Cancel
                                </Button>
                            </div>
                        </form>
                    ) : (
                        <>
                            <h2 className="max-w-[12ch] wrap-anywhere text-[38px] leading-[1.06] font-medium tracking-[-0.04em] sm:text-[46px]">
                                {user.name}
                            </h2>
                            <p className="mt-5 max-w-[45ch] whitespace-pre-wrap wrap-anywhere text-sm leading-[1.7] text-muted-foreground">
                                {user.bio || "Add a short bio to tell a little of your story."}
                            </p>
                            <Button
                                ref={(element) => {
                                    if (element && restoreFocus.current) {
                                        restoreFocus.current = false;
                                        element.focus();
                                    }
                                }}
                                type="button"
                                variant="secondary"
                                disabled={busy}
                                className="mt-7 rounded-none"
                                onClick={() => {
                                    setName(user.name);
                                    setBio(user.bio || "");
                                    setEditing(true);
                                }}
                            >
                                <Pencil size={14} aria-hidden="true" />
                                Edit profile
                            </Button>
                        </>
                    )}
                </div>
                <div
                    className="hidden flex-col justify-between border-l border-border bg-surface-2 px-6 py-8 sm:flex"
                    aria-hidden="true"
                >
                    <span className="self-end text-[11px] font-medium tracking-[0.08em] text-muted-foreground">
                        ACCRETION
                    </span>
                    <span className="text-[78px] leading-none font-semibold tracking-[-0.04em] text-accent-foreground">
                        {initials}
                    </span>
                </div>
            </div>
            <dl className="grid border-t border-border sm:grid-cols-[minmax(0,1fr)_180px]">
                <div className="min-w-0 px-6 py-5 sm:px-8">
                    <dt className="mb-2 text-xs text-muted-foreground">Email address</dt>
                    <dd className="flex flex-wrap items-center gap-x-4 gap-y-2">
                        <span className="break-all text-sm">{user.email}</span>
                        <span
                            className={`inline-flex items-center gap-1.5 text-xs ${user.email_verified ? "text-muted-foreground" : "text-accent-foreground"}`}
                        >
                            <VerificationIcon size={14} aria-hidden="true" />
                            {user.email_verified ? "Verified" : "Not verified"}
                        </span>
                    </dd>
                </div>
                <div className="border-t border-border px-6 py-5 sm:border-t-0 sm:border-l">
                    <dt className="mb-2 text-xs text-muted-foreground">Member since</dt>
                    <dd className="text-sm">
                        {validJoined ? (
                            <time dateTime={user.created_at}>
                                {joined.toLocaleDateString(undefined, {
                                    month: "short",
                                    day: "numeric",
                                    year: "numeric",
                                })}
                            </time>
                        ) : (
                            "Not available"
                        )}
                    </dd>
                </div>
            </dl>
        </section>
    );
}
