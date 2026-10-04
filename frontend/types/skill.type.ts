type SkillSource = "builtin" | "library" | "project";

export interface SkillSummary {
    name: string;
    description: string;
    source: SkillSource;
    // Library skills only.
    id?: string | null;
    // Built-in skills only: a platform skill that stays on in every project, and where the menus
    // file it. Built-ins arrive grouped in this order.
    required: boolean;
    category: string | null;
    subcategory: string | null;
    // Turned off for the whole account, so no project can use it.
    off_everywhere: boolean;
}

export interface ProjectSkill extends SkillSummary {
    enabled: boolean;
    // Project skills only: the library already has a skill of this name.
    in_library: boolean;
}

export interface SkillDetail extends SkillDraft {
    id: string;
}

export interface BuiltinSkillDetail {
    name: string;
    description: string;
    instructions: string;
}

export interface SkillDraft {
    name: string;
    description: string;
    instructions: string;
}

export interface ImportFailure {
    path: string;
    reason: string;
}

interface FoundSkill {
    path: string;
    name: string;
    description: string;
}

export interface GitHubSkills {
    repository: string;
    ref: string;
    skills: FoundSkill[];
    skipped: ImportFailure[];
}

export interface ImportResult {
    imported: SkillDetail[];
    failed: ImportFailure[];
}
