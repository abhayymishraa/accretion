// A tab-scoped draft survives sign-in/sign-up without putting private prompts in URLs.
export const PROJECT_DRAFT_KEY = "accretion-project-draft";
export const STARTER_KEY = "accretion-starter";
export const MAX_PROJECT_DRAFT_LENGTH = 2000;

// Pre-rename keys, read once by migrateKey so an open tab does not lose its draft.
export const LEGACY_PROJECT_DRAFT_KEY = "webbuilder-project-draft";
export const LEGACY_STARTER_KEY = "webbuilder-starter";
