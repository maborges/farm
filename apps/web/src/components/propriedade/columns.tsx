"use client";

import type { ColumnDef } from "@/components/ui/data-table";
import type { PropriedadeResponse } from "@farm/zod-schemas";
import { Badge } from "@/components/ui/badge";
import { PropriedadeActions } from "./actions";
import { StatusBadge } from "@/components/ui/status-badge";

function formatCPF(value: string): string {
  if (!value) return "-";
  const digits = value.replace(/\D/g, "");
  return digits.length <= 11
    ? digits.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4")
    : digits.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");
}

interface UsePropriedadeColumnsProps {
  onView: (row: PropriedadeResponse) => void;
  onEdit: (row: PropriedadeResponse) => void;
  onDelete: (row: PropriedadeResponse) => void;
}

export function usePropriedadeColumns({
  onView,
  onEdit,
  onDelete,
}: UsePropriedadeColumnsProps): ColumnDef<PropriedadeResponse>[] {
  return [
    {
      id: "nome",
      header: "Nome",
      accessorFn: (row) => row.nome,
      sortable: true,
      cell: (value: string, row: PropriedadeResponse) => (
        <div className="flex items-center gap-2">
          {row.cor && (
            <div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: row.cor }}
            />
          )}
          <div className="min-w-0">
            <div className="font-medium truncate">{value}</div>
            {row.nome_fantasia && (
              <div className="text-xs text-muted-foreground truncate">
                {row.nome_fantasia}
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      id: "cpf_cnpj",
      header: "CNPJ/CPF",
      accessorKey: "cpf_cnpj",
      sortable: true,
      cell: (value: string) => (
        <span className="font-mono text-sm">
          {value ? formatCPF(value) : "-"}
        </span>
      ),
    },
    {
      id: "regime_tributario",
      header: "Regime",
      accessorKey: "regime_tributario",
      sortable: true,
      cell: (value: string) =>
        value ? (
          <Badge variant="secondary" className="text-xs">
            {value.replace(/_/g, " ")}
          </Badge>
        ) : (
          <span className="text-muted-foreground text-xs">-</span>
        ),
    },
    {
      id: "contato",
      header: "Contato",
      accessorFn: (row) => row.telefone || row.email || "—",
      sortable: false,
      cell: (_, row: PropriedadeResponse) => (
        <span className="text-sm text-muted-foreground">
          {row.telefone || row.email || "—"}
        </span>
      ),
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "ativo",
      sortable: true,
      cell: (value: boolean) =>
        value ? (
          <StatusBadge status="ativo" />
        ) : (
          <StatusBadge status="inativo" />
        ),
    },
    {
      id: "acoes",
      header: "",
      sortable: false,
      filterable: false,
      exportable: false,
      cell: (_, row: PropriedadeResponse) => (
        <PropriedadeActions
          row={row}
          onView={onView}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ),
    },
  ];
}
