"use client";

import { useRequireSession } from "@/hooks/auth/useHasSession";
import { message } from "@/hooks/skills/useSkillLibrary";
import { githubService } from "@/services/service.github";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import useSWR from "swr";

/** The GitHub page: the user's connection, the repositories it reaches, and bringing one in as a project. */
export function useGithubAccount() {
    const hasSession = useRequireSession();
    const router = useRouter();
    const account = useSWR(hasSession ? ["/github/account"] : null, () => githubService.account());
    const reachable = Boolean(account.data?.connected && account.data.installed);
    const repos = useSWR(reachable ? ["/github/repos"] : null, () => githubService.repos());

    return {
        account: account.data ?? null,
        error: account.error
            ? message(account.error, "Could not load your GitHub connection.")
            : "",
        retry: () => account.mutate(),
        repos: repos.data ?? null,
        reposError: repos.error ? message(repos.error, "Could not list your repositories.") : "",
        retryRepos: () => repos.mutate(),
        /** Sends the browser to GitHub in this tab: in-app browsers block new windows. */
        connect: async () => {
            try {
                window.location.assign(await githubService.beginConnect());
            } catch (reason) {
                toast.error(message(reason, "Could not open GitHub."));
            }
        },
        /** Returns the error to show, or "". */
        disconnect: async () => {
            try {
                await githubService.disconnect();
                await account.mutate();
                return "";
            } catch (reason) {
                return message(reason, "Could not disconnect GitHub.");
            }
        },
        /** Makes a project from the repository and opens it; returns the error to show, or "". */
        importRepo: async (repoId: number) => {
            try {
                router.push(`/chat/${await githubService.importRepo(repoId)}`);
                return "";
            } catch (reason) {
                return message(reason, "Could not bring this repository in.");
            }
        },
    };
}
