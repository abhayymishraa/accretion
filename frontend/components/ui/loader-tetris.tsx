"use client";

import {
    type ComponentProps,
    type CSSProperties,
    useCallback,
    useEffect,
    useRef,
    useState,
} from "react";

import { generateTetrisFrames } from "@/lib/tetris/frames";
import { cn } from "@/lib/utils";

/**
 * I, O, T, S, Z, J, L. Each one reads a theme variable, so a light and a dark
 * board get their own shade; the literal after the comma keeps the component
 * working on its own, without the stylesheet.
 */
const PALETTE = [
    "var(--tetris-1, oklch(0.797 0.134 211.5))",
    "var(--tetris-2, oklch(0.861 0.173 91.9))",
    "var(--tetris-3, oklch(0.709 0.159 293.5))",
    "var(--tetris-4, oklch(0.800 0.182 151.7))",
    "var(--tetris-5, oklch(0.711 0.166 22.2))",
    "var(--tetris-6, oklch(0.714 0.143 254.6))",
    "var(--tetris-7, oklch(0.758 0.159 55.9))",
];

/** A number is read as pixels; a string goes through as written, `0.4em` and all. */
type Size = number | string;

const size = (value: Size) => (typeof value === "number" ? `${value}px` : value);

export type TetrisLoaderProps = {
    /** Cells across. Default `8`, minimum `4`. */
    columns?: number;
    /** Cells down. Default `16`, minimum `6`. */
    rows?: number;
    /** Side of one cell. A number is pixels. Default `6` — the whole loader scales with it. */
    cellSize?: Size;
    /** Space between cells. A number is pixels. Default `2`. */
    gap?: Size;
    /** Milliseconds per frame. Default `40`. */
    speed?: number;
    /** Pause or resume the animation. Default `true`. */
    playing?: boolean;
    /** Start a fresh game after each game over. Default `true`. */
    loop?: boolean;
    /** Called every time a game ends. */
    onComplete?: () => void;
    /** What a screen reader announces. Default `"Loading"`. */
    label?: string;
    /** Seven CSS colours, one per tetromino, in I O T S Z J L order. */
    colors?: readonly string[];
    /** Colour of a line the moment it clears. Defaults to the foreground. */
    flashColor?: string;
    /** Colour of the stack once the game is lost. */
    deadColor?: string;
    /** Extra classes for a single cell, on top of the size and colour above. */
    dotClassName?: string;
} & ComponentProps<"div">;

/** A fresh game for a board of this size. */
function deal(width: number, height: number) {
    return { dims: `${width}x${height}`, game: generateTetrisFrames(width, height) };
}

/** True while the reader asks for less movement. */
function useReducedMotion(): boolean {
    const [reduced, setReduced] = useState(false);

    useEffect(() => {
        const query = window.matchMedia("(prefers-reduced-motion: reduce)");
        const read = () => setReduced(query.matches);
        read();
        query.addEventListener("change", read);
        return () => query.removeEventListener("change", read);
    }, []);

    return reduced;
}

/**
 * A loading indicator that plays tetris. A bot stacks the pieces, clears the
 * lines, and eventually tops out — then the board wipes and a new game starts.
 * Readers who ask for less movement get one still board instead.
 */
export function TetrisLoader({
    columns = 8,
    rows = 16,
    cellSize = 6,
    gap = 2,
    speed = 40,
    playing = true,
    loop = true,
    onComplete,
    label = "Loading",
    colors = PALETTE,
    flashColor = "var(--tetris-flash, var(--foreground, currentColor))",
    deadColor = "var(--tetris-dead, color-mix(in oklab, var(--foreground, currentColor) 45%, transparent))",
    dotClassName,
    className,
    style,
    ...props
}: TetrisLoaderProps) {
    const width = Math.max(4, Math.round(columns));
    const height = Math.max(6, Math.round(rows));

    const gridRef = useRef<HTMLDivElement>(null);
    const frame = useRef(0);

    const reduced = useReducedMotion();
    // Frames only drive painting, never markup, so generating them during render cannot break hydration.
    const [board, setBoard] = useState(() => deal(width, height));
    // A new board size starts a new game, adjusted during render as React recommends.
    if (board.dims !== `${width}x${height}`) setBoard(deal(width, height));
    const game = board.game;

    // Held in a ref so an inline callback does not restart the animation.
    const completeRef = useRef(onComplete);
    useEffect(() => {
        completeRef.current = onComplete;
    });

    const paint = useCallback(
        (dots: HTMLDivElement[], index: number) => {
            const board = game[index];
            if (!board) return;

            dots.forEach((dot, i) => {
                const value = board[i] ?? 0;
                dot.style.backgroundColor = value ? `var(--tetris-cell-${value})` : "";
            });
        },
        [game],
    );

    useEffect(() => {
        const grid = gridRef.current;
        if (!grid) return;
        const dots = Array.from(grid.children) as HTMLDivElement[];

        if (frame.current >= game.length) frame.current = 0;

        // One still board, a good way in, for anyone who asked for less movement.
        if (reduced) {
            paint(dots, Math.floor(game.length * 0.55));
            return;
        }

        paint(dots, frame.current);
        if (!playing) return;

        // A clock, not a timer: a background tab freezes the game instead of
        // banking up frames it has to rush through on the way back.
        let request = 0;
        let last = performance.now();
        let owed = 0;

        const tick = (now: number) => {
            owed += now - last;
            last = now;
            if (owed > speed * 4) owed = speed;

            let ended = false;
            while (owed >= speed) {
                owed -= speed;
                frame.current++;
                if (frame.current >= game.length) {
                    ended = true;
                    break;
                }
            }

            paint(dots, Math.min(frame.current, game.length - 1));

            if (!ended) {
                request = requestAnimationFrame(tick);
                return;
            }

            completeRef.current?.();
            // A new game replaces the frames, which restarts this effect.
            if (loop) {
                frame.current = 0;
                setBoard(deal(width, height));
            } else frame.current = game.length - 1;
        };

        request = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(request);
    }, [game, playing, speed, loop, paint, reduced, width, height]);

    const vars: Record<string, string> = {
        "--tetris-cell": size(cellSize),
        "--tetris-gap": size(gap),
        "--tetris-cell-8": flashColor,
        "--tetris-cell-9": deadColor,
    };
    for (let i = 0; i < 7; i++) vars[`--tetris-cell-${i + 1}`] = colors[i] ?? PALETTE[i];

    return (
        <div
            ref={gridRef}
            role="status"
            aria-label={label}
            aria-busy={playing && !reduced}
            className={cn("grid w-fit", className)}
            style={
                {
                    gridTemplateColumns: `repeat(${width}, var(--tetris-cell))`,
                    gap: "var(--tetris-gap)",
                    ...vars,
                    ...style,
                } as CSSProperties
            }
            {...props}
        >
            {Array.from({ length: width * height }).map((_, i) => (
                <div
                    key={i}
                    style={{
                        height: "var(--tetris-cell)",
                        borderRadius: "calc(var(--tetris-cell) / 3)",
                    }}
                    className={cn("bg-foreground/10", dotClassName)}
                />
            ))}
        </div>
    );
}

export default TetrisLoader;
