"use client";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { ListFilter } from "lucide-react";

export interface MultiSelectOption {
  value: string;
  label: string;
}

export function MultiSelectFilter({
  label,
  options,
  selected,
  onChange,
  className,
}: {
  label: string;
  options: MultiSelectOption[];
  selected: string[];
  onChange: (values: string[]) => void;
  className?: string;
}) {
  function toggle(value: string) {
    onChange(
      selected.includes(value)
        ? selected.filter((v) => v !== value)
        : [...selected, value]
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className={className ?? "h-9 gap-2"}>
          <ListFilter className="size-3.5" />
          {label}
          {selected.length > 0 && (
            <Badge variant="secondary" className="h-4 px-1.5 text-[10px] font-normal">
              {selected.length}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-2" align="start">
        <div className="max-h-64 overflow-y-auto space-y-0.5">
          {options.length === 0 ? (
            <p className="text-xs text-muted-foreground px-2 py-1.5">Nenhuma opção disponível.</p>
          ) : (
            options.map((opt) => (
              <label
                key={opt.value}
                className="flex items-center gap-2 px-2 py-1.5 rounded-sm text-sm hover:bg-muted/60 cursor-pointer"
              >
                <Checkbox
                  checked={selected.includes(opt.value)}
                  onCheckedChange={() => toggle(opt.value)}
                />
                <span className="truncate">{opt.label}</span>
              </label>
            ))
          )}
        </div>
        {selected.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full mt-1 h-7 text-xs text-muted-foreground"
            onClick={() => onChange([])}
          >
            Limpar seleção
          </Button>
        )}
      </PopoverContent>
    </Popover>
  );
}
