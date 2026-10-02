"use client";

import { AUTH_SWITCH_LINK, AuthFrame } from "@/components/auth/AuthFrame";
import { ErrorBox } from "@/components/ui/ErrorBox";
import { SocialLogin } from "@/components/auth/SocialLogin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2 } from "lucide-react";
import Link from "next/link";

import { useSignUp } from "@/hooks/auth/useSignUp";

export default function SignUpPage() {
    const {
        name,
        setName,
        email,
        setEmail,
        password,
        setPassword,
        isLoading,
        error,
        options,
        setOptions,
        registered,
        handleSubmit,
    } = useSignUp();
    if (registered)
        return (
            <AuthFrame signup>
                <p role="status">
                    You&apos;re on the waitlist. We sent a link to {email}: open it within 30
                    minutes to confirm your spot. We&apos;ll email you again when you&apos;re in.
                </p>
                <p className={AUTH_SWITCH_LINK}>
                    <Link href="/verify-email">Resend verification email</Link>
                </p>
            </AuthFrame>
        );

    return (
        <AuthFrame signup>
            <SocialLogin registration onOptions={setOptions} />
            <form
                onSubmit={handleSubmit}
                className="mt-7 flex flex-col gap-5 [&_.ember-helper]:-mt-2"
                aria-busy={isLoading}
            >
                <label className="flex flex-col gap-[9px] text-[13px]" htmlFor="name">
                    Your name
                    <Input
                        id="name"
                        autoComplete="name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        required
                        disabled={isLoading}
                        placeholder="Your name"
                    />
                </label>
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
                        autoComplete="new-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        minLength={8}
                        maxLength={256}
                        disabled={isLoading}
                        aria-describedby="password-hint"
                    />
                </label>
                <p
                    id="password-hint"
                    className="ember-helper text-[12px] leading-[1.6] text-muted-foreground"
                >
                    Use at least 8 characters. New accounts join the waitlist automatically.
                </p>
                <ErrorBox message={error} />
                <Button
                    type="submit"
                    disabled={isLoading || !options?.email_verification}
                    variant="default"
                    className="relative"
                >
                    <span
                        className={`transition-opacity duration-[120ms] ${isLoading ? "opacity-0" : "opacity-100"}`}
                    >
                        Create workspace
                    </span>
                    {/* Stacked, not swapped. aria-busy on the form already
                        announces the state, so this layer is decorative. */}
                    <span
                        aria-hidden="true"
                        className={`absolute inset-0 flex items-center justify-center gap-2 transition-opacity duration-[120ms] ${isLoading ? "opacity-100" : "opacity-0"}`}
                    >
                        <Loader2 size={16} className="animate-spin" />
                        Creating account…
                    </span>
                </Button>
            </form>
            <p className={AUTH_SWITCH_LINK}>
                Already have an account? <Link href="/signin">Sign in</Link>
            </p>
        </AuthFrame>
    );
}
