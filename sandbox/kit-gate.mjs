// Kit gate (spec 8, "green on day one"): run inside a template build for one kit.
// Runs install, typecheck, build and migrate, starts every service, waits for each
// ready path, then stops them. Any failure exits non-zero and fails the template build.
// Usage: node kit-gate.mjs /opt/accretion/kits/<id>
import { execSync, spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.argv[2];
const stack = JSON.parse(readFileSync(join(root, "stack.json"), "utf8"));
const env = { ...process.env, ...JSON.parse(process.env.KIT_GATE_ENV || "{}") };
const run = (cmd) => cmd && execSync(cmd, { cwd: root, env, stdio: "inherit", shell: "/bin/bash" });

run(stack.install);
run(stack.typecheck);
run(stack.build);
run(stack.migrate);
const children = stack.services.map((service) =>
    spawn("/bin/bash", ["-c", service.start], { cwd: join(root, service.cwd), env, stdio: "inherit", detached: true }),
);
const ready = async (service) => {
    const deadline = Date.now() + 90_000;
    while (Date.now() < deadline) {
        try {
            const response = await fetch(`http://127.0.0.1:${service.port}${service.ready}`);
            if (response.ok) return;
        } catch {
            // Not listening yet.
        }
        await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    throw new Error(`${stack.id}: ${service.name} never answered ${service.ready}`);
};
try {
    for (const service of stack.services) await ready(service);
    console.log(`kit ${stack.id}: green`);
} finally {
    // Services are shells with dev servers under them: stop each whole process group.
    for (const child of children) process.kill(-child.pid, "SIGTERM");
}
