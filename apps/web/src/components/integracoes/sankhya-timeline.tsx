"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export interface ErpTimelineItem {
  id: string;
  tipo_registro: string;
  origem_dado: string;
  feature_code?: string | null;
  status: string;
  event_type?: string | null;
  resumo: string;
  occurred_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  duracao_ms?: number | null;
  processados: number;
  sucessos: number;
  erros: number;
  correlation_id?: string | null;
}

export type SankhyaTimelineItem = ErpTimelineItem;

function formatDateTime(value?: string | null) {
  if (!value) return "Não disponível";
  return new Date(value).toLocaleString("pt-BR");
}

function formatLabel(value?: string | null) {
  if (!value) return "Não disponível";
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function badgeVariant(status: string | null | undefined) {
  if (!status) return "secondary" as const;
  if (["CONNECTED", "SUCCESS", "sucesso"].includes(status)) return "default" as const;
  if (["DISCONNECTED", "AUTH_ERROR", "CONFIG_ERROR", "FAILED", "erro"].includes(status)) {
    return "destructive" as const;
  }
  return "secondary" as const;
}

type Props = {
  items: ErpTimelineItem[];
  enableFilters?: boolean;
};

export function ErpTimeline({ items, enableFilters = false }: Props) {
  const [statusFilter, setStatusFilter] = useState("todos");
  const [originFilter, setOriginFilter] = useState("todos");
  const [featureFilter, setFeatureFilter] = useState("");

  const features = useMemo(() => {
    return Array.from(
      new Set(items.map((item) => item.feature_code).filter((value): value is string => Boolean(value))),
    ).sort();
  }, [items]);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const statusOk = statusFilter === "todos" || item.status === statusFilter;
      const originOk = originFilter === "todos" || item.origem_dado === originFilter;
      const featureOk =
        featureFilter.trim().length === 0 ||
        (item.feature_code || "").toLowerCase().includes(featureFilter.trim().toLowerCase());
      return statusOk && originOk && featureOk;
    });
  }, [featureFilter, items, originFilter, statusFilter]);

  return (
    <div className="space-y-4">
      {enableFilters ? (
        <div className="grid gap-3 rounded-sm border bg-muted/20 p-3 md:grid-cols-3">
          <div className="space-y-1">
            <Label htmlFor="timeline-status">Status</Label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger id="timeline-status">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todos</SelectItem>
                <SelectItem value="SUCCESS">SUCCESS</SelectItem>
                <SelectItem value="FAILED">FAILED</SelectItem>
                <SelectItem value="RUNNING">RUNNING</SelectItem>
                <SelectItem value="sucesso">sucesso</SelectItem>
                <SelectItem value="erro">erro</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="timeline-origin">Origem</Label>
            <Select value={originFilter} onValueChange={setOriginFilter}>
              <SelectTrigger id="timeline-origin">
                <SelectValue placeholder="Todas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todas</SelectItem>
                <SelectItem value="canonical">oficial</SelectItem>
                <SelectItem value="legacy">legado</SelectItem>
                <SelectItem value="canonical+legacy">oficial+legado</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="timeline-feature">Feature</Label>
            <Input
              id="timeline-feature"
              placeholder={features[0] || "Ex.: pessoas"}
              value={featureFilter}
              onChange={(event) => setFeatureFilter(event.target.value)}
            />
          </div>
        </div>
      ) : null}

      <div className="space-y-2">
        {filteredItems.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum evento operacional encontrado.</p>
        ) : (
          filteredItems.map((item) => (
            <div key={item.id} className="rounded-sm border bg-muted/20 p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={badgeVariant(item.status)}>{item.status}</Badge>
                    <Badge variant="outline">{item.origem_dado}</Badge>
                    <Badge variant="secondary">{formatLabel(item.tipo_registro)}</Badge>
                  </div>
                  <p className="text-sm font-medium">{item.resumo}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDateTime(item.occurred_at)}
                    {item.feature_code ? ` · ${item.feature_code}` : ""}
                    {item.event_type ? ` · ${item.event_type}` : ""}
                  </p>
                </div>
                <div className="text-right text-xs text-muted-foreground">
                  <p>{item.sucessos}/{item.processados} sucesso</p>
                  <p>{item.erros} erros</p>
                  <p>{item.duracao_ms ? `${(item.duracao_ms / 1000).toFixed(2)}s` : "sem duração"}</p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export const SankhyaTimeline = ErpTimeline;
