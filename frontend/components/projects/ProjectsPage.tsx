"use client";

import { buttonVariants } from "@/components/ui/button";

import { WorkspaceSidebar } from "@/components/layout/WorkspaceSidebar";
import { ProjectCollection } from "@/components/projects/ProjectCollection";
import { ProjectCollectionSkeleton } from "@/components/projects/ProjectCollectionSkeleton";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus } from "lucide-react";
import Link from "next/link";

import { useProjectsPage } from "@/hooks/projects/useProjectsPage";

export default function ProjectsPage() {
    const { hasSession, user, signOut } = useProjectsPage();
    return (
        <>
            <div className="flex min-h-dvh">
                <WorkspaceSidebar current="projects" userData={user} onSignOut={signOut} />
                <main
                    className="w-full min-w-0 flex-1 max-w-295 mx-auto pt-12 px-10 pb-25 max-md:pt-8 max-md:px-5.5 max-md:pb-[65px]"
                    id="main-content"
                >
                    <div className="flex items-center justify-between gap-7.5 mb-9.5 [&_h1]:text-[clamp(32px,_4vw,_46px)] [&_h1]:leading-[1.08] [&_h1]:tracking-[-1.8px] [&_h1]:font-medium [&_p:not(.ember-eyebrow)]:text-[14px] [&_p:not(.ember-eyebrow)]:leading-[1.7] [&_p:not(.ember-eyebrow)]:text-muted-foreground [&_p:not(.ember-eyebrow)]:mt-4 max-md:items-start max-md:flex-col max-md:gap-5">
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
                                className="flex items-center justify-between gap-5 mb-[25px]"
                                aria-hidden="true"
                            >
                                <div className="flex items-center gap-2.5 max-w-95 w-full border border-input rounded-[8px] py-2.5 px-3">
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
