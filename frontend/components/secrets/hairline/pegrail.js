/**
 * Peg rail: a wall rail of five round pegs with nothing hung on them, the
 * empty state of a project's keys. At rest the pegs stand out unevenly and the
 * second one, a little further out, holds the bright edge. The pointer picks
 * the peg nearest it on screen (by rest position); that peg slides out, and
 * its neighbours slide less the further away they are. The second argument is
 * that reach, in pegs.
 */
import HL from "../../mcp/hairline/kernel.js";

const {
    Cam,
    circ,
    clamp,
    fit,
    hull,
    open,
    poly,
    proj,
    rrect,
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

const N = 5,
    PITCH = 22,
    X0 = 18,
    W = 2 * X0 + (N - 1) * PITCH;
const H = 30,
    T = 4,
    CZ = 12;
const SR = 2.1,
    HR = 4.2,
    HT = 2.6,
    L0 = 5,
    OUT = 15;
const REST = [0.2, 0.62, 0.28, 0.08, 0.16];
const falloff = (d, R) => clamp(1 - d / R, 0, 1);

export function mount({ stage, svg }, value) {
    const bag = disposer();
    const reach = value;
    const C = Cam(45, 0.5, 2.7);
    fit(
        C,
        [
            [0, -T, H],
            [W, -T, H],
            [0, 0, 0],
            [W, 0, 0],
            [X0, L0 + OUT + HT, CZ - HR],
            [W - X0, L0 + OUT + HT, CZ - HR],
        ],
        200,
        166,
    );
    const P = proj(C);
    const at = (ring, cx, y, cz) => ring.map((q) => P(cx + q.u, y, cz + q.v));
    // which edge of a ring extruded along y the camera sees on its near face
    const seen = (q) => 0.612 * q.nu + 0.5 * q.nv > 0;
    const rod = (ring, inner, cx, cz, y0, y1) => ({
        sil: poly(hull(at(ring, cx, y0, cz).concat(at(ring, cx, y1, cz)))),
        crease: inner ? open(at(run(inner, seen), cx, y1, cz)) : "",
    });

    const g = mk("g", {}, svg);
    // the rail: a rounded plank standing against the wall, with a screw near each end
    put(solid(g), rod(rrect(0, 0, W, H, 4, 4), rrect(1, 1, W - 1, H - 1, 3, 4), 0, 0, -T, 0));
    for (const sx of [7, W - 7])
        mk("path", { d: poly(at(circ(1.7, 20), sx, 0, H - 8)), class: "nf" }, g);
    mk("path", { d: open([P(X0 - 8, 0, H - 4), P(W - X0 + 8, 0, H - 4)]), class: "lo nf" }, g);

    const shaft = circ(SR, 32),
        head = circ(HR, 40),
        headIn = circ(HR - 0.9, 40);
    const pegs = REST.map((r, i) => {
        const grp = mk("g", {}, g);
        const s = mk("path", { class: "sil" }, grp),
            h = solid(grp);
        return { cx: X0 + i * PITCH, s, h, e: spring(r), drawn: -1 };
    });

    function draw(p) {
        if (Math.abs(p.e.x - p.drawn) < 1e-3) return;
        p.drawn = p.e.x;
        const L = L0 + OUT * p.e.x;
        p.s.setAttribute("d", rod(shaft, null, p.cx, CZ, 0, L).sil);
        put(p.h, rod(head, headIn, p.cx, CZ, L, L + HT));
    }

    let act = -2;
    function setActive(a) {
        if (a === act) return;
        act = a;
        pegs.forEach((p, i) => {
            p.e.t = a < 0 ? REST[i] : Math.max(REST[i] * 0.5, falloff(Math.abs(i - a), reach));
            p.h.sil.classList.toggle("hi", i === (a < 0 ? 1 : a));
        });
        B.wake();
    }

    const B = register(stage, (dt) => {
        let moving = false;
        for (const p of pegs) {
            if (stepS(p.e, dt)) moving = true;
            draw(p);
        }
        return moving;
    });
    bag.add(B.unregister);

    // hit test on the pegs' rest positions on screen, which never move
    const rx = pegs.map((p) => P(p.cx, 0, CZ));
    function hit([x, y]) {
        if (y < rx[0][1] - 70 || y > rx[N - 1][1] + 60) return -1;
        let best = -1,
            bd = PITCH * 1.4;
        rx.forEach(([px], i) => {
            const d = Math.abs(px - x);
            if (d < bd) {
                bd = d;
                best = i;
            }
        });
        return best;
    }
    bag.add(pointer(stage, { move: (pt) => setActive(hit(pt)), leave: () => setActive(-1) }));
    bag.add(() => svg.replaceChildren());
    setActive(-1);

    return { destroy: bag.dispose };
}
