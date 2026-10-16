"use client";

import styles from "@/components/mcp/mcp.module.css";
import { buttonVariants } from "@/components/ui/button";
import { LoaderCircle, TriangleAlert } from "lucide-react";
import Link from "next/link";

/** Where a service's connection returns: busy while it finishes, or why it did not, with the way back. */
export function CallbackScreen({
    error,
    service,
    back,
    backLabel = `Back to ${service}`,
}: {
    error: string;
    service: string;
    back: string;
    backLabel?: string;
}) {
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
                            href={back}
                            className={`${buttonVariants({ variant: "secondary" })} mt-5`}
                        >
                            {backLabel}
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
                        <h1 className="mt-3 text-[18px] font-medium">Connecting {service}</h1>
                        <p className="mt-1.5 text-[13.5px] leading-[1.5] text-muted-foreground">
                            One moment. You go back to {service} when this is done.
                        </p>
                    </>
                )}
            </div>
        </main>
    );
}
