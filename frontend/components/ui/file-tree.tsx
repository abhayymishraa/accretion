"use client";

// Adapted from Magic UI File Tree (MIT). See MAGIC-UI-LICENSE.
// https://github.com/magicuidesign/magicui/blob/52bc69354621e5cd7c9bc84a0e42b42f2d0c07b1/apps/www/registry/magicui/file-tree.tsx
// Uses the upstream accordion/context composition with controlled file selection,
// native scrolling, and Ember styling. Folder clicks never select a source file.
import * as Accordion from "@radix-ui/react-accordion";
import { ChevronRight } from "lucide-react";
import { createContext, useContext, useState, type ReactNode } from "react";

const rowClassName = [
    "flex w-full min-w-0 min-h-[34px] items-center gap-[7px] rounded-[6px] px-[8px] py-[7px]",
    "cursor-pointer text-left text-[12px] leading-[1.4] text-muted-foreground",
    "transition-[background,color] duration-[120ms] ease-[ease] motion-reduce:transition-none",
    "[&:hover]:bg-surface-2 [&:hover]:text-foreground",
    "data-[selected=true]:bg-accent data-[selected=true]:text-accent-foreground",
    "data-[selected=true]:[&:hover]:bg-accent data-[selected=true]:[&:hover]:text-accent-foreground",
    "focus-visible:outline-2 focus-visible:outline-solid focus-visible:outline-ring focus-visible:-outline-offset-2",
    "[&_svg]:size-[14px] [&_svg]:flex-[0_0_14px] [@media(pointer:coarse)]:min-h-[44px]",
].join(" ");

interface TreeContextValue {
    selectedId: string | null;
    expandedItems: string[];
    toggleFolder: (id: string) => void;
    selectFile: (id: string) => void;
}

const TreeContext = createContext<TreeContextValue | null>(null);

function useTree() {
    const context = useContext(TreeContext);
    if (!context) throw new Error("File tree components must be inside a Tree");
    return context;
}

export function Tree({
    children,
    selectedId,
    initialExpandedItems,
    onSelectFile,
}: {
    children: ReactNode;
    selectedId: string | null;
    initialExpandedItems: string[];
    onSelectFile: (id: string) => void;
}) {
    const [expandedItems, setExpandedItems] = useState(initialExpandedItems);
    const toggleFolder = (id: string) =>
        setExpandedItems((items) =>
            items.includes(id) ? items.filter((item) => item !== id) : [...items, id],
        );

    return (
        <TreeContext.Provider
            value={{ selectedId, expandedItems, toggleFolder, selectFile: onSelectFile }}
        >
            <nav className="min-w-0 p-[8px]" aria-label="Project files">
                <Accordion.Root
                    type="multiple"
                    value={expandedItems}
                    className="flex flex-col gap-[2px]"
                >
                    {children}
                </Accordion.Root>
            </nav>
        </TreeContext.Provider>
    );
}

export function Folder({
    value,
    name,
    icon,
    openIcon,
    children,
}: {
    value: string;
    name: string;
    icon: ReactNode;
    openIcon: ReactNode;
    children: ReactNode;
}) {
    const { expandedItems, toggleFolder } = useTree();
    const expanded = expandedItems.includes(value);
    return (
        <Accordion.Item value={value} className="min-w-0">
            <Accordion.Header>
                <Accordion.Trigger
                    className={`${rowClassName} group`}
                    onClick={() => toggleFolder(value)}
                    title={value}
                >
                    <ChevronRight
                        className="transition-transform duration-[140ms] ease-[var(--ease-out)] group-data-[state=open]:rotate-90 motion-reduce:transition-none"
                        aria-hidden="true"
                    />
                    {expanded ? openIcon : icon}
                    <span className="min-w-0 truncate">{name}</span>
                </Accordion.Trigger>
            </Accordion.Header>
            <Accordion.Content className="overflow-hidden">
                <Accordion.Root
                    type="multiple"
                    value={expandedItems}
                    className="ml-[14px] border-l border-border pl-[6px]"
                >
                    {children}
                </Accordion.Root>
            </Accordion.Content>
        </Accordion.Item>
    );
}

export function File({ value, name, icon }: { value: string; name: string; icon: ReactNode }) {
    const { selectedId, selectFile } = useTree();
    return (
        <button
            type="button"
            className={rowClassName}
            data-selected={selectedId === value}
            aria-current={selectedId === value ? "true" : undefined}
            onClick={() => selectFile(value)}
            title={value}
        >
            <span className="size-[14px] flex-[0_0_14px]" aria-hidden="true" />
            {icon}
            <span className="min-w-0 truncate">{name}</span>
        </button>
    );
}
