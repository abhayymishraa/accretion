import type { Project } from "@/types/project.type";

/** What to call a project; a new one is untitled until its first request has been named. */
export const projectName = (project: Pick<Project, "title">) => project.title || "New project";

export type ProjectSort = "recent" | "newest" | "oldest" | "name-asc" | "name-desc";
export type ProjectPeriod = "all" | "7" | "30";

export function filterProjects(
    projects: readonly Project[],
    query: string,
    sort: ProjectSort,
    period: ProjectPeriod,
    now = Date.now(),
): Project[] {
    const search = query.trim().toLocaleLowerCase();
    const cutoff = now - Number(period) * 86_400_000;
    return projects
        .filter((project) => {
            if (!projectName(project).toLocaleLowerCase().includes(search)) return false;
            if (period === "all") return true;

            const created = Date.parse(project.created_at);
            return created >= cutoff && created <= now;
        })
        .sort((a, b) => {
            let order: number;
            if (sort === "name-asc" || sort === "name-desc") {
                order = projectName(a).localeCompare(projectName(b), undefined, {
                    sensitivity: "base",
                    numeric: true,
                });
                if (sort === "name-desc") order = -order;
            } else {
                const first = Date.parse(
                    sort === "recent" ? a.updated_at || a.created_at : a.created_at,
                );
                const second = Date.parse(
                    sort === "recent" ? b.updated_at || b.created_at : b.created_at,
                );
                // Unknown dates always follow known dates, regardless of direction.
                if (Number.isFinite(first) !== Number.isFinite(second))
                    return Number.isFinite(first) ? -1 : 1;
                order = Number.isFinite(first) ? first - second : 0;
                if (sort !== "oldest") order = -order;
            }
            return order || a.id.localeCompare(b.id);
        });
}
