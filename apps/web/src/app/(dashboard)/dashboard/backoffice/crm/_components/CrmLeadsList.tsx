"use client";

import { DataTable, ColumnDef } from "@/components/ui/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Eye } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

import { Lead, LeadListData, ORIGENS } from "./types";
import { StatusBadge } from "@/components/ui/status-badge";

interface CrmLeadsListProps {
  statusFilter: string;
  setStatusFilter: (v: string) => void;
  leadsList: LeadListData | undefined;
  leadsLoading: boolean;
  onLeadClick: (lead: Lead) => void;
  formatCurrency: (val: number) => string;
}

export function CrmLeadsList({
  statusFilter,
  setStatusFilter,
  leadsList,
  leadsLoading,
  onLeadClick,
  formatCurrency,
}: CrmLeadsListProps) {

  const leadsColumns: ColumnDef<Lead>[] = [
      {
          id: "lead",
          header: "Lead",
          accessorKey: "nome",
          cell: (value, row) => (
              <div>
                  <p className="font-medium text-sm">{row.nome}</p>
                  <div className="flex gap-2 text-[10px] text-muted-foreground">
                      {row.email && <span>{row.email}</span>}
                      {row.telefone && <span>{row.telefone}</span>}
                  </div>
              </div>
          ),
      },
      {
          id: "empresa",
          header: "Empresa",
          accessorKey: "empresa",
          cell: (value) => value || "—",
      },
      {
          id: "estagio",
          header: "Estágio",
          accessorKey: "estagio",
          sortable: false,
          filterable: false,
          cell: (value, row) => {
              if (!row.estagio) return null;
              return (
                  <Badge
                      variant="outline"
                      className="text-xs"
                      style={{
                          backgroundColor: row.estagio.cor + "22",
                          color: row.estagio.cor,
                          borderColor: row.estagio.cor + "55",
                      }}
                  >
                      {row.estagio.nome}
                  </Badge>
              );
          },
      },
      {
          id: "origem",
          header: "Origem",
          accessorKey: "origem",
          sortable: false,
          filterable: false,
          cell: (value, row) => {
              const origemConfig = ORIGENS[row.origem] ?? ORIGENS.manual;
              return (
                  <Badge variant="outline" className={`text-xs ${origemConfig.color}`}>
                      {origemConfig.label}
                  </Badge>
              );
          },
      },
      {
          id: "valor",
          header: "Valor",
          accessorKey: "valor_estimado",
          cell: (value) => (value ? formatCurrency(value) : "—"),
      },
      {
          id: "status",
          header: "Status",
          accessorKey: "status",
          sortable: false,
          filterable: false,
          cell: (value, row) => (
              row.status === "ativo" ? (
                  <StatusBadge status="ativo" />
              ) : row.status === "convertido" ? (
                  <Badge className="bg-blue-500/10 text-blue-700 border-blue-200 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30">Convertido</Badge>
              ) : (
                  <Badge className="bg-red-500/10 text-red-700 border-red-200 dark:bg-red-500/20 dark:text-red-100 dark:border-red-400/30">Perdido</Badge>
              )
          ),
      },
      {
          id: "atualizado",
          header: "Atualizado",
          accessorKey: "updated_at",
          cell: (value) => (
              <span className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(value), { addSuffix: true, locale: ptBR })}
              </span>
          ),
      },
      {
          id: "acao",
          header: "",
          sortable: false,
          filterable: false,
          exportable: false,
          cell: (_, row) => (
              <Button
                  size="icon"
                  variant="ghost"
                  className="size-7 text-primary hover:text-primary"
                  onClick={(e) => {
                      e.stopPropagation();
                      onLeadClick(row);
                  }}
              >
                  <Eye className="size-3.5" />
              </Button>
          ),
      },
  ];

  return (
    <div className="space-y-4">
        <div className="flex gap-3 justify-end">
            <Select value={statusFilter || "all"} onValueChange={(v: string) => setStatusFilter(v === "all" ? "" : v)}>
                <SelectTrigger className="w-44">
                    <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="ativo">Ativos</SelectItem>
                    <SelectItem value="aprovado">Aprovados</SelectItem>
                    <SelectItem value="convertido">Convertidos</SelectItem>
                    <SelectItem value="perdido">Perdidos</SelectItem>
                </SelectContent>
            </Select>
        </div>

        {leadsLoading ? (
            <div className="flex justify-center py-12">
                <Skeleton className="h-6 w-48" />
            </div>
        ) : (
            <DataTable
                data={leadsList?.items ?? []}
                columns={leadsColumns}
                searchPlaceholder="Buscar por nome, email, empresa..."
                exportFileName={`leads-${statusFilter || "todos"}-${new Date().toISOString().split('T')[0]}`}
                onRowClick={onLeadClick}
                emptyMessage="Nenhum lead encontrado."
            />
        )}
    </div>
  );
}
