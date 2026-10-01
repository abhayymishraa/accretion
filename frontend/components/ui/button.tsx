import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

// Compact on a mouse, thumb-sized on touch: coarse pointers get the 44px target.
const control =
    "ember-button h-9 pointer-coarse:h-11 gap-2 rounded-[10px] border text-[13px] font-medium leading-none whitespace-nowrap no-underline [transition:background-color_140ms_ease,border-color_140ms_ease,opacity_140ms_ease,transform_140ms_var(--ease-out)] disabled:opacity-40 [&:not(:disabled):active]:scale-[0.985] motion-reduce:[&:not(:disabled):active]:scale-100 focus-visible:active:scale-100";

// Outline pill for marketing surfaces (landing, auth). Deliberately separate
// from `control`: those are app chrome at h-9/rounded-[10px], these are taller
// and fully rounded. Size, padding and text scale stay with the call site.
const outlinePill =
    "gap-2 rounded-full border border-foreground/25 bg-transparent font-medium text-foreground no-underline transition-[transform,background-color,border-color] duration-[160ms] ease-[var(--ease-out)] active:scale-[0.97] motion-reduce:active:scale-100 pointer-fine:hover:border-foreground/45 pointer-fine:hover:bg-foreground/5";

// Small chrome controls dip on press, like `control` above, kept subtle for how often they are hit.
const press =
    "[&:not(:disabled):active]:scale-[0.97] motion-reduce:[&:not(:disabled):active]:scale-100";
const ghost = `gap-1.5 rounded-[8px] border-0 bg-transparent text-muted-foreground [transition:background-color_130ms_ease,color_130ms_ease,scale_100ms_var(--ease-out)] ${press} disabled:opacity-40 disabled:cursor-default pointer-fine:hover:bg-surface-2 pointer-fine:hover:text-foreground`;

export const buttonVariants = cva(
    "inline-flex items-center justify-center cursor-pointer disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-solid focus-visible:outline-ring focus-visible:outline-offset-2 [&_svg]:shrink-0",
    {
        variants: {
            variant: {
                default: `${control} px-4 border-transparent bg-primary text-primary-foreground pointer-fine:hover:bg-primary/88`,
                secondary: `${control} ember-secondary px-4 border-border bg-surface-2 text-foreground pointer-fine:hover:bg-surface-2 pointer-fine:hover:border-input`,
                send: `${control} ember-send size-8 pointer-coarse:size-9 p-0 border-transparent bg-primary text-primary-foreground pointer-fine:hover:bg-primary/88`,
                icon: `ember-icon size-8 pointer-coarse:size-10 shrink-0 rounded-[8px] border border-transparent bg-transparent text-muted-foreground [transition:background-color_130ms_ease,color_130ms_ease,scale_100ms_var(--ease-out)] ${press} aria-pressed:bg-accent aria-pressed:text-accent-foreground pointer-fine:hover:bg-surface-2 pointer-fine:hover:text-foreground`,
                utility: `transcript-utility ${ghost} h-8 pointer-coarse:h-10 min-w-8 px-2 text-[12px]`,
                outlinePill,
                tab: `ember-tab h-8 gap-1.5 rounded-[7px] border-0 bg-transparent px-3 text-[12.5px] text-muted-foreground whitespace-nowrap [transition:background-color_130ms_ease,color_130ms_ease,scale_100ms_var(--ease-out)] ${press} aria-pressed:bg-surface-2 aria-pressed:text-foreground pointer-fine:hover:text-foreground`,
            },
        },
        defaultVariants: { variant: "default" },
    },
);

export function Button({
    className,
    variant,
    ...props
}: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants>) {
    return (
        <button
            data-slot="button"
            className={cn(buttonVariants({ variant }), className)}
            {...props}
        />
    );
}
