"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface PropriedadeFiltersProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function PropriedadeFilters({ value, onChange, className }: PropriedadeFiltersProps) {
  const filters = [
    { value: "all", label: "Todos" },
    { value: "true", label: "Ativos" },
    { value: "false", label: "Inativos" },
  ];

  return (
    <div className={cn("flex gap-2", className)}>
      {filters.map((filter) => (
        <Button
          key={filter.value}
          variant={value === filter.value ? "default" : "outline"}
          size="sm"
          onClick={() => onChange(filter.value)}
        >
          {filter.label}
        </Button>
      ))}
    </div>
  );
}
