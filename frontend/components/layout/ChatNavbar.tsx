import { AccountSummary } from "@/components/layout/AccountSummary";
import { Brand } from "@/components/layout/Brand";
import { ThemeToggle } from "@/components/layout/ThemeProvider";
import { Button, buttonVariants } from "@/components/ui/button";
import type { UserData } from "@/types/auth.type";
import { LogOut, Plus } from "lucide-react";
import Link from "next/link";

interface ChatNavbarProps {
    isAuthenticated: boolean;
    userData: UserData | null;
    onSignOut: () => void;
}

export function ChatNavbar({ isAuthenticated, userData, onSignOut }: ChatNavbarProps) {
    return (
        <header className="ember-workspace-header h-19 py-4 px-7 flex items-center justify-between gap-5 border-b border-b-border bg-background max-[1101px]:px-5 max-md:h-17.5 max-md:py-3.5 max-md:px-4 max-md:gap-2 max-md:[&>.ember-row]:gap-[5px] max-md:[&_.ember-button]:p-2.5 max-md:[&_.ember-button]:text-[12px] max-md:[&_.ember-brand]:text-[18px] max-md:[&_.ember-brand]:gap-[7px] max-md:[&_.ember-brand>svg]:w-5 max-md:[&_.ember-row]:gap-2 max-[381px]:gap-2 max-[381px]:px-3">
            <Brand />
            <div className="ember-row flex items-center gap-3.5">
                <ThemeToggle />
                {isAuthenticated ? (
                    <>
                        <AccountSummary userData={userData} />
                        <Button variant="icon" onClick={onSignOut} aria-label="Sign out">
                            <LogOut size={17} />
                        </Button>
                    </>
                ) : (
                    <>
                        <Link
                            href="/signin"
                            className="ember-text-link inline-flex items-center gap-2 text-[13px] bg-transparent border-0 text-secondary-foreground no-underline pointer-fine:hover:text-foreground"
                        >
                            Sign in
                        </Link>
                        <Link href="/signup" className={buttonVariants({ variant: "default" })}>
                            <Plus size={16} />
                            Sign up
                        </Link>
                    </>
                )}
            </div>
        </header>
    );
}
