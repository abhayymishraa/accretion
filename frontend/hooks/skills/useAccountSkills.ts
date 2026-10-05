"use client";

import { skillService } from "@/services/service.skills";
import type { ProjectSkill } from "@/types/skill.type";
import { useState } from "react";
import useSWR from "swr";

/**
 * The skills a new project starts with: built-in and library skills not turned off for the whole
 * account. Fetched the first time the "/" menu opens, under the library page's key, so either fills
 * the other's cache.
 */
export function useAccountSkills() {
    const [wanted, setWanted] = useState(false);
    const { data } = useSWR(wanted ? ["/skills"] : null, () => skillService.list());
    const skills: ProjectSkill[] | null = data
        ? data
              .filter((skill) => !skill.off_everywhere)
              .map((skill) => ({ ...skill, enabled: true, in_library: false }))
        : null;
    return { skills, ensureLoaded: () => setWanted(true) };
}
