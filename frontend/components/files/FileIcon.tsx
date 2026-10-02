import Image from "next/image";

// VS Code Material Icon Theme (material-icon-theme, MIT; licence beside the SVGs in
// public/icons/files). Only the icons generated apps use are copied; the lookup follows the
// theme's own order: exact file name, then extension, then the generic file icon.
const byName: Record<string, string> = {
    ".gitignore": "git",
    ".gitkeep": "git",
    "agents.md": "agent",
    "readme.md": "readme",
    "package.json": "nodejs",
    "package-lock.json": "nodejs",
    "tsconfig.json": "tsconfig",
    "requirements.txt": "python-misc",
    "route.ts": "routing",
    dockerfile: "docker",
    ".env.example": "tune",
};

// <tool>.config.<ext> files, keyed by tool.
const CONFIG_FILE = /^(\w+)\.config\./;
const byConfig: Record<string, string> = {
    vite: "vite",
    next: "next",
    drizzle: "drizzle",
    postcss: "postcss",
    tailwind: "tailwindcss",
    eslint: "eslint",
};

const byExtension: Record<string, string> = {
    tsx: "react_ts",
    ts: "typescript",
    jsx: "react",
    js: "javascript",
    mjs: "javascript",
    py: "python",
    css: "css",
    html: "html",
    json: "json",
    md: "markdown",
    sql: "database",
    ini: "settings",
    yml: "yaml",
    yaml: "yaml",
    svg: "svg",
    png: "image",
    jpg: "image",
    jpeg: "image",
    webp: "image",
    txt: "document",
    sh: "console",
};

// Folder name to its Material folder icon (folder-<icon>.svg and folder-<icon>-open.svg).
const folderIcons: Record<string, string> = {
    api: "api",
    app: "app",
    assets: "resource",
    backend: "server",
    components: "components",
    config: "config",
    css: "css",
    db: "database",
    drizzle: "drizzle",
    frontend: "client",
    hooks: "hook",
    lib: "lib",
    meta: "meta",
    migrations: "migrations",
    notes: "docs",
    pages: "views",
    public: "public",
    routes: "routes",
    scripts: "scripts",
    services: "controller",
    src: "src",
    styles: "css",
    tests: "test",
    types: "typescript",
    utils: "utils",
    views: "views",
};

function fileIcon(filename: string) {
    const name = (filename.split("/").pop() ?? filename).toLowerCase();
    return (
        byName[name] ??
        byConfig[name.match(CONFIG_FILE)?.[1] ?? ""] ??
        byExtension[name.split(".").pop() ?? ""] ??
        "file"
    );
}

function Svg({ icon }: { icon: string }) {
    return (
        <Image
            src={`/icons/files/${icon}.svg`}
            alt=""
            width={16}
            height={16}
            // Lazy loading only makes 16px icons pop in after their rows; load them with the tree.
            loading="eager"
        />
    );
}

export function FileIcon({ filename }: { filename: string }) {
    // Mention paths and composer labels end in "/" for folders.
    if (filename.endsWith("/")) return <FolderIcon name={filename} />;
    return <Svg icon={fileIcon(filename)} />;
}

export function FolderIcon({ name, open }: { name: string; open?: boolean }) {
    // The icon is keyed by the last name.
    const icon = folderIcons[name.replace(/\/$/, "").split("/").pop()?.toLowerCase() ?? ""];
    return <Svg icon={`${icon ? `folder-${icon}` : "folder"}${open ? "-open" : ""}`} />;
}
