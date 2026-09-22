// The product was renamed from WebBuilder to Accretion, so every stored key moved
// with it. Without this, the rename would silently reset saved themes and discard
// prompts a visitor typed before signing in.
export function migrateKey(storage: Storage, nextKey: string, legacyKey: string) {
    try {
        if (storage.getItem(nextKey) !== null) return;
        const legacy = storage.getItem(legacyKey);
        if (legacy === null) return;
        storage.setItem(nextKey, legacy);
        storage.removeItem(legacyKey);
    } catch {
        // Blocked or full storage: callers already fall back to their defaults.
    }
}
