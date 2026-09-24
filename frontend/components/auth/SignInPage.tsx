"use client";

import { AUTH_SWITCH_LINK, AuthFrame } from "@/components/auth/AuthFrame";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { SocialLogin } from "@/components/auth/SocialLogin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2 } from "lucide-react";
import Link from "next/link";

import { useEffect, useState } from "react";

import { useSignIn } from "@/hooks/auth/useSignIn";

export default function SignInPage() {
    const {
        email,
        setEmail,
        password,
        setPassword,
        isLoading,
        error,
        checkingSession,
        handleSubmit,
    } = useSignIn();

    // A loading line that paints for 80ms and vanishes is worse than no
    // loading line at all. Short session checks never render one.
    const [showChecking, setShowChecking] = useState(false);
    useEffect(() => {
        if (!checkingSession) return;
        const id = setTimeout(() => setShowChecking(true), 300);
        return () => clearTimeout(id);
    }, [checkingSession]);

    if (checkingSession) {
        return (
            <main
                data-palette="light"
                className="grid min-h-[100dvh] place-items-center bg-background px-6 text-foreground"
                aria-busy="true"
            >
                {showChecking ? (
                    <p className="text-[13px] text-muted-foreground" role="status">
                        Checking your session…
                    </p>
                ) : null}
            </main>
        );
    }

    return (
        <AuthFrame>
            <SocialLogin />
            <form
                onSubmit={handleSubmit}
                className="mt-7 flex flex-col gap-5 [&_.ember-helper]:-mt-2"
                aria-busy={isLoading}
            >
                <label className="flex flex-col gap-[9px] text-[13px]" htmlFor="email">
                    Email address
                    <Input
                        id="email"
                        type="email"
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        disabled={isLoading}
                        placeholder="you@example.com"
                    />
                </label>
                <label className="flex flex-col gap-[9px] text-[13px]" htmlFor="password">
                    Password
                    <Input
                        id="password"
                        type="password"
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        minLength={6}
                        disabled={isLoading}
                        aria-describedby="password-hint"
                    />
                </label>
                <p
                    id="password-hint"
                    className="ember-helper text-[12px] leading-[1.6] text-muted-foreground"
                >
                    Use the password for your Accretion account.
                </p>
                <ErrorBox message={error} />
                <Button type="submit" disabled={isLoading} variant="default" className="relative">
                    <span
                        className={`transition-opacity duration-[120ms] ${isLoading ? "opacity-0" : "opacity-100"}`}
                    >
                        Sign in
                    </span>
                    {/* Stacked, not swapped. aria-busy on the form already
                        announces the state, so this layer is decorative. */}
                    <span
                        aria-hidden="true"
                        className={`absolute inset-0 flex items-center justify-center gap-2 transition-opacity duration-[120ms] ${isLoading ? "opacity-100" : "opacity-0"}`}
                    >
                        <Loader2 size={16} className="animate-spin" />
                        Signing in…
                    </span>
                </Button>
            </form>
            <p className={AUTH_SWITCH_LINK}>
                <Link href="/verify-email">Verify your email</Link>
            </p>
            <p className={AUTH_SWITCH_LINK}>
                New to Accretion? <Link href="/signup">Create a workspace</Link>
            </p>
        </AuthFrame>
    );
}
