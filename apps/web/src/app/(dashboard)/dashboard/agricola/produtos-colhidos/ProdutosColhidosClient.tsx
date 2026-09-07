"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Button } from "@/components/ui/button";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Wheat, Eye } from "lucide-react";
import type { ProdutoColhido } from "@farm/zod-schemas";

function toBRL(v: number | null | undefined) {
  return v == null ? "—" : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function ProdutosColhidosClient() {
  const { data: lotes = [], isLoading } = useQuery<ProdutoColhido[]>({
    queryKey: ["agricola", "produtos-colhidos"],
    queryFn: () => apiFetch("/agricola/produtos-colhidos/"),
  });

  const columns: ColumnDef<ProdutoColhido>[] = [
    {
      id: "data_entrada",
      header: "Data de Entrada",
      accessorKey: "data_entrada",
      sortable: true,
      cell: (v) => new Date(v).toLocaleDateString("pt-BR", { timeZone: "UTC" }),
    },
    {
      id: "quantidade",
      header: "Quantidade",
      accessorKey: "quantidade",
      sortable: true,
      cell: (v, row) => `${Number(v).toLocaleString("pt-BR")} ${row.unidade}`,
    },
    {
      id: "custo_unitario_producao",
      header: "Custo Unit. (colheita)",
      accessorKey: "custo_unitario_producao",
      cell: (v) => toBRL(v),
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "status",
      filterable: true,
      cell: (v) => <WorkflowStatusBadge status={v} />,
    },
    {
      id: "acoes",
      header: "",
      exportable: false,
      sortable: false,
      filterable: false,
      cell: (_, row) => (
        <div className="flex items-center gap-0 justify-end">
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-primary hover:text-primary"
            aria-label="Visualizar"
            asChild
          >
            <Link href={`/dashboard/agricola/produtos-colhidos/${row.id}`}>
              <Eye className="size-3.5" />
            </Link>
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Produtos Colhidos"
        description="Lotes de colheita — consulte custo e margem apurados por lote"
        icon={<Wheat className="size-5" />}
      />
      <DataTable
        data={lotes}
        columns={columns}
        isLoading={isLoading}
        searchPlaceholder="Buscar lote..."
        exportFileName="produtos-colhidos"
        emptyMessage="Nenhum lote de colheita encontrado."
      />
    </div>
  );
}
