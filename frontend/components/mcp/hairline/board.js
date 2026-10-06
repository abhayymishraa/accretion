/**
 * Board: a patch panel with one port for each connector in a project. A live
 * connector's plug sits in its port with the cable rising behind; an off one's
 * plug is pulled out of its port, its cable hanging down; one that needs the
 * user is an empty port, and at rest the first of those holds the bright edge.
 * The pointer picks a port: its cable lifts, and its neighbours lean away, less
 * the further away; `reach` is how many ports the lean reaches. A port
 * switched between live and off moves its plug in or out on a spring.
 */
import HL from "./kernel.js";

const {
    Cam,
    clamp,
    facing,
    fillet,
    fit,
    hull,
    lerp,
    open,
    poly,
    proj,
    rings,
    rrect,
    run,
    seg,
    spring,
    stepS,
    disposer,
    mk,
    pointer,
    prism,
    put,
    register,
    solid,
} = HL;

const PITCH = 20,
    EAR = 14,
    MAR = 6,
    X0 = EAR + MAR;
const H = 34,
    T = 2.6,
    DEEP = 16,
    CZ = 17;
const JW = 5.4,
    JH = 4.4,
    NW = 2,
    NH = 1.8,
    JD = 2.4;
const PW = 4.6,
    PH = 3.7,
    PL = 4,
    BL = 5,
    CR = 1.9,
    OUT = 8,
    LEAN = 10,
    LIFT = 12;
const PULL = 9;
const falloff = (d, R) => (d === 0 ? 0 : clamp(1 - (d - 1) / R, 0, 1));

/** A cable of half-width w along screen points q, with round ends. */
function tube(q, w) {
    const n = q.length,
        L = [],
        R = [],
        tn = [];
    for (let i = 0; i < n; i++) {
        const a = q[Math.max(0, i - 1)],
            b = q[Math.min(n - 1, i + 1)],
            l = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
        const t = [(b[0] - a[0]) / l, (b[1] - a[1]) / l];
        tn.push(t);
        L.push([q[i][0] - t[1] * w, q[i][1] + t[0] * w]);
        R.push([q[i][0] + t[1] * w, q[i][1] - t[0] * w]);
    }
    const cap = (c, t, s) =>
        [1, 2, 3, 4, 5].map((k) => {
            const th = (k / 6) * Math.PI,
                cs = Math.cos(th),
                sn = Math.sin(th);
            return [
                c[0] + s * w * (-t[1] * cs + t[0] * sn),
                c[1] + s * w * (t[0] * cs + t[1] * sn),
            ];
        });
    return poly([...L, ...cap(q[n - 1], tn[n - 1], 1), ...R.reverse(), ...cap(q[0], tn[0], -1)]);
}

