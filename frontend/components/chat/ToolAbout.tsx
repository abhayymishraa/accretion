"use client";

import { buttonVariants } from "@/components/ui/button";
import { useToolAbout } from "@/hooks/chat/useToolAbout";
import type { presentTool } from "@/lib/tool-presentation";
import Link from "next/link";
import { useParams } from "next/navigation";

/** An opened skill or service row: what the skill is for, or what the service's tool does, and where to manage it. */
export function ToolAbout({ result }: { result: ReturnType<typeof presentTool> }) {
    const { id: projectId = "" } = useParams<{ id?: string }>();
    const about = useToolAbout(projectId, result.skill, result.service, result.toolName);
    const description = result.skill
        ? about.skill?.description
        : about.tool?.description || about.server?.description;
    const missing = result.skill
        ? "This skill is no longer in this project."
        : "This service is no longer connected.";
    return (
        <div className="grid justify-items-start gap-1.5 py-1">
            <p className="text-[12.5px] font-medium text-foreground">
                {result.skill || about.server?.title || result.service}
                {result.toolName && (
                    <span className="ml-1.5 font-mono text-[11.5px] font-normal text-muted-foreground">
                        {result.toolName}
                    </span>
                )}
            </p>
            <p className="max-h-48 overflow-y-auto overscroll-contain whitespace-pre-line text-[12.5px] leading-relaxed text-muted-foreground">
                {description ||
                    (about.loading
                        ? "Loading details…"
                        : about.failed
                          ? "Could not load details."
                          : missing)}
            </p>
            <Link
                href={
                    result.skill ? "/skills" : `/connectors/${encodeURIComponent(result.service)}`
                }
                className={buttonVariants({ variant: "utility" })}
            >
                {result.skill ? "Manage skills" : `Manage ${about.server?.title || result.service}`}
            </Link>
        </div>
    );
}
