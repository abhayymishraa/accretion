"use client";

import { PANEL_LINK } from "@/components/github/RepoStatus";
import { Button, buttonVariants } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { publishBusy, returnProject, takeReturn, usePublish } from "@/hooks/publish/usePublish";
import type { Publish } from "@/types/vercel.type";
import { ExternalLink, Rocket } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { PublishLive } from "./PublishLive";
import { PublishFailed, PublishProgress } from "./PublishProgress";

const NOTE = "text-xs leading-[1.5] text-muted-foreground";
const DATABASE = { postgres: "Neon", mongo: "MongoDB Atlas" } as const;

/** Adding the database on Vercel: where to go, what to pick, and the way back. */
function AddDatabase({
    publish,
    busy,
    onRetry,
}: {
    publish: Publish;
    busy: boolean;
    onRetry: () => void;
}) {
    const name = DATABASE[publish.database];
    return (
        <div className="grid gap-3">
            <p className="text-[13px] leading-[1.5]">
                Your app needs a database on Vercel. Add a free {name} database once, and every
                publish after this uses it.
            </p>
            <ol className="grid list-decimal gap-1.5 pl-5 text-[13px] leading-[1.5] text-muted-foreground marker:text-foreground">
                <li>Open the app&apos;s Storage page on Vercel.</li>
                <li>
                    Choose <span className="text-foreground">{name}</span>, then the free plan, then
                    Create. Keep every environment selected.
                </li>
                <li>Come back here and publish again.</li>
            </ol>
            <div className="flex flex-wrap gap-2">
                {publish.dashboard_url && (
                    <a
                        href={publish.dashboard_url}
                        target="_blank"
                        rel="noreferrer"
                        className={buttonVariants({ variant: "default" })}
                    >
                        Open Vercel
                        <ExternalLink size={14} aria-hidden="true" />
                    </a>
                )}
                <Button variant="secondary" disabled={busy} onClick={onRetry}>
                    {busy ? "Starting…" : "Publish again"}
                </Button>
            </div>
        </div>
    );
}

