"use client";

import { buttonVariants } from "@/components/ui/button";
import { useSignInCallback } from "@/hooks/connections/useSignInCallback";
import { LoaderCircle, TriangleAlert } from "lucide-react";
import Link from "next/link";
import styles from "./mcp.module.css";

/** Where a service's sign-in returns: it finishes the sign-in, then goes back to Connections. */
export function SignInCallback() {
    const { error } = useSignInCallback();
    return (
        <main
            id="main-content"
            className="grid min-h-dvh place-items-center px-4 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]"
        >
            <div
                key={error ? "error" : "busy"}
                className={`${styles.rise} flex w-full max-w-[360px] flex-col items-center text-center`}
                role={error ? "alert" : "status"}
            >
                {error ? (
                    <>
                        <TriangleAlert
                            size={22}
                            strokeWidth={1.75}
                            aria-hidden="true"
                            className="text-destructive"
                        />
                        <h1 className="mt-3 text-[18px] font-medium">Not connected</h1>
                        <p className="mt-1.5 text-[13.5px] leading-[1.5] text-muted-foreground">
                            {error}
                        </p>
                        <Link
                            href="/connectors"
                            className={`${buttonVariants({ variant: "secondary" })} mt-5`}
                        >
                            Back to Connectors
                        </Link>
                    </>
                ) : (
                    <>
                        <LoaderCircle
                            size={22}
                            strokeWidth={1.75}
                            aria-hidden="true"
                            className="text-primary motion-safe:animate-spin"
                        />
                        <h1 className="mt-3 text-[18px] font-medium">Finishing sign-in</h1>
                        <p className="mt-1.5 text-[13.5px] leading-[1.5] text-muted-foreground">
                            One moment. You go back to Connectors when this is done.
                        </p>
                    </>
                )}
            </div>
        </main>
    );
}
