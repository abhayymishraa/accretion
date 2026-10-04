"use client";
import { Button } from "@/components/ui/button";
import { ErrorBox } from "@/components/ui/ErrorBox";
import * as Dialog from "@radix-ui/react-dialog";
import styles from "./project-shelf.module.css";
export function ProjectDeleteDialog({
    open,
    deleting,
    title,
    error,
    dialogMotion,
    setDialogMotion,
    onClose,
    onConfirm,
    onRestoreFocus,
}: {
    open: boolean;
    deleting: boolean;
    title: string;
    error: string;
    dialogMotion: "open" | "closed" | null;
    setDialogMotion: (motion: "open" | "closed" | null) => void;
    onClose: () => void;
    onConfirm: () => Promise<void>;
    onRestoreFocus: () => void;
}) {
    return (
        <Dialog.Root
            open={open}
            onOpenChange={(open) => {
                if (!open && !deleting) onClose();
            }}
        >
            <Dialog.Portal>
                <Dialog.Overlay
                    data-motion={dialogMotion}
                    onPointerDown={() => setDialogMotion("closed")}
                    className={`${styles.dialogOverlay} fixed inset-0 z-50 bg-black/65`}
                />
                <Dialog.Content
                    data-motion={dialogMotion}
                    onPointerDownCapture={() => setDialogMotion("closed")}
                    onKeyDownCapture={() => setDialogMotion(null)}
                    onCloseAutoFocus={(event) => {
                        event.preventDefault();
                        onRestoreFocus();
                    }}
                    className={`${styles.dialogContent} fixed left-1/2 top-1/2 z-50 max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-border bg-card p-6 text-foreground shadow-xl`}
                >
                    <Dialog.Title className="text-xl font-medium">Delete project?</Dialog.Title>
                    <Dialog.Description className="mt-3 text-sm leading-relaxed text-muted-foreground">
                        <span className="wrap-anywhere font-medium text-foreground">{title}</span>{" "}
                        and its chat, saved files, and run history will be permanently removed. Its
                        preview will be stopped. This cannot be undone in Accretion.
                    </Dialog.Description>
                    <div className="[&>[data-error-box]]:mt-4">
                        <ErrorBox message={error} />
                    </div>
                    <div className="mt-6 flex flex-wrap justify-end gap-3">
                        <Dialog.Close asChild>
                            <Button variant="secondary" disabled={deleting}>
                                Keep project
                            </Button>
                        </Dialog.Close>
                        <Button disabled={deleting} onClick={() => void onConfirm()}>
                            {deleting ? "Deleting…" : "Delete project"}
                        </Button>
                    </div>
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    );
}
