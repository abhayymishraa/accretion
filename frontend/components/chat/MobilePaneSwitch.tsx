"use client";

import { PublishDot } from "@/components/publish/PublishTab";
import { Button } from "@/components/ui/button";
import { publishNeedsYou, usePublishStatus } from "@/hooks/publish/usePublish";

/** The phone's switch between the chat and the workspace. The workspace's tab row is hidden behind it, so the
 * Publish tab's dot shows on Workspace too. */
export function MobilePaneSwitch({
    pane,
    onChat,
    onWorkspace,
    projectId,
    revisionId,
}: {
    pane: string;
    onChat: () => void;
    onWorkspace: () => void;
    projectId: string;
    revisionId?: string | null;
}) {
    // The same request the Publish tab reads, so this costs no call of its own.
    const attention = publishNeedsYou(usePublishStatus(projectId, revisionId).data);
    return (
        <div
            className="hidden max-md:flex max-md:gap-1 max-md:border-b max-md:border-b-border max-md:px-3 max-md:py-1.5 max-md:[&>button]:flex-1"
            role="group"
            aria-label="Workspace view"
        >
            <Button variant="tab" aria-pressed={pane === "chat"} onClick={onChat}>
                Chat
            </Button>
            <Button
                variant="tab"
                aria-pressed={pane === "preview"}
                aria-label={attention ? "Workspace, Publish needs attention" : undefined}
                onClick={onWorkspace}
            >
                <span className="relative">
                    Workspace
                    {attention && <PublishDot />}
                </span>
            </Button>
        </div>
    );
}
