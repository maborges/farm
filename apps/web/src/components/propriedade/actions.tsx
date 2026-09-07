"use client";

import { Eye, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PropriedadeResponse } from "@farm/zod-schemas";

interface PropriedadeActionsProps {
  row: PropriedadeResponse;
  onView: (row: PropriedadeResponse) => void;
  onEdit: (row: PropriedadeResponse) => void;
  onDelete: (row: PropriedadeResponse) => void;
}

export function PropriedadeActions({ row, onView, onEdit, onDelete }: PropriedadeActionsProps) {
  return (
    <div className="flex items-center gap-0 justify-end">
      <Button
        variant="ghost"
        size="icon"
        className="size-7 text-primary hover:text-primary"
        onClick={() => onView(row)}
        aria-label="Visualizar"
      >
        <Eye className="size-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="size-7 text-primary hover:text-primary"
        onClick={() => onEdit(row)}
        aria-label="Editar"
      >
        <Pencil className="size-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="size-7 text-destructive hover:text-destructive"
        onClick={() => onDelete(row)}
        aria-label="Excluir"
      >
        <Trash2 className="size-3.5" />
      </Button>
    </div>
  );
}
