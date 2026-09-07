"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, MessageCircle, Sparkles, XCircle } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  useIAGrowthIncentivoAceitar,
  useIAGrowthIncentivoRecusar,
  type IAGrowthIncentivoItem,
} from "@/hooks";

const TIPO_LABELS: Record<string, { label: string; className: string }> = {
  TRIAL_PROFISSIONAL: { label: "Trial Profissional", className: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300" },
  TRIAL_ENTERPRISE: { label: "Trial Enterprise", className: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300" },
  DEMO_ASSISTIDA: { label: "Demo assistida", className: "bg-sky-100 text-sky-700 border-sky-200 dark:bg-sky-900/30 dark:text-sky-300" },
  CONSULTORIA_RAPIDA: { label: "Consultoria rápida", className: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300" },
  EXTENSAO_AVALIACAO: { label: "Extensão de avaliação", className: "bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-900/30 dark:text-violet-300" },
};

const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  OFERECIDO: { label: "Oferecido", className: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300" },
  ACEITO: { label: "Aceito", className: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300" },
  RECUSADO: { label: "Recusado", className: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-900/30 dark:text-slate-300" },
  EXPIRADO: { label: "Expirado", className: "bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-900/30 dark:text-rose-300" },
  CANCELADO: { label: "Cancelado", className: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300" },
  PENDENTE_APROVACAO: { label: "Pendente de aprovação", className: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300" },
  APROVADO: { label: "Aprovado", className: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300" },
  REPROVADO: { label: "Reprovado", className: "bg-rose-100 text-rose-700 border-rose-200 dark:bg-rose-900/30 dark:text-rose-300" },
};

interface IncentivoGrowthCardProps {
  incentivo: IAGrowthIncentivoItem | null | undefined;
  compact?: boolean;
  className?: string;
}

export function IncentivoGrowthCard({ incentivo, compact = false, className }: IncentivoGrowthCardProps) {
  const router = useRouter();
  const aceitarMut = useIAGrowthIncentivoAceitar();
  const recusarMut = useIAGrowthIncentivoRecusar();

  if (!incentivo) return null;

  const tipoBadge = TIPO_LABELS[incentivo.tipo_incentivo] ?? TIPO_LABELS.CONSULTORIA_RAPIDA;
  const statusBadge = STATUS_LABELS[incentivo.status] ?? STATUS_LABELS.OFERECIDO;
  const validade = new Date(incentivo.validade_fim).toLocaleDateString("pt-BR");

  const handleAceitar = async () => {
    try {
      await aceitarMut.mutateAsync(incentivo.id);
      toast.success("Incentivo aceito com sucesso.");
    } catch {
      toast.error("Não foi possível aceitar o incentivo agora.");
    }
  };

  const handleRecusar = async () => {
    try {
      await recusarMut.mutateAsync(incentivo.id);
      toast.success("Incentivo recusado.");
    } catch {
      toast.error("Não foi possível recusar o incentivo agora.");
    }
  };

  const handleEspecialista = () => {
    router.push("/dashboard/settings/support");
  };

  return (
    <Card className={cn("rounded-sm shadow-sm overflow-hidden border-l-4 border-l-blue-500/70", className)}>
      <CardHeader className={cn("pb-3", compact ? "bg-blue-50/40 dark:bg-blue-950/10" : "bg-blue-50/30 dark:bg-blue-950/10")}>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Sparkles className="text-blue-600" />
              <CardTitle className="text-sm font-bold uppercase tracking-wide">
                Incentivo controlado
              </CardTitle>
            </div>
            <CardDescription className="text-xs">
              Oferta temporária e auditável, sem alterar cobrança automaticamente.
            </CardDescription>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Badge variant="outline" className={cn("rounded-sm text-[10px]", tipoBadge.className)}>
              {tipoBadge.label}
            </Badge>
            <Badge variant="outline" className={cn("rounded-sm text-[10px]", statusBadge.className)}>
              {statusBadge.label}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-sm border border-border/60 bg-muted/20 p-3">
            <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">Plano alvo</p>
            <p className="mt-1 text-sm font-semibold">{incentivo.plano_alvo_label}</p>
          </div>
          <div className="rounded-sm border border-border/60 bg-muted/20 p-3">
            <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">Validade</p>
            <p className="mt-1 text-sm font-semibold">{validade}</p>
          </div>
          <div className="rounded-sm border border-border/60 bg-muted/20 p-3">
            <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">Dias restantes</p>
            <p className="mt-1 text-sm font-semibold tabular-nums">{incentivo.dias_validade_restantes}</p>
          </div>
        </div>

        <div className="rounded-sm border border-border/60 bg-background p-3 space-y-2">
          <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">Motivo</p>
          <p className="text-sm text-foreground/80 leading-relaxed">{incentivo.motivo}</p>
          <p className="text-[11px] text-muted-foreground">
            Origem: <span className="font-semibold text-foreground">{incentivo.origem_label}</span>
          </p>
        </div>

        {incentivo.status === "OFERECIDO" || incentivo.status === "APROVADO" ? (
          compact ? (
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                className="rounded-sm text-xs font-bold gap-1.5"
                onClick={handleAceitar}
                disabled={aceitarMut.isPending || recusarMut.isPending}
              >
                <CheckCircle2 data-icon="inline-start" />
                Aceitar
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="rounded-sm text-xs font-bold gap-1.5"
                onClick={handleRecusar}
                disabled={aceitarMut.isPending || recusarMut.isPending}
              >
                <XCircle data-icon="inline-start" />
                Recusar
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="rounded-sm text-xs font-bold gap-1.5"
                onClick={handleEspecialista}
              >
                <MessageCircle data-icon="inline-start" />
                Falar com especialista
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button
                className="rounded-sm text-xs font-bold gap-1.5"
                onClick={handleAceitar}
                disabled={aceitarMut.isPending || recusarMut.isPending}
              >
                <CheckCircle2 data-icon="inline-start" />
                Aceitar incentivo
              </Button>
              <Button
                variant="outline"
                className="rounded-sm text-xs font-bold gap-1.5"
                onClick={handleRecusar}
                disabled={aceitarMut.isPending || recusarMut.isPending}
              >
                <XCircle data-icon="inline-start" />
                Recusar
              </Button>
              <Button
                variant="ghost"
                className="rounded-sm text-xs font-bold gap-1.5"
                onClick={handleEspecialista}
              >
                <MessageCircle data-icon="inline-start" />
                Falar com especialista
              </Button>
            </div>
          )
        ) : (
          <div className="flex items-center justify-between gap-2">
            <p className="text-[11px] text-muted-foreground">
              {incentivo.status === "PENDENTE_APROVACAO"
                ? "Aguardando revisão interna antes de ser liberado ao usuário."
                : "Este incentivo já saiu da fase de oferta ativa."}
            </p>
            <Button
              size="sm"
              variant="ghost"
              className="rounded-sm text-xs font-bold gap-1.5"
              onClick={handleEspecialista}
            >
              <MessageCircle data-icon="inline-start" />
              Falar com especialista
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
