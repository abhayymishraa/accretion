/**
 * Deck: a tray of browser windows, one card per step of a plan, each with its
 * title bar, three dots and the lines of a page. Built cards lean far back,
 * filed; cards still to build stand near upright, and the next one holds the
 * bright edge. The pointer picks a card: it stands up and lifts, the ones in
 * front lean forward and the ones behind lean back, staggered outwards from it.
 */
import HL from "@/components/mcp/hairline/kernel.js";

const {
    Cam,
    clamp,
    facing,
    fillet,
    fit,
    hull,
    open,
    poly,
    proj,
    rad,
    ringAt,
    rrect,
    run,
    seg,
    tdone,
    tset,
    tval,
    tween,
    disposer,
    mk,
    place,
    pointer,
    register,
} = HL;

const W = 84,
    H = 56,
    G = 13,
    TK = 1.4,
    REST = -10,
    FILED = -34,
    BACK = -40,
    FWD = 20,
    LIFT = 14;
const X0 = -5,
    X1 = W + 5,
    Y0 = -9,
    WH = 18,
    WR = 6,
    WT = 2.4;
const LR = (pts) => (pts[0][0] <= pts[pts.length - 1][0] ? pts : pts.slice().reverse());

/** The tray, which never moves: `far` is painted before the cards, `near` after them. */
function tray(P, front, outer, inner) {
    const far = [
        [poly(hull(ringAt(P, outer, 0).concat(ringAt(P, outer, WH)))), "sil"],
        [poly(ringAt(P, inner, WH)), "nf"],
        [
            open(
                ringAt(
                    P,
                    run(inner, (q) => !front(q)),
                    2.5,
                ),
            ),
            "nf lo",
        ],
    ];
    const iF = LR(ringAt(P, run(inner, front), WH)),
        oT = LR(ringAt(P, run(outer, front), WH));
    const oB = LR(ringAt(P, run(outer, front), 0));
    const near = [
        [poly([...iF, oT[oT.length - 1], ...oB.slice().reverse(), oT[0]]), "fo"],
        [open(oT), "nf lo"],
        [open(iF), "nf"],
        [open([oT[0], ...oB, oT[oT.length - 1]]), "nf sil"],
    ];
    return { far, near };
}

/** Card i leaning th degrees and lifted by `lift`: its paths and where its three title-bar dots sit. */
function pose(P, i, shape, th, lift) {
    const yb = i * G,
        s = Math.sin(rad(th)),
        c = Math.cos(rad(th));
    const w = (u, v) => P(u, yb + v * s, v * c + lift);
    const wb = (u, v) => P(u, yb + v * s - TK * c, v * c + TK * s + lift);
    return {
        back: poly(shape.map((p) => wb(p[0], p[1]))),
        face: poly(shape.map((p) => w(p[0], p[1]))),
        bar: seg(w(4, H - 10), w(W - 4, H - 10)),
        lines: [H - 20, H - 27, H - 34, H - 41]
            .map((v, k) => seg(w(8, v), w(k % 2 ? W - 30 : W - 12, v)))
            .join(""),
        dots: [8, 13, 18].map((u) => w(u, H - 5)),
    };
}

export function mount({ stage, svg }, stag, done) {
    const bag = disposer();
    const steps = done.slice(0, 8);
    const N = steps.length;
    const Y1 = (N - 1) * G + 9;
    const restTh = steps.map((built) => (built ? FILED : REST));
    const C = Cam(45, 0.5, clamp(270 / (N * G + 70), 1.35, 2.1));
    fit(
        C,
        [
            [X0, Y0 - 40, 0],
            [X1, Y1, -8],
            [X1, Y0, 0],
            [X0, Y1, 0],
            [X0, Y0, H],
            [X1, Y0, H + LIFT],
        ],
        200,
        166,
    );
    const P = proj(C),
        front = facing(C);
    const outer = rrect(X0, Y0, X1, Y1, WR, 6),
        inner = rrect(X0 + WT, Y0 + WT, X1 - WT, Y1 - WT, WR - WT, 6);
    const paths = tray(P, front, outer, inner);
    const shape = fillet(
        [
            [0, 0],
            [W, 0],
            [W, H],
            [0, H],
        ],
        [1, 1, 3.2, 3.2],
    );

    const g = mk("g", {}, svg);
    for (const [d, cls] of paths.far) mk("path", { d, class: cls }, g);
    const cards = steps.map((_, i) => {
        const grp = mk("g", {}, g);
        const back = mk("path", { class: "lo" }, grp),
            face = mk("path", { class: "sil" }, grp);
        const bar = mk("path", { class: "nf" }, grp),
            lines = mk("path", { class: "nf lo" }, grp);
        const dots = [0, 1, 2].map(() => mk("circle", { r: 1.05, class: "dot off" }, grp));
        return { back, face, bar, lines, dots, a: tween(restTh[i]), z: tween(0) };
    });
    for (const [d, cls] of paths.near) mk("path", { d, class: cls }, g);
    const next = steps.indexOf(false) < 0 ? N - 1 : steps.indexOf(false);

    function draw(i, th, lift) {
        const cd = cards[i],
            q = pose(P, i, shape, th, lift);
        cd.back.setAttribute("d", q.back);
        cd.face.setAttribute("d", q.face);
        cd.bar.setAttribute("d", q.bar);
        cd.lines.setAttribute("d", q.lines);
        cd.dots.forEach((el, k) => place(el, q.dots[k]));
    }
    const B = register(stage, (_dt, now) => {
        let moving = false;
        cards.forEach((cd, i) => {
            draw(i, tval(cd.a, now), tval(cd.z, now));
            if (!tdone(cd.a, now) || !tdone(cd.z, now)) moving = true;
        });
        return moving;
    });
    bag.add(B.unregister);

    // Hit test on the rest pose: the card whose resting top edge is nearest the pointer.
    const tops = steps.map((_, i) =>
        P(W / 2, i * G + H * Math.sin(rad(restTh[i])), H * Math.cos(rad(restTh[i]))),
    );
    const span = [P(0, Y1, 0)[0] - 6, P(W, Y0, 0)[0] + 6];
    function hit([x, y]) {
        if (x < span[0] || x > span[1]) return -1;
        let best = -1,
            far = Infinity;
        tops.forEach((t, i) => {
            const d = Math.abs(t[1] - y);
            if (y >= t[1] - 4 && d < far) [best, far] = [i, d];
        });
        return best;
    }

    let act = -1;
    function setActive(a) {
        if (a === act) return;
        const now = performance.now(),
            from = a >= 0 ? a : act;
        act = a;
        cards.forEach((cd, i) => {
            const delay = Math.abs(i - from) * stag;
            const th = a < 0 ? restTh[i] : i < a ? Math.min(BACK, restTh[i]) : i > a ? FWD : 0;
            tset(cd.a, th, now, delay);
            tset(cd.z, a === i ? LIFT : 0, now, delay);
            const lit = a < 0 ? i === next : i === a;
            cd.face.classList.toggle("hi", lit);
            cd.bar.classList.toggle("hi", lit);
            cd.dots.forEach((el) => el.classList.toggle("off", !lit));
        });
        B.wake();
    }
    setActive(-2);
    act = -1;
    bag.add(pointer(stage, { move: (p) => setActive(hit(p)), leave: () => setActive(-1) }));
    bag.add(() => svg.replaceChildren());
    return { destroy: bag.dispose };
}
