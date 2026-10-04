import { apiClient } from "@/lib/http/client";
import type {
    BuiltinSkillDetail,
    GitHubSkills,
    ImportResult,
    ProjectSkill,
    SkillDetail,
    SkillDraft,
    SkillSummary,
} from "@/types/skill.type";

const skillPath = (id: string) => `/skills/${encodeURIComponent(id)}`;

export const skillService = {
    list: async (): Promise<SkillSummary[]> =>
        (await apiClient.get<{ skills: SkillSummary[] }>("/skills")).data.skills,

    get: async (id: string): Promise<SkillDetail> =>
        (await apiClient.get<SkillDetail>(skillPath(id))).data,

    builtin: async (name: string): Promise<BuiltinSkillDetail> =>
        (await apiClient.get<BuiltinSkillDetail>(`/skills/builtin/${encodeURIComponent(name)}`))
            .data,

    create: async (draft: SkillDraft): Promise<SkillDetail> =>
        (await apiClient.post<SkillDetail>("/skills", draft)).data,

    // The name is fixed once created: per-project settings refer to a skill by name.
    update: async (id: string, draft: Omit<SkillDraft, "name">): Promise<SkillDetail> =>
        (await apiClient.patch<SkillDetail>(skillPath(id), draft)).data,

    remove: async (id: string): Promise<void> => {
        await apiClient.delete(skillPath(id));
    },

    // The file goes as the raw body: the API reads .md, .mdx or .zip without a multipart parser.
    importFile: async (file: File): Promise<SkillDetail> =>
        (
            await apiClient.post<SkillDetail>("/skills/import", file, {
                params: { filename: file.name },
                headers: { "Content-Type": "application/octet-stream" },
                // Up to 2 MB, which a slow phone connection can take longer than the default 30s to send.
                timeout: 120000,
            })
        ).data,

    discoverGitHub: async (url: string): Promise<GitHubSkills> =>
        (await apiClient.post<GitHubSkills>("/skills/github/discover", { url })).data,

    importGitHub: async (url: string, paths: string[]): Promise<ImportResult> =>
        (await apiClient.post<ImportResult>("/skills/github/import", { url, paths })).data,

    saveToLibrary: async (projectId: string, name: string): Promise<SkillDetail> =>
        (
            await apiClient.post<SkillDetail>(
                `/projects/${encodeURIComponent(projectId)}/skills/${encodeURIComponent(name)}/library`,
            )
        ).data,

    // On or off for every project of the account; each project's own choice is kept underneath.
    setEverywhere: async (name: string, enabled: boolean): Promise<void> => {
        await apiClient.put(`/skill-settings/${encodeURIComponent(name)}`, { enabled });
    },

    forProject: async (projectId: string): Promise<ProjectSkill[]> =>
        (
            await apiClient.get<{ skills: ProjectSkill[] }>(
                `/projects/${encodeURIComponent(projectId)}/skills`,
            )
        ).data.skills,

    setEnabled: async (projectId: string, name: string, enabled: boolean): Promise<void> => {
        await apiClient.put(
            `/projects/${encodeURIComponent(projectId)}/skills/${encodeURIComponent(name)}`,
            { enabled },
        );
    },
};
