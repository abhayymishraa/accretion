import { Brand } from "@/components/layout/Brand";
import { ThemeToggle } from "@/components/layout/ThemeProvider";
import { Button, buttonVariants } from "@/components/ui/button";
import { LogOut, Plus } from "lucide-react";
import Link from "next/link";

interface ChatNavbarProps {
    isAuthenticated: boolean;
    onSignOut: () => void;
}

export function ChatNavbar({ isAuthenticated, onSignOut }: ChatNavbarProps) {
    return (
        <header
            // Signed in, the sidebar carries the logo, theme and sign-out wherever it shows.
            className={`ember-workspace-header ${isAuthenticated ? "md:hidden" : ""} flex h-14 shrink-0 items-center justify-between gap-4 border-b border-b-border bg-background px-4 [&_.ember-brand]:gap-2 [&_.ember-brand]:text-[17px] [&_.ember-brand]:tracking-[-0.03em] [&_.ember-brand>svg]:w-[22px] max-md:px-3 max-[381px]:gap-2`}
        >
            <Brand />
            <div className="ember-row flex items-center gap-1">
                <ThemeToggle />
                {isAuthenticated ? (
                    <Button variant="icon" onClick={onSignOut} aria-label="Sign out">
                        <LogOut size={17} />
                    </Button>
                ) : (
                    <>
                        <Link
                            href="/signin"
                            className="ember-text-link inline-flex h-8 items-center gap-2 border-0 bg-transparent px-2 text-[13px] text-muted-foreground no-underline pointer-fine:hover:text-foreground"
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
