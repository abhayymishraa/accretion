"use client";

import { buttonVariants } from "@/components/ui/button";

import { ChatNavbar } from "@/components/layout/ChatNavbar";
import { WorkspaceSidebar } from "@/components/layout/WorkspaceSidebar";
import { ProjectCollection } from "@/components/projects/ProjectCollection";
import { ProjectCollectionSkeleton } from "@/components/projects/ProjectCollectionSkeleton";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus } from "lucide-react";
import Link from "next/link";

import { useProjectsPage } from "@/hooks/projects/useProjectsPage";

export default function ProjectsPage() {
    const { ready, hasSession, user, signOut } = useProjectsPage();
    return (
        <>
            <ChatNavbar isAuthenticated={ready} userData={user} onSignOut={signOut} />
            <div className="ember-workspace-shell flex min-h-[calc(100dvh_-_76px)] [&>.ember-workspace]:flex-1 [&>.ember-workspace]:min-w-0 [&>.ember-workspace]:w-full [&>.ember-workspace]:mx-auto max-md:min-h-[calc(100dvh_-_70px)]">
                <WorkspaceSidebar current="projects" />
                <main
                    className="ember-workspace max-w-295 mx-auto pt-12 px-10 pb-25 max-md:pt-8 max-md:px-5.5 max-md:pb-[65px]"
                    id="main-content"
                >
                    <div className="ember-page-title flex items-center justify-between gap-7.5 mb-9.5 [&_h1]:text-[clamp(32px,_4vw,_46px)] [&_h1]:leading-[1.08] [&_h1]:tracking-[-1.8px] [&_h1]:font-medium [&_p:not(.ember-eyebrow)]:text-[14px] [&_p:not(.ember-eyebrow)]:leading-[1.7] [&_p:not(.ember-eyebrow)]:text-muted-foreground [&_p:not(.ember-eyebrow)]:mt-4 max-md:items-start max-md:flex-col max-md:gap-5">
                        <div>
                            <p className="ember-eyebrow uppercase tracking-[0.12em] text-[10px] font-medium text-accent-foreground mb-5.5">
                                Your workspace
                            </p>
                            <h1>Made by you.</h1>
                            <p>Your projects, ready to pick up again.</p>
                        </div>
                        <Link
                            href="/chat"
                            className={buttonVariants({
                                variant: "default",
                                className: "md:hidden",
                            })}
                        >
                            <Plus size={17} />
                            New project
                        </Link>
                    </div>
                    {hasSession ? (
                        <div data-loaded-in="">
                            <ProjectCollection />
                        </div>
                    ) : (
                        <>
                            <div
                                className="ember-project-toolbar flex items-center justify-between gap-5 mb-[25px]"
                                aria-hidden="true"
                            >
                                <div className="ember-search flex items-center gap-2.5 max-w-95 w-full border border-input rounded-[8px] py-2.5 px-3 [&_input]:w-full [&_input]:min-w-0 [&_input]:bg-transparent [&_input]:border-0 [&_input]:text-foreground [&_input]:outline-none [&_input]:text-[14px] focus-within:outline-2 focus-within:outline-solid focus-within:outline-ring focus-within:outline-offset-0.5">
                                    <Skeleton className="h-5 w-44 max-w-full" />
                                </div>
                            </div>
                            <ProjectCollectionSkeleton />
                        </>
                    )}
                </main>
            </div>
        </>
    );
}
