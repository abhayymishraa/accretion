/** The tetromino tables the build loader's bot plays with (components/ui/loader-tetris.tsx). */

export type Cell = [number, number];

/** The seven tetrominoes, each rotation listed as `[x, y]` cells. */
const SHAPES: { id: number; rot: Cell[][] }[] = [
    {
        id: 1, // I
        rot: [
            [
                [0, 1],
                [1, 1],
                [2, 1],
                [3, 1],
            ],
            [
                [2, 0],
                [2, 1],
                [2, 2],
                [2, 3],
            ],
        ],
    },
    {
        id: 2, // O
        rot: [
            [
                [0, 0],
                [1, 0],
                [0, 1],
                [1, 1],
            ],
        ],
    },
    {
        id: 3, // T
        rot: [
            [
                [1, 0],
                [0, 1],
                [1, 1],
                [2, 1],
            ],
            [
                [1, 0],
                [1, 1],
                [2, 1],
                [1, 2],
            ],
            [
                [0, 1],
                [1, 1],
                [2, 1],
                [1, 2],
            ],
            [
                [1, 0],
                [0, 1],
                [1, 1],
                [1, 2],
            ],
        ],
    },
    {
        id: 4, // S
        rot: [
            [
                [1, 0],
                [2, 0],
                [0, 1],
                [1, 1],
            ],
            [
                [0, 0],
                [0, 1],
                [1, 1],
                [1, 2],
            ],
        ],
    },
    {
        id: 5, // Z
        rot: [
            [
                [0, 0],
                [1, 0],
                [1, 1],
                [2, 1],
            ],
            [
                [1, 0],
                [0, 1],
                [1, 1],
                [0, 2],
            ],
        ],
    },
    {
        id: 6, // J
        rot: [
            [
                [0, 0],
                [0, 1],
                [1, 1],
                [2, 1],
            ],
            [
                [1, 0],
                [2, 0],
                [1, 1],
                [1, 2],
            ],
            [
                [0, 1],
                [1, 1],
                [2, 1],
                [2, 2],
            ],
            [
                [1, 0],
                [1, 1],
                [0, 2],
                [1, 2],
            ],
        ],
    },
    {
        id: 7, // L
        rot: [
            [
                [2, 0],
                [0, 1],
                [1, 1],
                [2, 1],
            ],
            [
                [1, 0],
                [1, 1],
                [1, 2],
                [2, 2],
            ],
            [
                [0, 1],
                [1, 1],
                [2, 1],
                [0, 2],
            ],
            [
                [0, 0],
                [1, 0],
                [1, 1],
                [1, 2],
            ],
        ],
    },
];

/**
 * Pull every rotation back to the origin. Without this a rotation whose cells
 * start away from zero — the upright I, say — can never reach the left wall.
 */
export const PIECES = SHAPES.map(({ id, rot }) => ({
    id,
    rot: rot.map((cells) => {
        const left = Math.min(...cells.map((c) => c[0]));
        const top = Math.min(...cells.map((c) => c[1]));
        return cells.map(([x, y]) => [x - left, y - top] as Cell);
    }),
}));
