import type { Message } from "@/types/chat.type";

// A queued run waits for a worker; both are live and both have a stream to follow.
export function isOpenRun(status: Message["run_status"]): boolean {
    return status === "queued" || status === "running";
}
