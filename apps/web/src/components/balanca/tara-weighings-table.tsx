"use client";

import { useQuery } from "@tanstack/react-query";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { apiFetch } from "@/lib/api";

type UnknownRecord = Record<string, unknown>;

interface TaraWeighing {
  id: string;
  local_id: string;
  etapa: string;
  peso_aferido_kg: number | string;
  peso_informado_kg?: number | string | null;
  peso_tara_kg?: number | string | null;
  captured_at: string;
  contexto?: UnknownRecord | null;
}

interface TaraWeighingPage {
  items: TaraWeighing[];
  next_cursor: string | null;
}

const etapaLabels: Record<string, string> = {
  CHEGADA: "Chegada",
  ENTRADA: "Entrada",
  SAIDA: "Saída",
  UNICA: "Única",
};

const pesoFormatter = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

const dataHoraFormatter = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asText(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function readDescription(contexto: UnknownRecord | null | undefined): string | null {
  if (!contexto) return null;

  const directKeys = [
    "descricao_codigo",
    "codigo_descricao",
    "descricao",
    "description",
    "produto_descricao",
  ];
  for (const key of directKeys) {
    const value = asText(contexto[key]);
    if (value) return value;
  }

  const nestedSources = [contexto.produto, contexto.carga];
  for (const source of nestedSources) {
    if (!isRecord(source)) continue;
    const product = isRecord(source.produto) ? source.produto : source;
    const value = asText(product.descricao) ?? asText(product.description);
    if (value) return value;
  }

  return null;
}

function codeDescription(row: TaraWeighing): string {
  return readDescription(row.contexto) ?? etapaLabels[row.etapa] ?? row.etapa;
}

function numericValue(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatPeso(value: number | string | null | undefined): string {
  const parsed = numericValue(value);
  return parsed === null ? "—" : `${pesoFormatter.format(parsed)} kg`;
}

function formatDataHora(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : dataHoraFormatter.format(date);
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) return error.message;
  if (isRecord(error) && typeof error.detail === "string") return error.detail;
  return "Verifique a configuração e a disponibilidade do Pondaxis.";
}

const columns: ColumnDef<TaraWeighing>[] = [
  {
    id: "descricao_codigo",
    header: "Descrição / código",
    accessorFn: codeDescription,
    exportFormat: (_value, row) => `${codeDescription(row)} (${row.local_id})`,
    cell: (_value, row) => (
      <div className="flex min-w-44 flex-col">
        <span className="font-medium">{codeDescription(row)}</span>
        <span className="font-mono text-xs text-muted-foreground">{row.local_id}</span>
      </div>
    ),
  },
  {
    id: "captured_at",
    header: "Data/hora",
    accessorFn: (row) => new Date(row.captured_at).getTime(),
    exportFormat: (_value, row) => formatDataHora(row.captured_at),
    cell: (_value, row) => formatDataHora(row.captured_at),
  },
  {
    id: "peso_aferido_kg",
    header: "Peso aferido",
    accessorFn: (row) => numericValue(row.peso_aferido_kg),
    exportFormat: (_value, row) => formatPeso(row.peso_aferido_kg),
    cell: (_value, row) => formatPeso(row.peso_aferido_kg),
  },
  {
    id: "peso_informado_kg",
    header: "Peso informado",
    accessorFn: (row) => numericValue(row.peso_informado_kg),
    exportFormat: (_value, row) => formatPeso(row.peso_informado_kg),
    cell: (_value, row) => formatPeso(row.peso_informado_kg),
  },
  {
    id: "peso_tara_kg",
    header: "Tara",
    accessorFn: (row) => numericValue(row.peso_tara_kg),
    exportFormat: (_value, row) => formatPeso(row.peso_tara_kg),
    cell: (_value, row) => formatPeso(row.peso_tara_kg),
  },
];

export function TaraWeighingsTable() {
  const weighingsQuery = useQuery({
    queryKey: ["tara-weighings"],
    queryFn: () => apiFetch<TaraWeighingPage>("/integracoes/tara/weighings", { params: { limit: 100 } }),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pesagens recentes</CardTitle>
        <CardDescription>Consulta somente leitura do Pondaxis, com pesos e data/hora no padrão brasileiro.</CardDescription>
      </CardHeader>
      <CardContent>
        {weighingsQuery.isError ? (
          <Alert variant="destructive">
            <AlertTitle>Falha na consulta</AlertTitle>
            <AlertDescription>{errorMessage(weighingsQuery.error)}</AlertDescription>
          </Alert>
        ) : (
          <DataTable
            data={weighingsQuery.data?.items ?? []}
            columns={columns}
            isLoading={weighingsQuery.isLoading}
            searchPlaceholder="Buscar por descrição ou código..."
            exportFileName="pesagens-recentes"
            emptyMessage="Nenhuma pesagem recente encontrada."
          />
        )}
      </CardContent>
    </Card>
  );
}
