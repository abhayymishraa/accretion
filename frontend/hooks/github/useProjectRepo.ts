"use client";

import { message } from "@/hooks/skills/useSkillLibrary";
import { githubService } from "@/services/service.github";
import type { ProjectRepo } from "@/types/github.type";
import useSWR from "swr";

// While GitHub work runs in the background, the status is read again this often.
const BUSY_POLL_MS = 4000;
export const repoBusy = (repo?: ProjectRepo) =>
    repo?.status === "pushing" || repo?.status === "pulling";

/** A project's GitHub status line. The header and the GitHub tab share it, so it is fetched once. */
export function useRepoStatus(projectId: string) {
    return useSWR(["/projects", projectId, "repo"] as const, ([, id]) => githubService.repo(id), {
        refreshInterval: (latest) => (repoBusy(latest) ? BUSY_POLL_MS : 0),
    });
}

/** The GitHub tab: the project's repository, and every change to it. Each change returns the error to show, or "". */
export function useProjectRepo(projectId: string) {
    const repo = useRepoStatus(projectId);
    const account = useSWR(["/github/account"], () => githubService.account());

    async function run(write: () => Promise<ProjectRepo | void>, fallback: string) {
        try {
            const next = await write();
            if (next) await repo.mutate(next, { revalidate: false });
            else await repo.mutate();
            return "";
        } catch (reason) {
            return message(reason, fallback);
        }
    }

    return {
        repo: repo.data ?? null,
        account: account.data ?? null,
        failed: Boolean(repo.error || account.error),
        retry: () => Promise.all([repo.mutate(), account.mutate()]),
        create: (name?: string) =>
            run(() => githubService.createRepo(projectId, name), "Could not save to GitHub."),
        sync: () => run(() => githubService.sync(projectId), "Could not sync now."),
        approve: () =>
            run(() => githubService.approveWorkflows(projectId), "Could not approve the file."),
        unlink: () =>
            run(async () => {
                await githubService.unlink(projectId);
            }, "Could not unlink the repository."),
        createBranch: (name: string) =>
            run(() => githubService.createBranch(projectId, name), "Could not make the branch."),
        switchBranch: (name: string) =>
            run(() => githubService.switchBranch(projectId, name), "Could not switch branch."),
    };
}

/** The repository's branches, read only once "More" opens, and opening a pull request. */
export function useRepoBranches(projectId: string, wanted: boolean) {
    const branches = useSWR(
        wanted ? (["/projects", projectId, "repo", "branches"] as const) : null,
        ([, id]) => githubService.branches(id),
    );
    return {
        branches: branches.data ?? null,
        failed: Boolean(branches.error),
        reload: () => branches.mutate(),
        /** Returns the pull request's address, or an error to show. */
        openPull: async (): Promise<{ url: string } | { error: string }> => {
            try {
                return { url: await githubService.openPull(projectId) };
            } catch (reason) {
                return { error: message(reason, "Could not open a pull request.") };
            }
        },
    };
}
