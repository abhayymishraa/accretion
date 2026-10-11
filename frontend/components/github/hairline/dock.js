/**
 * Dock: the GitHub mark built as a coin standing on its edge, the cat raised on
 * its face, hovering over a plate with a slot. The nearer the pointer comes,
 * the lower the coin settles, until it lands in the slot; with the pointer gone
 * it lifts back. The second argument is how far the pull reaches, in viewBox units.
 */
import HL from "../../mcp/hairline/kernel.js";

const {
    Cam,
    clamp,
    fit,
    hull,
    open,
    poly,
    proj,
    rings,
    prism,
    facing,
    seg,
    spring,
    stepS,
    disposer,
    mk,
    pointer,
    put,
    register,
    solid,
} = HL;

// The cat inside simple-icons' GitHub mark, in the mark's own 24 × 24 units, y down.
// prettier-ignore
const CAT = [
    [8.75, 23.62], [8.91, 23.48], [9, 23.3], [9.03, 23.11], [9.02, 22.88], [9.02, 22.55],
    [9.02, 22.13], [9.01, 21.63], [9.01, 21.07], [7.31, 21.18], [6.15, 20.81], [5.43, 20.23],
    [5.07, 19.69], [4.97, 19.46], [4.62, 18.74], [4.26, 18.24], [3.95, 17.92], [3.72, 17.75],
    [3.63, 17.7], [3.22, 17.34], [3.19, 17.12], [3.37, 17.01], [3.6, 16.98], [3.72, 16.97],
    [4.37, 17.13], [4.88, 17.44], [5.26, 17.8], [5.48, 18.09], [5.56, 18.21], [6.26, 19.04],
    [7.05, 19.44], [7.83, 19.51], [8.53, 19.4], [9.05, 19.21], [9.14, 18.77], [9.27, 18.39],
    [9.43, 18.07], [9.61, 17.81], [9.81, 17.6], [8.22, 17.31], [6.73, 16.71], [5.5, 15.66],
    [4.66, 14.02], [4.34, 11.67], [4.4, 10.91], [4.56, 10.21], [4.81, 9.57], [5.15, 8.98],
    [5.58, 8.45], [5.48, 8.16], [5.37, 7.68], [5.33, 7.02], [5.41, 6.21], [5.68, 5.27],
    [5.81, 5.25], [6.18, 5.26], [6.83, 5.4], [7.76, 5.78], [8.98, 6.5], [9.57, 6.36],
    [10.16, 6.25], [10.76, 6.17], [11.37, 6.12], [11.98, 6.1], [12.6, 6.12], [13.2, 6.17],
    [13.81, 6.25], [14.4, 6.36], [14.98, 6.5], [16.2, 5.78], [17.13, 5.4], [17.77, 5.26],
    [18.15, 5.25], [18.27, 5.27], [18.54, 6.21], [18.62, 7.02], [18.58, 7.68], [18.48, 8.16],
    [18.39, 8.45], [18.81, 8.98], [19.15, 9.57], [19.41, 10.21], [19.56, 10.91], [19.62, 11.67],
    [19.31, 14.03], [18.46, 15.66], [17.22, 16.71], [15.74, 17.3], [14.14, 17.59], [14.39, 17.85],
    [14.61, 18.2], [14.79, 18.65], [14.91, 19.18], [14.95, 19.81], [14.95, 20.73], [14.95, 21.55],
    [14.94, 22.23], [14.94, 22.76], [14.94, 23.1], [14.97, 23.29], [15.05, 23.47], [15.21, 23.61],
];
const K = 3.4,
    R = 12 * K,
    T = 7,
    RT = 2.2,
    HOVER = 22,
    PT = 4,
    PW = R + 14,
    PD = 26;
const S2 = Math.SQRT1_2;

export function mount({ stage, svg }, value) {
    const bag = disposer();
    const reach = value;
    const C = Cam(45, 0.5, 2);
    // The coin's face stands in the plane x = y: its right runs along (1, -1), its depth along (1, 1).
    const at = (u, z, t) => [u * S2 + t * S2, -u * S2 + t * S2, z];
    fit(
        C,
        [
            at(-PW, 0, -PD),
            at(PW, 0, PD),
            at(-PW, 0, PD),
            at(PW, 0, -PD),
            at(-R, PT + HOVER + 2 * R, 0),
            at(R, PT + HOVER + 2 * R, T),
        ],
        200,
        166,
    );
    const P = proj(C),
        front = facing(C);
    const W = (u, z, t) => P(...at(u, z, t));

    const g = mk("g", {}, svg);
    // the plate, square to the coin, with the slot it lands in
    const [pr, pi] = rings(-PW, -PD, PW, PD, 10, 1.6);
    const turned = (ring) =>
        ring.map((q) => ({
            u: q.u * S2 + q.v * S2,
            v: -q.u * S2 + q.v * S2,
            nu: q.nu * S2 + q.nv * S2,
            nv: -q.nu * S2 + q.nv * S2,
        }));
    put(solid(g), prism(P, front, turned(pr), turned(pi), 0, PT));
    const slot = mk(
        "path",
        {
            class: "nf",
            d: poly([
                W(-R * 0.55, PT, -1.2),
                W(R * 0.55, PT, -1.2),
                W(R * 0.55, PT, T + 1.2),
                W(-R * 0.55, PT, T + 1.2),
            ]),
        },
        g,
    );
    const drop = mk("path", { class: "dash" }, g);

    // the coin: a disc standing on its edge, then the cat raised on its near face
    const disc = Array.from({ length: 72 }, (_, k) => {
        const a = (k / 72) * Math.PI * 2;
        return [Math.cos(a) * R, Math.sin(a) * R];
    });
    const inner = disc.map(([u, z]) => [u * (1 - 1.8 / R), z * (1 - 1.8 / R)]);
    const coin = solid(g);
    const catBack = mk("path", { class: "lo" }, g),
        catFace = mk("path", { class: "hi" }, g);
    const cat = CAT.map(([x, y]) => [(x - 12) * K, (12.297 - y) * K]);

    const e = spring(1);
    let drawn = -1;
    function draw() {
        if (Math.abs(e.x - drawn) < 1e-3) return;
        drawn = e.x;
        const z0 = PT + HOVER * e.x + R;
        const ring = (pts, t) => pts.map(([u, z]) => W(u, z0 + z, t));
        // seen from above, the coin's top edge shows between its back and its face
        put(coin, {
            sil: poly(hull(ring(disc, 0).concat(ring(disc, T)))),
            crease: open(
                ring(
                    inner.filter(([, z]) => z > 0),
                    T,
                ),
            ),
        });
        catBack.setAttribute("d", poly(ring(cat, T)));
        catFace.setAttribute("d", poly(ring(cat, T + RT)));
        drop.setAttribute("d", e.x > 0.02 ? seg(W(0, z0 - R, T / 2), W(0, PT, T / 2)) : "");
    }

    const B = register(stage, (dt) => {
        const moving = stepS(e, dt);
        draw();
        return moving;
    });
    bag.add(B.unregister);

    // hit test against the coin's centre at rest, which never moves
    const home = W(0, PT + HOVER + R, T / 2);
    function aim(pt) {
        const d = pt ? Math.hypot(pt[0] - home[0], pt[1] - home[1]) : Infinity;
        e.t = clamp((d - R * 0.6) / reach, 0, 1);
        slot.classList.toggle("lo", e.t > 0.5);
        B.wake();
    }
    bag.add(pointer(stage, { move: aim, leave: () => aim(null) }));
    bag.add(() => svg.replaceChildren());
    aim(null);
    draw();

    return { destroy: bag.dispose };
}
