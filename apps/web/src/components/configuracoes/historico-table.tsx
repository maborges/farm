"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";

interface HistoricoItem {
  id: string;
  campo_alterado: string;
  valor_anterior: unknown;
  valor_novo: unknown;
  alterado_por: string | null;
  alterado_em: string;
}

const CAMPO_LABELS: Record<string, string> = {
  ano_agricola: "Ano Agrícola",
  unidade_area: "Unidade de Área",
  moeda: "Moeda",
  fuso_horario: "Fuso Horário",
  idioma: "Idioma",
};

function formatValor(val: unknown): string {
  if (val === null || val === undefined) return "—";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

export function HistoricoTable() {
  const { data: itens = [], isLoading } = useQuery<HistoricoItem[]>({
    queryKey: ["config-historico"],
    queryFn: () => apiFetch("config/historico?limit=50"),
  });

  const columns: ColumnDef<HistoricoItem>[] = [
    {
      id: "campo",
      header: "Campo",
      accessorFn: (row) => CAMPO_LABELS[row.campo_alterado] ?? row.campo_alterado,
      sortable: true,
    },
    {
      id: "anterior",
      header: "Anterior",
      accessorFn: (row) => formatValor(row.valor_anterior),
      cell: (value: any) => <span className="text-muted-foreground font-mono text-xs">{value}</span>,
    },
    {
      id: "novo",
      header: "Novo",
      accessorFn: (row) => formatValor(row.valor_novo),
      cell: (value: any) => <span className="font-mono text-xs">{value}</span>,
    },
    {
      id: "quando",
      header: "Quando",
      accessorFn: (row) => formatDistanceToNow(new Date(row.alterado_em), { addSuffix: true, locale: ptBR }),
      cell: (value: any) => <span className="text-muted-foreground text-xs whitespace-nowrap">{value}</span>,
    },
  ];

  return (
    <div className="space-y-4">
      <DataTable
        data={itens}
        columns={columns}
        isLoading={isLoading}
        searchable={true}
        exportable={true}
        emptyMessage="Nenhuma alteração registrada."
      />
    </div>
  );
}
