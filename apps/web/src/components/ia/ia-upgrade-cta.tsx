"use client";

import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, Sparkles, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useIAGrowthCTA, useIAGrowthTrack, useIAGrowthTrackClick } from "@/hooks";

interface IAUpgradeCTAProps {
  contexto?: "progresso" | "acao" | "resumo";
  className?: string;
  compact?: boolean;
}

export function IAUpgradeCTA({ contexto = "progresso", className, compact = false }: IAUpgradeCTAProps) {
  const { data, isLoading } = useIAGrowthCTA(contexto);
  const { mutate: trackEvento } = useIAGrowthTrack();
  const { mutate: trackClick } = useIAGrowthTrackClick();
  const [viewed, setViewed] = React.useState(false);
  const [dismissed, setDismissed] = React.useState(false);

  React.useEffect(() => {
    if (data?.deve_exibir && data.timing_decision !== "HIDDEN" && !viewed && !dismissed) {
      setViewed(true);
      trackEvento({
        evento: "upgrade_cta_viewed",
        tipo_cta: data.tipo,
        contexto: data.contexto,
        churn_risk_score: data.churn_risk_score,
        churn_risk_level: data.churn_risk_level,
        metadados: { 
          roi_valor: data.roi_valor,
          moment_score: data.moment_score,
          timing_decision: data.timing_decision,
          churn_risk_score: data.churn_risk_score,
          churn_risk_level: data.churn_risk_level,
        },
      });
    }
  }, [data?.deve_exibir, viewed, trackEvento, data, dismissed]);

  if (isLoading || !data?.deve_exibir || data.timing_decision === "HIDDEN" || dismissed) return null;

  const handleClick = () => {
    trackEvento({
      evento: "upgrade_cta_clicked",
      tipo_cta: data.tipo,
      contexto: data.contexto,
      churn_risk_score: data.churn_risk_score,
      churn_risk_level: data.churn_risk_level,
      metadados: { 
        roi_valor: data.roi_valor,
        moment_score: data.moment_score,
        timing_decision: data.timing_decision,
        churn_risk_score: data.churn_risk_score,
        churn_risk_level: data.churn_risk_level,
      },
    });

    if (data.experimento_id && data.variante_id) {
      trackClick({
        experimento_id: data.experimento_id,
        variante_id: data.variante_id,
        contexto: data.contexto,
        churn_risk_score: data.churn_risk_score,
        churn_risk_level: data.churn_risk_level,
      });
    }
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDismissed(true);
    trackEvento({
      evento: "upgrade_cta_dismissed",
      tipo_cta: data.tipo,
      contexto: data.contexto,
      churn_risk_score: data.churn_risk_score,
      churn_risk_level: data.churn_risk_level,
      metadados: { 
        roi_valor: data.roi_valor,
        moment_score: data.moment_score,
        timing_decision: data.timing_decision,
        churn_risk_score: data.churn_risk_score,
        churn_risk_level: data.churn_risk_level,
      },
    });
  };

  const isSoft = data.timing_decision === "SOFT";
  const showChurnDebug = process.env.NODE_ENV !== "production" && data.churn_risk_level && data.churn_risk_level !== "BAIXO";
  const churnLabel = data.churn_risk_level === "ALTO" ? "Risco alto" : "Risco medio";

  if (compact || isSoft) {
    return (
      <div className={cn(
        "group relative flex items-center justify-between gap-3 rounded-sm border px-3 py-2 transition-all duration-300",
        isSoft 
          ? "border-border/50 bg-background/50 hover:border-primary/30" 
          : "border-primary/20 bg-primary/5",
        className
      )}>
        <div className="flex-1 min-w-0">
          {showChurnDebug && (
            <Badge variant="outline" className="mb-1 rounded-sm text-[9px] uppercase tracking-wide text-amber-700 border-amber-500/30 bg-amber-500/5">
              {churnLabel}
            </Badge>
          )}
          {data.titulo_alternativo && (
            <span className={cn("block text-[10px] font-bold truncate", isSoft ? "text-muted-foreground" : "text-primary")}>
              {data.titulo_alternativo}
            </span>
          )}
          <p className={cn("text-[10px] font-semibold leading-snug line-clamp-1", isSoft ? "text-foreground/80" : "text-primary")}>
            {data.mensagem}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button asChild size="sm" variant="outline" className={cn(
            "h-6 text-[10px] px-2 shrink-0 gap-1",
            isSoft ? "border-border hover:bg-primary/10 hover:text-primary" : "border-primary/30 text-primary"
          )} onClick={handleClick}>
            <Link href={data.cta_url}>
              {data.cta_label}
              <ArrowRight className="size-2.5" />
            </Link>
          </Button>
          <button 
            onClick={handleDismiss}
            className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-accent rounded-sm"
            title="Fechar"
          >
            <X className="size-3 text-muted-foreground" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      "group relative rounded-sm border border-primary/20 bg-primary/5 p-4 space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-500", 
      className
    )}>
      <button 
        onClick={handleDismiss}
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-primary/10 rounded-sm"
        title="Fechar"
      >
        <X className="size-3.5 text-primary/60 hover:text-primary" />
      </button>

      <div className="flex items-start gap-3">
        <Sparkles className="size-4 text-primary shrink-0 mt-0.5 animate-pulse" />
        <div className="space-y-1 flex-1">
          {showChurnDebug && (
            <Badge variant="outline" className="rounded-sm text-[9px] uppercase tracking-wide text-amber-700 border-amber-500/30 bg-amber-500/5">
              {churnLabel}
            </Badge>
          )}
          {data.titulo_alternativo && (
            <h4 className="text-sm font-bold text-primary leading-tight">
              {data.titulo_alternativo}
            </h4>
          )}
          <p className="text-sm font-medium text-foreground leading-snug">{data.mensagem}</p>
        </div>
      </div>
      <Button asChild size="sm" variant="outline" className="h-8 text-xs border-primary/30 text-primary gap-1.5 w-full" onClick={handleClick}>
        <Link href={data.cta_url}>
          {data.cta_label}
          <ArrowRight className="size-3" />
        </Link>
      </Button>
    </div>
  );
}