/** Draws one port per entry of states ("live", "off" or "attention"), left to right. */
export function mount({ stage, svg }, reach, states) {
    const bag = disposer();
    const N = states.length,
        W = 2 * X0 + N * PITCH;
    // ponytail: the panel shrinks to fit past six ports; at twenty it is too fine to read
    const S = Math.min(2.15, 344 / W),
        C = Cam(45, 0.5, S);
    fit(
        C,
        [
            [0, -DEEP, H],
            [W, -DEEP, H],
            [0, 0, 0],
            [W, 0, 0],
            [X0, 34, CZ + 30 + LIFT],
            [W - X0, 30, CZ - 30],
        ],
        200,
        166,
    );
    const P = proj(C),
        front = facing(C);
    let over = -1,
        lit = null;
    const at = (ring, cx, y, cz) => ring.map((q) => P(cx + q.u, y, cz + q.v));
    const seen = (q) => 0.612 * q.nu + 0.5 * q.nv > 0;
    const slab = (ring, inner, cx, cz, y0, y1) => ({
        sil: poly(hull(at(ring, cx, y0, cz).concat(at(ring, cx, y1, cz)))),
        crease: open(at(run(inner, seen), cx, y1, cz)),
    });

    // the chassis behind the face, then the face plate with its four rack screws
    const g = mk("g", {}, svg);
    const [br, bi] = rings(EAR + 2, -DEEP, W - EAR - 2, -T, 3, 1.6);
    put(solid(g), prism(P, front, br, bi, 3, H - 3));
    put(
        solid(g),
        slab(rrect(0, 0, W, H, 3, 4), rrect(0.7, 0.7, W - 0.7, H - 0.7, 2.3, 4), 0, 0, -T, 0),
    );
    const flat = (ring) => ring.map((q) => [q.u, q.v]);
    const face = (pts, cls) =>
        mk("path", { d: poly(pts.map(([x, z]) => P(x, 0, z))), class: cls }, g);
    for (const ex of [EAR / 2 + 1, W - EAR / 2 - 1])
        for (const ez of [8, H - 8])
            face(flat(rrect(ex - 3.4, ez - 1.5, ex + 3.4, ez + 1.5, 1.5, 3)), "nf");
    face(flat(rrect(X0 + 1, CZ - JH - 3.4, W - X0 - 1, CZ + JH + NH + 3, 2.4, 4)), "lo nf");

    const jack = fillet(
        [
            [-JW, -JH],
            [JW, -JH],
            [JW, JH],
            [NW, JH],
            [NW, JH + NH],
            [-NW, JH + NH],
            [-NW, JH],
            [-JW, JH],
        ],
        [1, 1, 1, 0.4, 0.5, 0.5, 0.4, 1],
    );
    const ports = states.map((state, p) => ({ p, state, cx: X0 + (p + 0.5) * PITCH }));
    for (const pt of ports) {
        pt.jack = face(
            jack.map(([u, v]) => [pt.cx + u, CZ + v]),
            "nf",
        );
        mk(
            "path",
            {
                d: open(
                    [
                        [-JW + JD, JH],
                        [-JW + JD, -JH + 0.816 * JD],
                        [JW, -JH + 0.816 * JD],
                    ].map(([u, v]) => P(pt.cx + u, 0, CZ + v)),
                ),
                class: "lo nf",
            },
            g,
        );
    }

    // cables first, so every plug covers the end of its own cable
    const cabG = mk("g", {}, g),
        plugG = mk("g", {}, g);
    const plug = rrect(-PW, -PH, PW, PH, 1.2, 3),
        plugIn = rrect(-PW + 0.7, -PH + 0.7, PW - 0.7, PH - 0.7, 0.6, 3);
    const bootA = rrect(-3.8, -3.1, 3.8, 3.1, 1.6, 3),
        bootB = rrect(-2.5, -2.5, 2.5, 2.5, 2.4, 3);
    for (const pt of ports) {
        pt.pull = spring(0, { eps: 2e-3 });
        pt.lx = spring(0, { eps: 0.01 });
        // 0 is seated (live), 1 pulled out (off): the spring carries a switch flip between them.
        pt.seat = spring(pt.state === "off" ? 1 : 0, { eps: 2e-3 });
        if (pt.state === "attention") continue;
        pt.cable = mk("path", { class: "sil" }, cabG);
        pt.plug = solid(plugG);
        pt.latch = mk("path", { class: "lo nf" }, pt.plug.g);
        pt.boot = solid(plugG);
        pt.drawn = "";
    }

    function drawPort(pt) {
        const k = pt.pull.x,
            lx = pt.lx.x,
            u = pt.seat.x,
            key = [k, lx, u].map((v) => v.toFixed(3)).join();
        if (key === pt.drawn) return;
        pt.drawn = key;
        const cx = pt.cx,
            cz = CZ,
            y0 = PULL * u;
        const y1 = y0 + PL + OUT * k,
            y2 = y1 + BL,
            j = ((pt.p * 7) % 5) - 2;
        put(pt.plug, slab(plug, plugIn, cx, cz, y0, y1));
        pt.latch.setAttribute("d", seg(P(cx, y0 + 0.6, cz + PH), P(cx, y1 - 0.8, cz + PH)));
        put(pt.boot, {
            sil: poly(hull(at(bootA, cx, y1, cz).concat(at(bootB, cx, y2, cz)))),
            crease: "",
        });
        // the cable rises behind a seated plug and hangs below a pulled one, and swings between the two
        const p0 = [cx, y2 - 1.5, cz],
            p1 = [lerp(cx, cx + 0.5, u), y2 + lerp(1 + 2 * k, 6 + 4 * k, u), cz + lerp(6, 0, u)];
        const p3 = [cx + 3 + j + lx, y2 + 3 + LIFT * k, cz + lerp(26 + j, -18, u) + LIFT * k],
            p2 = [p3[0] - 0.6, p3[1] - 1, p3[2] - lerp(12, -12, u)];
        const q = [];
        for (let i = 0; i <= 16; i++) {
            const s = i / 16,
                a = (1 - s) ** 3,
                b = 3 * (1 - s) ** 2 * s,
                c = 3 * (1 - s) * s * s,
                d = s ** 3;
            q.push(P(...[0, 1, 2].map((m) => a * p0[m] + b * p1[m] + c * p2[m] + d * p3[m])));
        }
        pt.cable.setAttribute("d", tube(q, CR * S));
    }

    /** Pulls port a and leans the others away from it; -1 settles every port. */
    function aim(a) {
        for (const pt of ports) {
            const dx = a < 0 ? 0 : pt.p - a,
                f = falloff(Math.abs(dx), reach);
            pt.pull.t = pt.p === a ? 1 : 0;
            pt.lx.t = dx ? clamp(Math.sign(dx) * f * LEAN, -LEAN, LEAN) : 0;
        }
    }
    /** Gives the one bright edge to port pt: its plug and cable, or its empty jack. */
    function light(pt) {
        if (pt === lit) return;
        const mark = (q, on) =>
            (q.cable ? [q.plug.sil, q.boot.sil, q.cable] : [q.jack]).forEach((el) =>
                el.classList.toggle("hi", on),
            );
        if (lit) mark(lit, false);
        lit = pt;
        if (pt) mark(pt, true);
    }
    const first = ports.find((pt) => pt.state === "attention") ?? null;
    light(first);

    const B = register(stage, (dt) => {
        let m = false;
        for (const pt of ports) {
            for (const s of [pt.pull, pt.lx, pt.seat]) if (stepS(s, dt)) m = true;
            if (pt.cable) drawPort(pt);
        }
        return m;
    });
    bag.add(B.unregister);

    // hit test on the face plane, which never moves: the port nearest the pointer across the panel
    const o = P(0, 0, 0),
        ux = P(1, 0, 0),
        uz = P(0, 0, 1);
    const ex = [ux[0] - o[0], ux[1] - o[1]],
        ez = [uz[0] - o[0], uz[1] - o[1]],
        det = ex[0] * ez[1] - ex[1] * ez[0];
    function hit([sx, sy]) {
        const qx = sx - o[0],
            qy = sy - o[1],
            x = (qx * ez[1] - qy * ez[0]) / det,
            z = (ex[0] * qy - ex[1] * qx) / det;
        if (x < X0 - 2 || x > W - X0 + 2 || z < 0 || z > H) return -1;
        return clamp(Math.floor((x - X0) / PITCH), 0, N - 1);
    }
    function retarget() {
        aim(over);
        light(over >= 0 ? ports[over] : first);
        B.wake();
    }
    bag.add(
        pointer(stage, {
            move: (p) => {
                const h = hit(p);
                if (h !== over) {
                    over = h;
                    retarget();
                }
            },
            leave: () => {
                over = -1;
                retarget();
            },
        }),
    );
    bag.add(() => svg.replaceChildren());
    return {
        /** New states for the same ports, live and off swapped only: each changed plug moves on its spring. */
        setStates: (next) => {
            next.forEach((state, p) => (ports[p].seat.t = state === "off" ? 1 : 0));
            B.wake();
        },
        destroy: bag.dispose,
    };
}
