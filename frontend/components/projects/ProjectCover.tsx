"use client";

import { useProjectCover } from "@/hooks/projects/useProjectCover";

import styles from "@/components/projects/project-shelf.module.css";
import Image from "next/image";
import { useState } from "react";

/** The app as its last succeeded build looked, or the blue brand mark on a grid until there is one. */
export function ProjectCover({
    projectId,
    version,
}: {
    projectId: string;
    version: string | null;
}) {
    const { url, loading } = useProjectCover(projectId, version);
    const [loaded, setLoaded] = useState(false);
    if (!url && !loading)
        return (
            <span className={`${styles.banner} absolute inset-0 grid place-items-center`}>
                <svg viewBox="0 0 100 100" aria-hidden="true" className="relative size-12">
                    <use href="/brand/accretion-mark.svg#mark" />
                </svg>
            </span>
        );
    return (
        <>
            {/* Stays under the image, so the fade never shows an empty frame. */}
            <span
                className={`absolute inset-0 bg-surface-3 ${url ? "" : "motion-safe:animate-pulse"}`}
            />
            {url && (
                // A session-authenticated blob URL, already sized for the card on the server.
                <Image
                    src={url}
                    alt=""
                    unoptimized
                    fill
                    data-loaded={loaded || undefined}
                    onLoad={() => setLoaded(true)}
                    className={`${styles.cover} object-cover object-top`}
                />
            )}
        </>
    );
}
