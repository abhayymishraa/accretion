"use client";

import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useProjectDownload } from "@/hooks/files/useProjectDownload";
import { Ellipsis, FileCode, FolderArchive, Globe, Link2, PanelLeft, Plus, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

type TabType = "preview" | "files";

/** The workspace panel's tab row, after v0: Preview stays, Code opens from "+", extras under •••. */
export function PreviewToolbar({
    activeTab,
    onTabChange,
    chatHidden,
    onToggleChat,
    projectId,
    revisionId,
}: {
    activeTab: TabType;
    onTabChange: (tab: TabType) => void;
    chatHidden: boolean;
    onToggleChat: () => void;
    projectId: string;
    revisionId?: string | null;
}) {
    // A file opened from the run timeline switches to Code, which shows the tab without "+".
    const [codeOpen, setCodeOpen] = useState(false);
    const showCode = codeOpen || activeTab === "files";
    const { isDownloading, handleDownloadAll } = useProjectDownload(projectId, revisionId);
    const copyLink = () =>
        navigator.clipboard.writeText(window.location.href).then(
            () => toast.success("Link copied"),
            () => toast.error("Could not copy the link"),
        );
    return (
        <div className="ember-preview-toolbar flex h-11 shrink-0 items-center gap-0.5 border-b border-b-border bg-background px-2 max-md:px-1.5">
            <Button
                variant="icon"
                className="max-md:hidden"
                aria-label={chatHidden ? "Show conversation" : "Hide conversation"}
                aria-pressed={chatHidden}
                onClick={onToggleChat}
            >
                <PanelLeft size={15} />
            </Button>
            <div className="flex min-w-0 items-center gap-0.5" role="group" aria-label="Panel tabs">
                <Button
                    variant="tab"
                    aria-pressed={activeTab === "preview"}
                    onClick={() => onTabChange("preview")}
                >
                    <Globe size={14} />
                    Preview
                </Button>
                {showCode && (
                    <span className="flex items-center">
                        <Button
                            variant="tab"
                            className="pr-1.5"
                            aria-pressed={activeTab === "files"}
                            onClick={() => onTabChange("files")}
                        >
                            <FileCode size={14} />
                            Code
                        </Button>
                        <button
                            type="button"
                            aria-label="Close Code"
                            onClick={() => {
                                setCodeOpen(false);
                                onTabChange("preview");
                            }}
                            className="grid size-6 cursor-pointer place-items-center rounded-[6px] text-muted-foreground [transition:background-color_130ms_ease,color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-2 pointer-fine:hover:text-foreground"
                        >
                            <X size={13} />
                        </button>
                    </span>
                )}
            </div>
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="icon" aria-label="Open a panel tab">
                        <Plus size={15} />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-44">
                    <DropdownMenuItem
                        onSelect={() => {
                            setCodeOpen(true);
                            onTabChange("files");
                        }}
                    >
                        <FileCode />
                        Code
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="icon" className="ml-auto" aria-label="Project actions">
                        <Ellipsis size={15} />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem onSelect={copyLink}>
                        <Link2 />
                        Copy link
                    </DropdownMenuItem>
                    <DropdownMenuItem
                        disabled={isDownloading}
                        onSelect={() =>
                            handleDownloadAll().then(
                                (ok) => ok || toast.error("Could not download the project ZIP"),
                            )
                        }
                    >
                        <FolderArchive />
                        Download ZIP
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    );
}
