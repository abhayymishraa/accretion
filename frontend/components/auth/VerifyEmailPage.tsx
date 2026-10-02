"use client";

import { Button } from "@/components/ui/button";

import { AUTH_SWITCH_LINK, AuthFrame } from "@/components/auth/AuthFrame";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { Input } from "@/components/ui/input";
import Link from "next/link";

import { useEmailVerification } from "@/hooks/auth/useEmailVerification";

export default function VerifyEmailPage() {
    const { token, email, setEmail, ready, busy, message, error, confirm, requestVerification } =
        useEmailVerification();
    return (
        <AuthFrame title="Verify your email" description="One small step before your next idea.">
            {!ready ? (
                <p role="status">Opening verification…</p>
            ) : token ? (
                <div className="ember-form flex flex-col gap-[21px] mt-7.5 [&_.ember-helper]:-mt-3">
                    <p>Confirm your email and sign in to Accretion.</p>
                    <Button type="button" variant="default" disabled={busy} onClick={confirm}>
                        {busy ? "Signing in…" : "Continue"}
                    </Button>
                </div>
            ) : (
                <form
                    className="ember-form flex flex-col gap-[21px] mt-7.5 [&_.ember-helper]:-mt-3"
                    onSubmit={requestVerification}
                >
                    <label
                        className="flex flex-col gap-[9px] text-[13px]"
                        htmlFor="verification-email"
                    >
                        Account email
                        <Input
                            id="verification-email"
                            type="email"
                            autoComplete="email"
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}
                            required
                            disabled={busy}
                        />
                    </label>
                    <Button type="submit" variant="default" disabled={busy}>
                        {busy ? "Sending…" : "Send verification link"}
                    </Button>
                </form>
            )}
            {message && (
                <p
                    role="status"
                    className="ember-helper text-[12px] leading-[1.6] text-muted-foreground mt-4"
                >
                    {message}
                </p>
            )}
            <div className="mt-4">
                <ErrorBox message={error} />
            </div>
            <p className={AUTH_SWITCH_LINK}>
                <Link href="/signin">Back to sign in</Link>
            </p>
        </AuthFrame>
    );
}
