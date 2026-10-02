import { API_BASE_URL } from "@/config/env";

// The server turned the stream away: expired token, or a project or run this user cannot see.
// Retrying with the same token cannot succeed, unlike a network failure.
export class StreamRefusedError extends Error {}
const REFUSED = [401, 403, 404];

// Reconnect backoff shared by every stream: 1 s, doubling, capped at 10 s.
export function retryDelay(attempt: number): number {
    return Math.min(1000 * 2 ** attempt, 10000);
}

type FollowOptions = {
    lastEventId?: string;
    onEvent: (data: string, id: string | undefined) => void;
    signal: AbortSignal;
};

// A line ends at CRLF, LF or a lone CR (WHATWG HTML, "Interpreting an event stream"). A CR that
// ends the buffer stays there until the next chunk shows whether an LF follows it.
const LINE_END = /\r\n|\r(?!$)|\n/;

// Reads a text/event-stream with the session's bearer token. EventSource cannot send
// Authorization, so this parses the SSE wire format itself: blank line ends an event.
// Axios cannot read a streaming body in the browser, so this is the one place fetch is used.
export async function followEvents(path: string, { lastEventId, onEvent, signal }: FollowOptions) {
    const token = localStorage.getItem("auth_token");
    const headers: Record<string, string> = { Accept: "text/event-stream" };
    if (token) headers.Authorization = `Bearer ${token}`;
    if (lastEventId) headers["Last-Event-ID"] = lastEventId;
    const response = await fetch(`${API_BASE_URL}${path}`, { headers, signal });
    if (REFUSED.includes(response.status)) throw new StreamRefusedError();
    if (!response.ok || !response.body) throw new Error(`Stream failed with ${response.status}`);
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = "";
    let data: string[] = [];
    let id: string | undefined;
    for (;;) {
        const { value, done } = await reader.read();
        // An event cut off before its blank line is discarded, as the spec requires.
        // A read that settled just before abort must not reach a hook that has unmounted.
        if (done || signal.aborted) return;
        buffer += value;
        const lines = buffer.split(LINE_END);
        buffer = lines.pop() ?? "";
        for (const line of lines) {
            if (line === "") {
                if (data.length) onEvent(data.join("\n"), id);
                data = [];
                continue;
            }
            if (line.startsWith(":")) continue;
            const [field, ...rest] = line.split(":");
            const text = rest.join(":").replace(/^ /, "");
            if (field === "data") data.push(text);
            if (field === "id") id = text;
        }
    }
}
