"use client";

import { ImageGeneration } from "img-fx";

/** Pixel-mosaic loader that dissolves into the given images (img-fx). Off: see config/effects.ts. */
export default function PreviewReveal({ images }: { images: string[] }) {
    return (
        <ImageGeneration preset="pixels-organic" images={images} autoReveal>
            <div className="size-40 rounded-[14px] bg-surface-2" />
        </ImageGeneration>
    );
}
