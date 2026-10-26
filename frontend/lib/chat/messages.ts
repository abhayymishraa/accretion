import type { Message } from "@/types/chat.type";

// A queued run waits for a worker; both are live and both have a stream to follow.
export function isOpenRun(status: Message["run_status"]): boolean {
    return status === "queued" || status === "running";
}

/** Each message with the steers sent during it. History sorts by creation time, so a steer follows the run it
 * was sent to (agent/context/history.py); it shows inside that run, not after its reply. */
export function withSteers(messages: Message[]): { message: Message; steers: Message[] }[] {
    const items: { message: Message; steers: Message[] }[] = [];
    for (const message of messages) {
        const last = items.at(-1);
        if (message.event_type === "steer" && last?.message.event_type === "run")
            last.steers = [...last.steers, message];
        // One shared empty list: a new one per call would re-render every bubble on each streamed event.
        else items.push({ message, steers: NO_STEERS });
    }
    return items;
}

const NO_STEERS: Message[] = [];
