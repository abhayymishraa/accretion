"use client";

import { useGithubCallback } from "@/hooks/github/useGithubCallback";
import { CallbackScreen } from "./CallbackScreen";

/** Where GitHub returns after the user installs Accretion's app and signs in. */
export function GithubCallback() {
    const { error } = useGithubCallback();
    return <CallbackScreen error={error} service="GitHub" back="/integrations/github" />;
}
