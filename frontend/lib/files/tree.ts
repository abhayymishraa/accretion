import type { FileNode } from "@/types/file.type";

export function buildFileTree(files: string[]): FileNode[] {
    const root: FileNode[] = [];

    files.forEach((filePath) => {
        const parts = filePath.split("/");
        let currentLevel = root;
        let currentPath = "";

        parts.forEach((part, index) => {
            currentPath += (index === 0 ? "" : "/") + part;
            const isLastPart = index === parts.length - 1;

            let existingNode = currentLevel.find((node) => node.name === part);

            if (!existingNode) {
                existingNode = {
                    name: part,
                    path: currentPath,
                    isDirectory: !isLastPart,
                    children: !isLastPart ? [] : undefined,
                };
                currentLevel.push(existingNode);
            }

            if (!isLastPart && existingNode.children) {
                currentLevel = existingNode.children;
            }
        });
    });

    sortTree(root);
    return root;
}

// Like an IDE: folders before files, then by name, ignoring case, with numbers in order.
const byName = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

function sortTree(nodes: FileNode[]) {
    nodes.sort((a, b) =>
        a.isDirectory === b.isDirectory ? byName.compare(a.name, b.name) : a.isDirectory ? -1 : 1,
    );
    for (const node of nodes) if (node.children) sortTree(node.children);
}

export function getLanguageFromPath(filePath: string): string {
    const ext = filePath.split(".").pop()?.toLowerCase();
    const languageMap: Record<string, string> = {
        js: "javascript",
        jsx: "javascript",
        ts: "typescript",
        tsx: "typescript",
        json: "json",
        html: "html",
        css: "css",
        scss: "scss",
        py: "python",
        md: "markdown",
        yml: "yaml",
        yaml: "yaml",
        xml: "xml",
        sh: "shell",
    };

    return languageMap[ext || ""] || "plaintext";
}
