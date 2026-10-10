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
    KeyRound,
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
    { tab: "secrets", label: "Keys", icon: KeyRound },
];

/** The workspace panel's tab row: Preview stays, Code, Skills, Connectors and Keys open from "+",
 * extras under •••. */
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
        <div className="flex h-11 shrink-0 items-center gap-0.5 border-b border-b-border bg-background px-2 max-md:px-1.5">
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
                        <span
                            key={tab}
                            className="flex origin-left items-center [transition:opacity_150ms_var(--ease-out),scale_150ms_var(--ease-out)] starting:scale-[0.97] starting:opacity-0 motion-reduce:starting:scale-100"
                        >
                            <Button
                                variant="tab"
                                className="pr-1.5 pointer-coarse:pr-2.5"
                                aria-pressed={activeTab === tab}
                                onClick={() => onTabChange(tab)}
                            >
                                <Icon size={14} />
                                {label}
                            </Button>
                            {/* 24px to see; on touch the hit area spills out to 44px. */}
                            <Button
                                variant="icon"
                                aria-label={`Close ${label}`}
                                onClick={() => close(tab)}
                                className="relative size-6 rounded-[6px] pointer-coarse:size-6 pointer-coarse:after:absolute pointer-coarse:after:-inset-2.5"
                            >
                                <X size={13} />
                            </Button>
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
