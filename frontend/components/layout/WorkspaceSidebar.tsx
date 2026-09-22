import { buttonVariants } from "@/components/ui/button";
import { FolderOpen, Plus, UserRound } from "lucide-react";
import Link from "next/link";

export function WorkspaceSidebar({
    current,
}: {
    current: "new" | "projects" | "builder" | "profile";
}) {
    return (
        <aside className="ember-workspace-sidebar flex w-[212px] shrink-0 flex-col gap-5 border-r border-r-border bg-background px-3 py-4 [&_nav]:flex [&_nav]:flex-col [&_nav]:gap-0.5 [&_nav_a]:flex [&_nav_a]:min-h-9 [&_nav_a]:items-center [&_nav_a]:gap-2.5 [&_nav_a]:rounded-[8px] [&_nav_a]:px-2.5 [&_nav_a]:text-[12.5px] [&_nav_a]:text-muted-foreground [&_nav_a]:[transition:background-color_130ms_ease,color_130ms_ease] [&_nav_a[aria-current=page]]:bg-accent [&_nav_a[aria-current=page]]:text-accent-foreground pointer-fine:[&_nav_a:hover]:bg-surface-2 pointer-fine:[&_nav_a:hover]:text-foreground [&>div]:mt-auto [&>div]:px-2.5 [&>div]:py-3 [&_p]:text-[12px] [&_p]:text-muted-foreground [&_span]:mt-1.5 [&_span]:block [&_span]:text-[10.5px] [&_span]:leading-[1.6] [&_span]:text-muted-foreground/70 max-[1101px]:w-[180px] max-md:hidden">
            <Link
                href="/chat"
                className={buttonVariants({ variant: "default" })}
                aria-current={current === "new" ? "page" : undefined}
            >
                <Plus size={15} />
                New project
            </Link>
            <nav aria-label="Workspace navigation">
                <Link href="/projects" aria-current={current === "projects" ? "page" : undefined}>
                    <FolderOpen size={15} />
                    Projects
                </Link>
                <Link href="/profile" aria-current={current === "profile" ? "page" : undefined}>
                    <UserRound size={15} />
                    Profile
                </Link>
            </nav>
            <div>
                <p>Your ideas, your code.</p>
                <span>Make something worth opening.</span>
            </div>
        </aside>
    );
}
