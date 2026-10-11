import { ProjectTitle } from "@/components/chat/ProjectTitle";
import { RepoStatus } from "@/components/github/RepoStatus";

/** The bar atop the conversation: the project's name, and its GitHub status once it saves there. */
export function ProjectBar({
    projectId,
    revisionId,
}: {
    projectId: string;
    revisionId?: string | null;
}) {
    return (
        <div className="flex h-11 shrink-0 items-center border-b border-b-border bg-background px-3 max-md:hidden">
            <ProjectTitle projectId={projectId} revisionId={revisionId} />
            <RepoStatus projectId={projectId} />
        </div>
    );
}
