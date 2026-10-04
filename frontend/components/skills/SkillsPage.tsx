"use client";

import { WorkspaceSidebar } from "@/components/layout/WorkspaceSidebar";
import { useProjectsPage } from "@/hooks/projects/useProjectsPage";
import { useSkillLibrary } from "@/hooks/skills/useSkillLibrary";
import type { SkillSummary } from "@/types/skill.type";
import { useState } from "react";
import { toast } from "sonner";
import { type AddSkillActions, AddSkillMenu } from "./AddSkillMenu";
import { GitHubImportSheet } from "./GitHubImportSheet";
import { type SkillScope, SkillFilters } from "./SkillFilters";
import { SkillFormSheet } from "./SkillFormSheet";
import { SkillPreviewSheet } from "./SkillPreviewSheet";
import { BuiltinSkills, slot, WorkspaceSkills } from "./SkillSections";
import styles from "./skills.module.css";
import { TeachBanner } from "./TeachBanner";

/** Settings > Skills library: the user's skills, the built-in ones, and the form to add more. */
export default function SkillsPage() {
    const { user, signOut } = useProjectsPage();
    const { skills, error, retry, save, importFile, remove, setEverywhere } = useSkillLibrary();
    const [form, setForm] = useState({ open: false, target: "new", key: 0 });
    const [github, setGitHub] = useState(false);
    const [preview, setPreview] = useState<{ open: boolean; skill: SkillSummary | null }>({
        open: false,
        skill: null,
    });
    const [query, setQuery] = useState("");
    const [scope, setScope] = useState<SkillScope>("all");

    const own = skills?.filter((skill) => skill.source === "library") ?? null;
    const builtin = skills?.filter((skill) => skill.source === "builtin") ?? null;
    const counts =
        own && builtin
            ? { all: own.length + builtin.length, library: own.length, builtin: builtin.length }
            : null;
    const openPreview = (skill: SkillSummary) => setPreview({ open: true, skill });
    const openForm = (target: string) =>
        setForm((current) => ({ open: true, target, key: current.key + 1 }));
    const add: AddSkillActions = {
        onWrite: () => openForm("new"),
        onGitHub: () => setGitHub(true),
        onImportFile: async (file) => {
            const failure = await importFile(file);
            if (failure) toast.error(failure);
            else toast.success(`Imported ${file.name}`);
        },
    };

    return (
        <>
            <div className="flex min-h-dvh">
                <WorkspaceSidebar current="skills" userData={user} onSignOut={signOut} />
                <main
                    id="main-content"
                    className="mx-auto w-full max-w-[880px] min-w-0 px-4 pt-8 pb-[calc(48px+env(safe-area-inset-bottom))] sm:px-6 md:px-10 md:pt-10"
                >
                    <header
                        className={`${styles.rise} mb-8 flex flex-wrap items-end justify-between gap-x-8 gap-y-4 border-b border-border pb-6`}
                        style={slot(0)}
                    >
                        <div className="min-w-0">
                            <p className="mb-3 font-mono text-[11px] tracking-[0.1em] text-muted-foreground uppercase">
                                Settings / Skills
                            </p>
                            <h1 className="text-[28px] leading-[1.2] font-semibold tracking-[-0.6px]">
                                Skills library
                            </h1>
                            <p className="mt-2 max-w-[60ch] text-[14px] leading-[1.5] text-muted-foreground">
                                Skills are reusable instructions Accretion applies when they fit the
                                task. Yours are available in all your projects.
                            </p>
                        </div>
                        <AddSkillMenu {...add} />
                    </header>
                    <div className={styles.rise} style={slot(1)}>
                        <TeachBanner />
                    </div>
                    {!error && (
                        <SkillFilters
                            query={query}
                            onQuery={setQuery}
                            scope={scope}
                            onScope={setScope}
                            counts={counts}
                        />
                    )}
                    {!error && scope !== "builtin" && (
                        <WorkspaceSkills
                            skills={own}
                            query={query}
                            add={add}
                            onStarter={save}
                            onPreview={openPreview}
                            onEdit={openForm}
                            onDelete={remove}
                            onToggle={setEverywhere}
                        />
                    )}
                    {scope !== "library" && (
                        <BuiltinSkills
                            skills={builtin}
                            query={query}
                            error={error}
                            retry={retry}
                            onPreview={openPreview}
                            onToggle={setEverywhere}
                        />
                    )}
                </main>
            </div>
            <SkillFormSheet
                open={form.open}
                target={form.target}
                formKey={form.key}
                onClose={() => setForm((current) => ({ ...current, open: false }))}
                save={save}
            />
            <SkillPreviewSheet
                open={preview.open}
                skill={preview.skill}
                onClose={() => setPreview((current) => ({ ...current, open: false }))}
                onEdit={(id) => {
                    setPreview((current) => ({ ...current, open: false }));
                    openForm(id);
                }}
            />
            <GitHubImportSheet open={github} onClose={() => setGitHub(false)} />
        </>
    );
}
