"use client";

import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDown, FileArchive, PenLine, Plus } from "lucide-react";
import { useRef } from "react";
import { SiGithub } from "react-icons/si";

const ITEM = "min-h-11 gap-3 rounded-none px-3 text-[13.5px] pointer-fine:min-h-9 [&_svg]:size-4";

export interface AddSkillActions {
    onWrite: () => void;
    onGitHub: () => void;
    onImportFile: (file: File) => void;
}

/** "Add skill" with its three sources: write one, find them in a GitHub repository, or upload a file. */
export function AddSkillMenu({ onWrite, onGitHub, onImportFile }: AddSkillActions) {
    const picker = useRef<HTMLInputElement>(null);
    return (
        <>
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button className="rounded-none">
                        <Plus size={16} />
                        Add skill
                        <ChevronDown size={14} className="-mr-1 opacity-80" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-60 rounded-none p-0">
                    <DropdownMenuItem className={ITEM} onSelect={onWrite}>
                        <PenLine />
                        Write manually
                    </DropdownMenuItem>
                    <DropdownMenuItem className={ITEM} onSelect={onGitHub}>
                        <SiGithub />
                        From GitHub
                    </DropdownMenuItem>
                    <DropdownMenuItem className={ITEM} onSelect={() => picker.current?.click()}>
                        <FileArchive />
                        Import from file
                        <span className="ml-auto font-mono text-[10px] tracking-[0.08em] text-muted-foreground uppercase">
                            .md .zip
                        </span>
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
            <input
                ref={picker}
                type="file"
                accept=".md,.mdx,.zip"
                className="sr-only"
                tabIndex={-1}
                aria-hidden="true"
                onChange={(event) => {
                    const file = event.target.files?.[0];
                    // Cleared so choosing the same file again still fires a change.
                    event.target.value = "";
                    if (file) onImportFile(file);
                }}
            />
        </>
    );
}
