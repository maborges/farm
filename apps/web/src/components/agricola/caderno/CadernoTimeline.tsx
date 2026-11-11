"use client";

import { Badge } from "@/components/ui/badge";
import { WorkflowStatusBadge } from "@/components/ui/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  Sprout, Eye, CloudRain, Layers, Clipboard, Stethoscope, Camera, ChevronRight
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface TimelineItem {
  id: string;
  tipo: string;
  tipo_evento?: string;
  subtipo?: string;
  descricao: string;
  data_registro: string;
  talhao_id: string;
  usuario_id?: string;
  executado_por_pessoa_id?: string;
  status_evento?: string;
  status_evento_atualizado_em?: string;
  pendente_aprovacao?: boolean;
  aprovado?: boolean;
  consolidado?: boolean;
  rejeitado?: boolean;
  nivel_severidade?: string;
  fotos_count: number;
  excluida: boolean;
  origem: string;
  origem_invalidada?: boolean;
  origem_invalidada_em?: string | null;
  origem_invalidada_por?: string | null;
  motivo_invalidacao_origem?: string | null;
  documental_status?: string | null;
  retifica_evento_id?: string | null;
  retificado_por_evento_id?: string | null;
  motivo_retificacao?: string | null;
  retificado_em?: string | null;
  retificado_por_usuario_id?: string | null;
  versao_vigente?: boolean;
  retificado?: boolean;
  retificador?: boolean;
}

interface Props {
  items: TimelineItem[];
  isLoading: boolean;
  onSelect: (item: TimelineItem) => void;
}

const TIPO_CONFIG: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  OPERACAO_AUTO: { label: "Operação", icon: Sprout, color: "text-emerald-700 dark:text-emerald-400 bg-emerald-500/10" },
  MONITORAMENTO: { label: "Monitoramento", icon: Stethoscope, color: "text-orange-700 dark:text-orange-400 bg-orange-500/10" },
  VISITA_TECNICA: { label: "Visita Técnica", icon: Clipboard, color: "text-blue-700 dark:text-blue-400 bg-blue-500/10" },
  EPI_ENTREGA: { label: "EPI", icon: Layers, color: "text-purple-700 dark:text-purple-400 bg-purple-500/10" },
  OBSERVACAO: { label: "Observação", icon: Eye, color: "text-muted-foreground bg-muted" },
  CLIMA: { label: "Clima", icon: CloudRain, color: "text-sky-700 dark:text-sky-400 bg-sky-500/10" },
  SOLO: { label: "Solo", icon: Layers, color: "text-amber-700 dark:text-amber-400 bg-amber-500/10" },
};

const SEVERIDADE_DOT: Record<string, string> = {
  BAIXO: "bg-green-500",
  MEDIO: "bg-yellow-500",
  ALTO: "bg-orange-500",
  CRITICO: "bg-red-500",
};

function groupByDate(items: TimelineItem[]): Record<string, TimelineItem[]> {
  return items.reduce((acc, item) => {
    const key = item.data_registro;
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {} as Record<string, TimelineItem[]>);
}

export function CadernoTimeline({ items, isLoading, onSelect }: Props) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="flex gap-3">
            <Skeleton className="size-8 rounded-full shrink-0" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-12 w-full" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <Clipboard className="size-10 text-muted-foreground/40 mb-3" />
        <p className="font-medium text-sm">Nenhum registro no caderno</p>
        <p className="text-xs text-muted-foreground mt-1">
          Use o botão Novo Registro para adicionar observações, monitoramentos ou visitas técnicas.
        </p>
      </div>
    );
  }

  const grouped = groupByDate(items);
  const dates = Object.keys(grouped).sort((a, b) => b.localeCompare(a));

  return (
    <div className="relative space-y-6">
      {/* Linha vertical da timeline */}
      <div className="absolute left-4 top-2 bottom-2 w-px bg-border" aria-hidden />

      {dates.map(dateKey => {
        const dateItems = grouped[dateKey];
        const dateLabel = format(new Date(dateKey + "T12:00:00"), "dd 'de' MMMM", { locale: ptBR });

        return (
          <div key={dateKey} className="relative pl-10">
            {/* Marcador de data */}
            <div className="absolute left-0 -translate-x-px flex items-center justify-center size-8 rounded-full bg-background border-2 border-border">
              <span className="text-[10px] font-bold text-muted-foreground leading-none">
                {format(new Date(dateKey + "T12:00:00"), "dd")}
              </span>
            </div>

            <div className="mb-2">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {dateLabel}
              </span>
            </div>

            <div className="space-y-2">
              {dateItems.map(item => {
                const tipoEvento = item.tipo_evento ?? item.tipo;
                const config = TIPO_CONFIG[tipoEvento] ?? TIPO_CONFIG.OBSERVACAO;
                const Icon = config.icon;

                return (
                  <button
                    key={item.id}
                    onClick={() => onSelect(item)}
                    className={cn(
                      "w-full text-left rounded-sm border bg-card p-3 hover:bg-muted/40 transition-colors",
                      "flex items-start gap-3 group",
                      item.excluida && "opacity-50"
                    )}
                  >
                    <div className={cn("size-7 rounded-full flex items-center justify-center shrink-0 mt-0.5", config.color)}>
                      <Icon className="size-3.5" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                        <span className="text-xs font-medium">
                          {item.origem === "operacao"
                            ? `Operação — ${item.subtipo ?? ""}`
                            : config.label}
                        </span>
                        {item.status_evento && (
                          <WorkflowStatusBadge status={item.status_evento} className="h-4 px-1.5 text-[10px]" />
                        )}
                        {item.versao_vigente && (
                          <Badge variant="secondary" className="h-4 px-1.5 text-[10px]">Versão vigente</Badge>
                        )}
                        {item.retificado && (
                          <Badge variant="outline" className="h-4 px-1.5 text-[10px]">Retificado</Badge>
                        )}
                        {item.retificador && (
                          <Badge variant="outline" className="h-4 px-1.5 text-[10px]">Retificador</Badge>
                        )}
                        {item.origem_invalidada && (
                          <Badge variant="destructive" className="h-4 px-1.5 text-[10px]">Origem invalidada</Badge>
                        )}
                        {item.nivel_severidade && (
                          <span className={cn("size-2 rounded-full inline-block", SEVERIDADE_DOT[item.nivel_severidade])} />
                        )}
                        {item.fotos_count > 0 && (
                          <span className="flex items-center gap-0.5 text-[10px] text-muted-foreground">
                            <Camera className="size-3" /> {item.fotos_count}
                          </span>
                        )}
                        {item.excluida && (
                          <Badge variant="destructive" className="text-[10px] h-4 px-1">Excluída</Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-2">{item.descricao}</p>
                      {item.origem_invalidada && (
                        <p className="mt-1 text-[11px] font-medium text-destructive">
                          Origem operacional invalidada{item.motivo_invalidacao_origem ? `: ${item.motivo_invalidacao_origem}` : ""}
                        </p>
                      )}
                    </div>

                    <ChevronRight className="size-4 text-muted-foreground/50 shrink-0 mt-1 group-hover:text-muted-foreground transition-colors" />
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
