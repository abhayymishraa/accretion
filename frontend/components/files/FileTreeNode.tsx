"use client";

import { File, Folder } from "@/components/ui/file-tree";

import type { FileNode } from "@/types/file.type";
import { FileIcon, FolderIcon } from "./FileIcon";
export function FileTreeNode({ node }: { node: FileNode }) {
    if (!node.isDirectory)
        return <File value={node.path} name={node.name} icon={<FileIcon filename={node.name} />} />;
    return (
        <Folder
            value={node.path}
            name={node.name}
            icon={<FolderIcon name={node.name} />}
            openIcon={<FolderIcon name={node.name} open />}
        >
            {node.children?.map((child) => (
                <FileTreeNode key={child.path} node={child} />
            ))}
        </Folder>
    );
}
