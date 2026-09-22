import { AccountSummary } from "@/components/layout/AccountSummary";
import { Brand } from "@/components/layout/Brand";
import { ThemeToggle } from "@/components/layout/ThemeProvider";
import { ProjectsList } from "@/components/projects/ProjectsList";
import { Button, buttonVariants } from "@/components/ui/button";
import type { UserData } from "@/types/auth.type";
import { ChevronLeft, PanelRight, Plus, UserRound } from "lucide-react";
import Link from "next/link";

interface ChatIdHeaderProps {
    userData: UserData | null;
    showPreview: boolean;
    onTogglePreview: () => void;
    onNewChat: () => void;
    onBack: () => void;
}

export function ChatIdHeader({
    userData,
    showPreview,
    onTogglePreview,
    onNewChat,
    onBack,
}: ChatIdHeaderProps) {
    return (
        <header className="ember-workspace-header flex h-14 shrink-0 items-center justify-between gap-4 border-b border-b-border bg-background px-4 [&_.ember-brand]:gap-2 [&_.ember-brand]:text-[17px] [&_.ember-brand]:tracking-[-0.03em] [&_.ember-brand>svg]:w-[22px] max-md:px-3 max-[381px]:gap-2">
            <div className="ember-row flex min-w-0 items-center gap-2">
                <Button variant="icon" onClick={onBack} aria-label="Back to projects">
                    <ChevronLeft size={18} />
                </Button>
                <Brand />
            </div>
            <div className="ember-row flex items-center gap-1">
                <AccountSummary userData={userData} />
                <ProjectsList />
                <Link
                    href="/profile"
                    className={buttonVariants({ variant: "icon" })}
                    aria-label="Your profile"
                >
                    <UserRound size={17} />
                </Link>
                <ThemeToggle />
                <Button
                    variant="icon"
                    className="ember-preview-toggle max-md:hidden"
                    onClick={onTogglePreview}
                    aria-label={showPreview ? "Hide workspace panel" : "Show workspace panel"}
                    aria-pressed={showPreview}
                >
                    <PanelRight size={17} />
                </Button>
                <Button variant="default" className="ml-2" onClick={onNewChat}>
                    <Plus size={15} />
                    <span className="ember-builder-new-label max-md:hidden">New project</span>
                    <span className="sr-only md:hidden">New project</span>
                </Button>
            </div>
        </header>
    );
}
