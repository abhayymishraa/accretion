"use client";

import styles from "@/components/mcp/mcp.module.css";
import { buttonVariants } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

/** The top of the GitHub and Supabase pages: the way back, the service's mark as a figure, its name and what it does. */
export function IntegrationHeader({
    title,
    description,
    figure,
}: {
    title: string;
    description: string;
    figure: ReactNode;
}) {
    return (
        <>
            <Link href="/projects" className={`${buttonVariants({ variant: "back" })} mb-2`}>
                <ChevronLeft size={16} aria-hidden="true" />
                Projects
            </Link>
            <header
                className={`${styles.rise} mb-8 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:gap-8`}
            >
                <div className="min-w-0 flex-1">
                    <h1 className="text-[20px] leading-7 font-semibold">{title}</h1>
                    <p className="mt-2 max-w-[52ch] text-[14px] leading-5 text-pretty text-foreground/85">
                        {description}
                    </p>
                </div>
                <div className="self-center sm:self-auto">{figure}</div>
            </header>
        </>
    );
}
