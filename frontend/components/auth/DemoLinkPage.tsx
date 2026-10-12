"use client";

import { AUTH_SWITCH_LINK, AuthFrame } from "@/components/auth/AuthFrame";
import { ErrorBox } from "@/components/ui/ErrorBox";
import Link from "next/link";

import { useDemoLink } from "@/hooks/auth/useDemoLink";

export default function DemoLinkPage() {
    const { error } = useDemoLink();
    return (
        <AuthFrame title="Opening your demo" description="We’re getting your workspace ready.">
            <ErrorBox message={error} />
            {error ? (
                <p className={AUTH_SWITCH_LINK}>
                    <Link href="/signin">Go to sign in</Link>
                </p>
            ) : (
                <p role="status">Opening your workspace…</p>
            )}
        </AuthFrame>
    );
}
