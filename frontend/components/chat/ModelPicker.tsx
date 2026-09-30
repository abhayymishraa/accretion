import { ChevronDown } from "lucide-react";

import type { ModelOption } from "@/types/models.type";

interface ModelPickerProps {
    models: ModelOption[];
    value: string;
    disabled?: boolean;
    onChange: (value: string) => void;
}

// Native select: components/ui has no select primitive, and the platform control is accessible.
export function ModelPicker({ models, value, disabled = false, onChange }: ModelPickerProps) {
    return (
        <label className="relative flex max-w-[10rem] min-w-0 items-center text-[12.5px] text-muted-foreground">
            <span className="sr-only">Model</span>
            <select
                value={value}
                disabled={disabled}
                onChange={(event) => onChange(event.target.value)}
                className="h-8 w-full cursor-pointer appearance-none truncate rounded-md border border-input bg-transparent pr-8 pl-2.5 text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none disabled:opacity-50"
            >
                <option value="auto">Auto (recommended)</option>
                {models.map((model) => (
                    <option key={model.id} value={model.id}>
                        {model.name} · {model.speed}, {model.cost}
                    </option>
                ))}
            </select>
            <ChevronDown
                aria-hidden="true"
                className="pointer-events-none absolute right-2.5 size-3.5 text-muted-foreground"
            />
        </label>
    );
}
