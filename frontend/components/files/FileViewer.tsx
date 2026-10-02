"use client";

import { FileIcon } from "./FileIcon";

import { ErrorBox } from "@/components/ui/ErrorBox";
import { Tree } from "@/components/ui/file-tree";
import Editor from "@monaco-editor/react";
import { Download, FileCode, Loader2 } from "lucide-react";

import type { OpenedFile } from "@/hooks/chat/useWorkspaceLayout";
import { useFileViewer } from "@/hooks/files/useFileViewer";
import { buildFileTree, getLanguageFromPath } from "@/lib/files/tree";
import { FileTreeNode } from "./FileTreeNode";
interface FileViewerProps {
    files: string[];
    projectId: string;
    revisionId?: string | null;
    openedFile?: OpenedFile | null;
}

export function FileViewer({ files, projectId, revisionId, openedFile }: FileViewerProps) {
    const {
        selectedFile,
        setSelectedFile,
        fileContent,
        isLoadingFile,
        downloadError,
        binary,
        handleDownloadFile,
    } = useFileViewer({ files, projectId, revisionId, openedFile });
    const fileTree = buildFileTree(files);
    if (files.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <FileCode className="mb-4 size-9 opacity-50" />
                <p className="text-sm">No files available yet</p>
                <p className="text-xs mt-1">Files will appear once your app is built</p>
            </div>
        );
    }

    return (
        <div className="h-full flex">
            {/* File Tree Sidebar */}
            <div className="ember-file-tree w-47.5 min-w-30 max-w-[38%] shrink-0 max-md:w-[135px] border-r border-border overflow-y-auto bg-surface-1">
                <div className="sticky top-0 z-10 border-b border-border bg-surface-1 p-3">
                    <h3 className="mb-2 text-sm font-semibold text-foreground">Files</h3>
                    <p className="text-muted-foreground text-xs">
                        {files.length} file{files.length !== 1 ? "s" : ""}
                    </p>
                </div>

                <div className="px-3 [&>[data-error-box]]:my-2">
                    <ErrorBox message={downloadError} />
                </div>
                <Tree
                    selectedId={selectedFile}
                    onSelectFile={setSelectedFile}
                    initialExpandedItems={fileTree
                        .filter((node) => node.isDirectory)
                        .map((node) => node.path)}
                >
                    {fileTree.map((node) => (
                        <FileTreeNode key={node.path} node={node} />
                    ))}
                </Tree>
            </div>

            {/* Editor Area */}
            <div className="ember-file-editor min-w-0 flex-1 flex flex-col">
                {selectedFile ? (
                    <>
                        {/* Editor Header */}
                        <div className="ember-file-header flex min-w-0 flex-wrap items-center justify-between gap-2 border-b border-border bg-surface-1 px-3 py-2">
                            <div className="flex items-center gap-2">
                                <FileIcon filename={selectedFile} />
                                <span className="ember-file-path min-w-0 wrap-anywhere text-[11px] text-foreground font-mono">
                                    {selectedFile}
                                </span>
                            </div>
                            <button
                                onClick={handleDownloadFile}
                                className="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-[6px] bg-surface-2 px-2.5 text-[11.5px] text-muted-foreground [transition:background-color_130ms_ease,color_130ms_ease] pointer-fine:hover:bg-accent pointer-fine:hover:text-accent-foreground"
                            >
                                <Download className="w-3 h-3" />
                                Download
                            </button>
                        </div>

                        {/* Monaco Editor */}
                        <div className="flex-1 relative">
                            {isLoadingFile ? (
                                <div className="absolute inset-0 flex items-center justify-center bg-surface-1">
                                    <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                                </div>
                            ) : binary ? (
                                <div className="p-6 text-sm text-muted-foreground">
                                    Binary or large file. Download to view the original.
                                </div>
                            ) : (
                                <Editor
                                    height="100%"
                                    language={getLanguageFromPath(selectedFile)}
                                    value={fileContent}
                                    theme="vs-dark"
                                    options={{
                                        readOnly: true,
                                        minimap: { enabled: false },
                                        fontSize: 13,
                                        lineNumbers: "on",
                                        scrollBeyondLastLine: false,
                                        automaticLayout: true,
                                        wordWrap: "on",
                                        padding: { top: 16, bottom: 16 },
                                    }}
                                    loading={
                                        <div className="flex items-center justify-center h-full">
                                            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                                        </div>
                                    }
                                />
                            )}
                        </div>
                    </>
                ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                        <div className="text-center">
                            <FileCode className="w-12 h-12 mx-auto mb-4 opacity-50" />
                            <p className="text-sm">Select a file to view</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
