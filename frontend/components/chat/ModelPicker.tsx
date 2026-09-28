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
        <label className="flex min-w-0 items-center text-[12.5px] text-muted-foreground">
            <span className="sr-only">Model</span>
            <select
                value={value}
                disabled={disabled}
                onChange={(event) => onChange(event.target.value)}
                className="h-8 w-full max-w-[10rem] truncate rounded-md border border-input bg-transparent px-2 text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none disabled:opacity-50"
            >
                <option value="auto">Auto (recommended)</option>
                {models.map((model) => (
                    <option key={model.id} value={model.id}>
                        {model.name} · {model.speed}, {model.cost}
                    </option>
                ))}
            </select>
        </label>
    );
}
