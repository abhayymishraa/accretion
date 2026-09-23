"use client";

import { AUTH_SWITCH_LINK, AuthFrame } from "@/components/auth/AuthFrame";
import { ErrorBox } from "@/components/ui/ErrorBox";
import Link from "next/link";

import { useOAuthCallback } from "@/hooks/auth/useOAuthCallback";

export default function OAuthCallbackPage() {
    const { error } = useOAuthCallback();
    return (
        <AuthFrame
            title="Connecting your account"
            description="We’re getting your workspace ready."
        >
            {/* Renders nothing until there has been an error, then stays
                mounted so the dismissal can animate out. */}
            <ErrorBox message={error} />
            {error ? (
                <p className={AUTH_SWITCH_LINK}>
                    <Link href="/signin">Back to sign in</Link>
                </p>
            ) : (
                <p role="status">Opening your workspace…</p>
            )}
        </AuthFrame>
    );
}
