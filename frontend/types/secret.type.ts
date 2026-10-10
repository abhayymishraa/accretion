/** A project's keys by name. A saved value is never sent back. */
export interface ProjectSecrets {
    secrets: string[];
    // The keys the platform gives the app: shown, never editable.
    managed: string[];
}
