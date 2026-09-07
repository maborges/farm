"use client";

import { Switch } from "@/components/ui/switch";

type MapVisualizationToggleProps = {
    checked: boolean;
    onCheckedChange: (checked: boolean) => void;
    className?: string;
};

export function MapVisualizationToggle({ checked, onCheckedChange, className }: MapVisualizationToggleProps) {
    return (
        <div className={`pointer-events-auto flex items-center gap-2 rounded-sm border bg-background/95 px-3 py-2 shadow-lg backdrop-blur-sm ${className ?? ""}`.trim()}>
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Relevo</span>
            <Switch
                checked={checked}
                onCheckedChange={onCheckedChange}
                aria-label="Alternar visualização entre satélite e relevo"
            />
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Satélite</span>
        </div>
    );
}
