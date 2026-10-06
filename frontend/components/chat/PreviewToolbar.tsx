"use client";

import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { WorkspaceTab } from "@/hooks/chat/useWorkspaceLayout";
import { useProjectDownload } from "@/hooks/files/useProjectDownload";
import {
    BookOpen,
    Plug,
    Ellipsis,
    FileCode,
    FolderArchive,
    Globe,
    Link2,
    PanelLeft,
    Plus,
    X,
    type LucideIcon,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

type ExtraTab = Exclude<WorkspaceTab, "preview">;

// What "+" can open, in menu order.
const EXTRA_TABS: { tab: ExtraTab; label: string; icon: LucideIcon }[] = [
    { tab: "files", label: "Code", icon: FileCode },
    { tab: "skills", label: "Skills", icon: BookOpen },
    { tab: "connectors", label: "Connectors", icon: Plug },
];

/** The workspace panel's tab row, after v0: Preview stays, Code, Skills and Connectors open from "+", extras under
 * •••. */
export function PreviewToolbar({
    activeTab,
    onTabChange,
    chatHidden,
    onToggleChat,
    projectId,
    revisionId,
}: {
    activeTab: WorkspaceTab;
    onTabChange: (tab: WorkspaceTab) => void;
    chatHidden: boolean;
    onToggleChat: () => void;
    projectId: string;
    revisionId?: string | null;
}) {
    // A tab opened from elsewhere (a file in the run timeline, "Manage skills" in the composer)
    // switches to it without "+"; it stays in the row until closed.
    const [opened, setOpened] = useState<ExtraTab[]>([]);
    if (activeTab !== "preview" && !opened.includes(activeTab)) setOpened([...opened, activeTab]);
    const close = (tab: ExtraTab) => {
        setOpened(opened.filter((other) => other !== tab));
        if (activeTab === tab) onTabChange("preview");
    };
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
                {EXTRA_TABS.filter(({ tab }) => opened.includes(tab)).map(
                    ({ tab, label, icon: Icon }) => (
                        <span key={tab} className="flex items-center">
                            <Button
                                variant="tab"
                                className="pr-1.5"
                                aria-pressed={activeTab === tab}
                                onClick={() => onTabChange(tab)}
                            >
                                <Icon size={14} />
                                {label}
                            </Button>
                            <button
                                type="button"
                                aria-label={`Close ${label}`}
                                onClick={() => close(tab)}
                                className="grid size-6 cursor-pointer place-items-center rounded-[6px] text-muted-foreground [transition:background-color_130ms_ease,color_130ms_ease] focus-visible:outline-2 focus-visible:outline-ring pointer-fine:hover:bg-surface-2 pointer-fine:hover:text-foreground"
                            >
                                <X size={13} />
                            </button>
                        </span>
                    ),
                )}
            </div>
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="icon" aria-label="Open a panel tab">
                        <Plus size={15} />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-44">
                    {EXTRA_TABS.map(({ tab, label, icon: Icon }) => (
                        <DropdownMenuItem key={tab} onSelect={() => onTabChange(tab)}>
                            <Icon />
                            {label}
                        </DropdownMenuItem>
                    ))}
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
