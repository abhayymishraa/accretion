"use client";

import { Button } from "@/components/ui/button";
import { IconSwap } from "@/components/ui/IconSwap";
import { publishBusy, publishNeedsYou, usePublishStatus } from "@/hooks/publish/usePublish";
import { LoaderCircle, Rocket } from "lucide-react";

/** The one dot that says Publish wants the user, on the tab and on the phone's Workspace switch. */
export function PublishDot() {
    return (
        // Grows in from half size, never from nothing; reduced motion keeps the fade only.
        <span
            aria-hidden="true"
            className="absolute -top-0.5 -right-0.5 size-1.5 rounded-full bg-primary ring-[1.5px] ring-background [transition:opacity_200ms_var(--ease-out),scale_200ms_var(--ease-out)] starting:scale-50 starting:opacity-0 motion-reduce:starting:scale-100"
        />
    );
}

/** The workspace's Publish tab. Two signals only: a turning ring while a publish runs, and one dot when the tab
 * wants the user (a failure, a missing database, or changes not live yet). The name says which. */
export function PublishTab({
    projectId,
    revisionId,
    active,
    onSelect,
}: {
    projectId: string;
    revisionId?: string | null;
    active: boolean;
    onSelect: () => void;
}) {
    const { data } = usePublishStatus(projectId, revisionId);
    const busy = publishBusy(data);
    const attention = publishNeedsYou(data);
    let label = "Publish";
    if (busy) label = "Publish, publishing now";
    else if (attention) label = "Publish, needs attention";
    return (
        <Button variant="tab" aria-pressed={active} aria-label={label} onClick={onSelect}>
            <span className="relative">
                <IconSwap
                    swapped={busy}
                    from={<Rocket size={14} />}
                    to={
                        <LoaderCircle
                            size={14}
                            // Spins only while shown, so a hidden ring costs nothing all session.
                            className={`text-muted-foreground ${busy ? "motion-safe:animate-spin" : ""}`}
                        />
                    }
                />
                {attention && <PublishDot />}
            </span>
            Publish
        </Button>
    );
}
