/**
 * Bolt: the Supabase mark built as its two halves, standing over a plate. At
 * rest the halves stand apart, the upper one lifted; the nearer the pointer
 * comes, the closer they slide, until they meet as one bolt. The second argument is
 * how far the pull reaches, in viewBox units.
 */
import HL from "../../mcp/hairline/kernel.js";

const {
    Cam,
    clamp,
    fit,
    fillet,
    hull,
    open,
    poly,
    proj,
    rings,
    prism,
    facing,
    run,
    spring,
    stepS,
    disposer,
    mk,
    pointer,
    put,
    register,
    solid,
} = HL;

// simple-icons' Supabase mark, in its own 24 × 24 units, y down, cut where its two halves meet.
const UPPER = [
    [11.9, 1.04],
    [10.03, 0.4],
    [0.76, 12.05],
    [2.41, 15.46],
    [11.99, 15.46],
];
const LOWER = [
    [11.99, 15.46],
    [12.1, 22.97],
    [13.97, 23.6],
    [23.24, 11.95],
    [21.59, 8.54],
    [11.95, 8.54],
];
const K = 3.6,
    T = 8,
    PT = 4,
    PW = 58,
    PD = 22,
    BASE = 10,
    GAP = 9,
    LIFT = 7;
const S2 = Math.SQRT1_2;

/** A half as a ring, rounded a little at every corner, with the outward normal of each sample. */
function ring(pts, inset) {
    const r = fillet(
        pts.map(([x, y]) => [(x - 12) * K, (12 - y) * K]),
        pts.map(() => 2.2),
        3,
    );
    const n = r.length;
    return r.map((p, i) => {
        const a = r[(i + n - 1) % n],
            b = r[(i + 1) % n],
            l = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
        // the outline runs clockwise on screen, so its outward normal is the tangent turned left
        const nu = -(b[1] - a[1]) / l,
            nv = (b[0] - a[0]) / l;
        return { u: p[0] - nu * inset, v: p[1] - nv * inset, nu, nv };
    });
}

export function mount({ stage, svg }, value) {
    const bag = disposer();
    const reach = value;
    const C = Cam(45, 0.5, 2);
    // The mark stands in the plane x = y: its right runs along (1, -1), its depth along (1, 1).
    const at = (u, z, t) => [u * S2 + t * S2, -u * S2 + t * S2, z];
    const top = PT + BASE + 24 * K;
    fit(
        C,
        [
            at(-PW, 0, -PD),
            at(PW, 0, PD),
            at(-PW, 0, PD),
            at(PW, 0, -PD),
            at(-12 * K - GAP, top + LIFT, 0),
            at(12 * K + GAP, top, T),
        ],
        200,
        166,
    );
    const P = proj(C),
        front = facing(C);
    const W = (u, z, t) => P(...at(u, z, t));

    const g = mk("g", {}, svg);
    const [pr, pi] = rings(-PW, -PD, PW, PD, 10, 1.6);
    const turned = (rg) =>
        rg.map((q) => ({
            u: q.u * S2 + q.v * S2,
            v: -q.u * S2 + q.v * S2,
            nu: q.nu * S2 + q.nv * S2,
            nv: -q.nu * S2 + q.nv * S2,
        }));
    put(solid(g), prism(P, front, turned(pr), turned(pi), 0, PT));

    // the upper half first: the halves stand side by side, the same distance from the eye
    const halves = [UPPER, LOWER].map((pts, i) => ({
        out: ring(pts, 0),
        inn: ring(pts, 1.6),
        s: solid(g),
        side: i ? 1 : -1,
    }));
    const e = spring(1);
    let drawn = -1;
    function draw() {
        if (Math.abs(e.x - drawn) < 1e-3) return;
        drawn = e.x;
        for (const h of halves) {
            const du = h.side * GAP * e.x,
                dz = PT + BASE + 12 * K + (h.side < 0 ? LIFT * e.x : 0);
            const pts = (rg, t) => rg.map((q) => W(q.u + du, q.v + dz, t));
            // seen from above, a half's upward edges show between its back and its face
            put(h.s, {
                sil: poly(hull(pts(h.out, 0).concat(pts(h.out, T)))),
                crease: open(
                    pts(
                        run(h.inn, (q) => q.nv > 0.2),
                        T,
                    ),
                ),
            });
        }
    }

    const B = register(stage, (dt) => {
        const moving = stepS(e, dt);
        draw();
        return moving;
    });
    bag.add(B.unregister);

    // hit test against the bolt's centre at rest, which never moves
    const home = W(0, PT + BASE + 12 * K, T / 2);
    function aim(pt) {
        const d = pt ? Math.hypot(pt[0] - home[0], pt[1] - home[1]) : Infinity;
        e.t = clamp((d - 12 * K * 0.5) / reach, 0, 1);
        // apart, the lower half holds the bright edge; joined, the whole bolt does
        halves.forEach((h, i) => h.s.sil.classList.toggle("hi", i === 1 || e.t < 0.15));
        B.wake();
    }
    bag.add(pointer(stage, { move: aim, leave: () => aim(null) }));
    bag.add(() => svg.replaceChildren());
    aim(null);
    draw();

    return { destroy: bag.dispose };
}