/** The Publish button in the workspace toolbar, and the sheet it opens. */
export function PublishSheet({
    projectId,
    disabled,
    onAskBuilder,
}: {
    projectId: string;
    // No saved app yet: nothing to publish.
    disabled: boolean;
    onAskBuilder?: (text: string) => void;
}) {
    // Back from connecting Vercel: open where the user left off. Read here, cleared by the effect below.
    const [open, setOpen] = useState(() => returnProject() === projectId);
    const project = usePublish(projectId, open);
    const { account, publish } = project;
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState("");
    // The status last shown, and whether the app went live while the user watched. Set during render, as React
    // recommends for state that follows a prop.
    const [shown, setShown] = useState(publish?.status);
    const [landed, setLanded] = useState(false);
    if (publish && publish.status !== shown) {
        setLanded(shown === "uploading" || shown === "building");
        setShown(publish.status);
    }
    useEffect(() => {
        takeReturn(projectId);
    }, [projectId]);

    const act = async (action: () => Promise<string>) => {
        setBusy(true);
        setError(await action());
        setBusy(false);
    };
    const start = () => void act(project.start);

    let body: ReactNode;
    if (project.failed && !(account && publish))
        body = (
            <ErrorBox message="Couldn't load publishing." onRetry={() => void project.retry()} />
        );
    else if (!account || !publish)
        body = <Skeleton className="h-28 rounded-[12px]" aria-label="Loading" />;
    else if (!account.configured)
        body = <p className={NOTE}>Publishing isn&apos;t available here yet.</p>;
    else if (!account.connected)
        body = (
            <div className="grid gap-4">
                <p className="text-[13px] leading-[1.5]">
                    Your app goes live on your own Vercel account, with its own link you can share.
                    Vercel is free for personal projects.
                </p>
                <ol className="grid list-decimal gap-1.5 pl-5 text-[13px] leading-[1.5] text-muted-foreground marker:text-foreground">
                    <li>Connect Vercel. Sign up there if you have no account.</li>
                    <li>Add a free {DATABASE[publish.database]} database on Vercel.</li>
                    <li>Publish, and share your link.</li>
                </ol>
                <Button disabled={busy} onClick={() => void act(project.connect)}>
                    {busy ? "Opening Vercel…" : "Connect Vercel"}
                </Button>
            </div>
        );
    else if (publishBusy(publish)) body = <PublishProgress publish={publish} />;
    else if (publish.status === "database")
        body = <AddDatabase publish={publish} busy={busy} onRetry={start} />;
    else if (publish.status === "failed")
        body = (
            <div className="grid gap-5">
                <PublishFailed
                    publish={publish}
                    busy={busy}
                    onRetry={start}
                    onAskBuilder={
                        onAskBuilder &&
                        ((text) => {
                            setOpen(false);
                            onAskBuilder(text);
                        })
                    }
                />
                {publish.url && (
                    <p className={NOTE}>
                        The last version that worked is still live at{" "}
                        <a
                            href={publish.url}
                            target="_blank"
                            rel="noreferrer"
                            className="underline"
                        >
                            {publish.url.replace(/^https:\/\//, "")}
                        </a>
                        .
                    </p>
                )}
            </div>
        );
    else if (publish.status === "live" && publish.url)
        body = (
            <PublishLive
                publish={{ ...publish, url: publish.url }}
                landed={landed}
                busy={busy}
                onUpdate={start}
                onUnpublish={project.unpublish}
            />
        );
    else
        body = (
            <div className="grid gap-4">
                <p className="text-[13px] leading-[1.5]">
                    Put this app on the web with its own link. The first time, you add a free{" "}
                    {DATABASE[publish.database]} database on Vercel.
                </p>
                <Button disabled={busy} onClick={start}>
                    {busy ? "Starting…" : "Publish"}
                </Button>
            </div>
        );

    return (
        <>
            <Button
                variant="default"
                className="h-8 px-3 text-[12.5px]"
                disabled={disabled}
                title={disabled ? "Build your app first" : undefined}
                onClick={() => setOpen(true)}
            >
                <Rocket size={14} aria-hidden="true" />
                Publish
            </Button>
            <Sheet
                open={open}
                onOpenChange={(next) => {
                    setOpen(next);
                    if (!next) {
                        setError("");
                        setLanded(false);
                    }
                }}
            >
                <SheetContent className="w-full gap-0 overflow-y-auto pb-[env(safe-area-inset-bottom)] sm:max-w-md">
                    <SheetHeader className="pt-[max(1rem,env(safe-area-inset-top))] pr-12">
                        <SheetTitle className="font-brand text-[16px] tracking-[-0.3px]">
                            Publish
                        </SheetTitle>
                        <SheetDescription className="text-[12.5px]">
                            Share your app with anyone, on your own free Vercel account.
                        </SheetDescription>
                    </SheetHeader>
                    <div className="grid gap-4 px-4 pb-6">
                        {/* A new view fades in over the old one; steps inside a running publish stay put, and
                            a card that just went live rises in on its own. */}
                        <div
                            key={`${account?.connected}:${publishBusy(publish) ? "busy" : publish?.status}`}
                            data-loaded-in={landed ? undefined : ""}
                        >
                            {body}
                        </div>
                        <ErrorBox message={error} />
                        {account?.connected &&
                            publish?.dashboard_url &&
                            publish.status !== "database" && (
                                <a
                                    href={publish.dashboard_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className={`${PANEL_LINK} border-t border-border pt-3`}
                                >
                                    Manage this app on Vercel
                                    <ExternalLink size={13} aria-hidden="true" />
                                </a>
                            )}
                    </div>
                </SheetContent>
            </Sheet>
        </>
    );
}
