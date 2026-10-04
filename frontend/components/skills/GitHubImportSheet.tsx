"use client";

import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { useGitHubImport } from "@/hooks/skills/useGitHubImport";
import type { ImportFailure } from "@/types/skill.type";
import { AnimatedList } from "@/components/ui/animated-list";
import { NumberTicker } from "@/components/ui/number-ticker";
import { useState } from "react";
import { GitHubFindLog } from "./GitHubFindLog";
import { SHEET, SHEET_HEADER, SHEET_TITLE } from "./sheet";
import { slot } from "./SkillSections";
import styles from "./skills.module.css";
import { TrustNotice } from "./TrustNotice";

function Failures({ title, items }: { title: string; items: ImportFailure[] }) {
    if (!items.length) return null;
    return (
        <details className="border-t border-border px-5 py-4 sm:px-7">
            <summary className="min-h-11 cursor-pointer content-center text-[13px] text-muted-foreground pointer-fine:min-h-0">
                {title}
            </summary>
            <ul className="mt-2 grid gap-2">
                {items.map((item) => (
                    <li key={item.path} className="text-[12.5px] leading-[1.5]">
                        <code className="block truncate font-mono text-foreground">
                            {item.path}
                        </code>
                        <span className="text-muted-foreground">{item.reason}</span>
                    </li>
                ))}
            </ul>
        </details>
    );
}

/** From GitHub: find the skills in a repository or folder, choose some, import them into the library. */
export function GitHubImportSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
    const [url, setUrl] = useState("");
    // What was searched, and a count that restarts the log for each new search.
    const [search, setSearch] = useState({ url: "", attempt: 0 });
    const { found, chosen, result, busy, error, discover, toggle, importChosen, reset } =
        useGitHubImport();
    const close = () => {
        onClose();
        reset();
        setUrl("");
        setSearch({ url: "", attempt: 0 });
    };

    return (
        <Sheet open={open} onOpenChange={(next) => !next && close()}>
            <SheetContent className={SHEET}>
                <header className={SHEET_HEADER}>
                    <SheetTitle className={SHEET_TITLE}>Import from GitHub</SheetTitle>
                    <SheetDescription className="mt-1.5 text-[13.5px] leading-[1.55]">
                        Paste a public repository or folder link. Accretion finds every SKILL.md in
                        it.
                    </SheetDescription>
                </header>
                <TrustNotice />
                <form
                    className="flex gap-2 px-5 py-5 sm:px-7"
                    onSubmit={(event) => {
                        event.preventDefault();
                        if (!url.trim() || busy) return;
                        setSearch((current) => ({ url: url.trim(), attempt: current.attempt + 1 }));
                        void discover(url.trim());
                    }}
                >
                    <label htmlFor="github-url" className="sr-only">
                        GitHub repository
                    </label>
                    <Input
                        id="github-url"
                        value={url}
                        onChange={(event) => setUrl(event.target.value)}
                        placeholder="github.com/owner/repo"
                        inputMode="url"
                        autoCapitalize="none"
                        autoCorrect="off"
                        spellCheck={false}
                        className="h-11 rounded-none font-mono"
                    />
                    <Button
                        type="submit"
                        className="h-11 rounded-none"
                        disabled={busy || !url.trim()}
                    >
                        {busy && !found ? "Finding…" : "Find skills"}
                    </Button>
                </form>
                {search.attempt > 0 && !result && (
                    <div className="px-5 pb-5 sm:px-7">
                        <GitHubFindLog
                            key={search.attempt}
                            url={search.url}
                            found={busy && !found ? null : found}
                            error={busy ? "" : error}
                        />
                    </div>
                )}
                {/* A failed import, once the list is showing; a failed search is told in the log above. */}
                <div className="px-5 sm:px-7">
                    <ErrorBox message={found ? error : ""} />
                </div>
                {result ? (
                    <section
                        className={`${styles.landed} border-t border-border px-5 py-5 sm:px-7`}
                        aria-live="polite"
                    >
                        <h3 className="text-[15px] font-semibold">
                            Imported {result.imported.length}{" "}
                            {result.imported.length === 1 ? "skill" : "skills"}
                        </h3>
                        <ul className="mt-3 flex flex-wrap gap-2">
                            {result.imported.map((skill, index) => (
                                <li
                                    key={skill.id}
                                    // Staggered for the first eight; a long import's rest arrive with the eighth.
                                    style={slot(index)}
                                    className={`${styles.arrive} ${styles.chip} px-2 py-1 font-mono text-[12px]`}
                                >
                                    /{skill.name}
                                </li>
                            ))}
                        </ul>
                        <Failures
                            title={`${result.failed.length} not imported`}
                            items={result.failed}
                        />
                        <Button className="mt-5 h-11 w-full rounded-none" onClick={close}>
                            Done
                        </Button>
                    </section>
                ) : (
                    found && (
                        <section aria-label="Skills found" className="border-t border-border">
                            <p className="px-5 pt-4 pb-2 font-mono text-[11px] tracking-[0.08em] text-muted-foreground uppercase sm:px-7">
                                <NumberTicker value={found.skills.length} /> found in{" "}
                                {found.repository}@{found.ref}
                            </p>
                            {/* Results arrive one after another, in reading order, then settle. */}
                            <AnimatedList
                                delay={40}
                                className="items-stretch gap-0 border-t border-border"
                            >
                                {found.skills.map((skill) => (
                                    <div key={skill.path} className="border-b border-border">
                                        <label className="flex min-h-11 cursor-pointer gap-3 px-5 py-3 sm:px-7 pointer-fine:hover:bg-surface-1">
                                            <input
                                                type="checkbox"
                                                checked={chosen.has(skill.path)}
                                                onChange={() => toggle(skill.path)}
                                                className="mt-1 size-4 shrink-0 accent-[var(--primary)]"
                                            />
                                            <span className="min-w-0">
                                                <span className="block truncate font-mono text-[13px] text-primary">
                                                    /{skill.name}
                                                </span>
                                                <span className="mt-0.5 line-clamp-2 text-[12.5px] leading-[1.5] text-muted-foreground">
                                                    {skill.description}
                                                </span>
                                            </span>
                                        </label>
                                    </div>
                                ))}
                            </AnimatedList>
                            <Failures
                                title={`${found.skipped.length} files can't be imported`}
                                items={found.skipped}
                            />
                            <div className="sticky bottom-0 border-t border-border bg-background px-5 py-4 sm:px-7">
                                <Button
                                    className="h-11 w-full rounded-none"
                                    disabled={busy || chosen.size === 0}
                                    onClick={() => importChosen(url.trim())}
                                >
                                    {busy
                                        ? "Importing…"
                                        : `Import ${chosen.size} ${chosen.size === 1 ? "skill" : "skills"}`}
                                </Button>
                            </div>
                        </section>
                    )
                )}
            </SheetContent>
        </Sheet>
    );
}
