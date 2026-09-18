import { AccountSummary } from "@/components/layout/AccountSummary";
import { Brand } from "@/components/layout/Brand";
import { ThemeToggle } from "@/components/layout/ThemeProvider";
import { ProjectsList } from "@/components/projects/ProjectsList";
import { Button, buttonVariants } from "@/components/ui/button";
import type { UserData } from "@/types/auth.type";
import { ChevronLeft, Eye, EyeOff, Plus, UserRound } from "lucide-react";
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
        <header className="ember-workspace-header h-19 py-4 px-7 flex items-center justify-between gap-5 border-b border-b-border bg-background max-[1101px]:px-5 max-md:h-17.5 max-md:py-3.5 max-md:px-4 max-md:gap-2 max-md:[&>.ember-row]:gap-[5px] max-md:[&_.ember-button]:p-2.5 max-md:[&_.ember-button]:text-[12px] max-md:[&_.ember-brand]:text-[18px] max-md:[&_.ember-brand]:gap-[7px] max-md:[&_.ember-brand>svg]:w-5 max-md:[&_.ember-row]:gap-2 max-[381px]:gap-2 max-[381px]:px-3">
            <div className="ember-row flex items-center gap-3.5">
                <Button variant="icon" onClick={onBack} aria-label="Back to projects">
                    <ChevronLeft size={21} />
                </Button>
                <Brand />
            </div>
            <div className="ember-row flex items-center gap-3.5">
                <AccountSummary userData={userData} />
                <Link
                    href="/profile"
                    className={buttonVariants({ variant: "icon" })}
                    aria-label="Your profile"
                >
                    <UserRound size={18} />
                </Link>
                <ThemeToggle />
                <ProjectsList />
                <Button
                    variant="icon"
                    className="ember-preview-toggle max-md:hidden"
                    onClick={onTogglePreview}
                    aria-label={showPreview ? "Hide preview" : "Show preview"}
                    aria-pressed={showPreview}
                >
                    {showPreview ? <Eye size={18} /> : <EyeOff size={18} />}
                </Button>
                <Button variant="default" onClick={onNewChat}>
                    <Plus size={16} />
                    <span className="ember-builder-new-label max-md:hidden">New project</span>
                    <span className="sr-only md:hidden">New project</span>
                </Button>
            </div>
        </header>
    );
}
