"use client";

import { useRouter } from "next/navigation";
import { CheckCircle2, MessageCircle, XCircle } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  useIAGrowthIncentivoAprovar,
  useIAGrowthIncentivoReprovar,
  type IAGrowthIncentivoItem,
} from "@/hooks";

interface IncentivoGrowthApprovalCardProps {
  incentivo: IAGrowthIncentivoItem;
  className?: string;
}

export function IncentivoGrowthApprovalCard({ incentivo, className }: IncentivoGrowthApprovalCardProps) {
  const router = useRouter();
  const aprovarMut = useIAGrowthIncentivoAprovar();
  const reprovarMut = useIAGrowthIncentivoReprovar();

  const handleAprovar = async () => {
    try {
      await aprovarMut.mutateAsync(incentivo.id);
      toast.success("Incentivo aprovado.");
    } catch {
      toast.error("Não foi possível aprovar o incentivo agora.");
    }
  };

  const handleReprovar = async () => {
    try {
      await reprovarMut.mutateAsync({
        id: incentivo.id,
        motivo_reprovacao: "Reprovado após revisão humana.",
      });
      toast.success("Incentivo reprovado.");
    } catch {
      toast.error("Não foi possível reprovar o incentivo agora.");
    }
  };

  return (
    <Card className={cn("rounded-sm shadow-sm overflow-hidden border-l-4 border-l-amber-500/70", className)}>
      <CardHeader className="pb-3 bg-amber-50/40 dark:bg-amber-950/10">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-sm font-bold uppercase tracking-wide">
              Incentivo pendente de aprovação
            </CardTitle>
            <CardDescription className="text-xs">
              Revisão humana antes de liberar a oferta ao usuário.
            </CardDescription>
          </div>
          <Badge variant="outline" className="rounded-sm text-[10px] bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300">
            {incentivo.status_label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-sm border border-border/60 bg-muted/20 p-3">
            <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">Usuário</p>
            <p className="mt-1 text-xs font-semibold break-all">{incentivo.usuario_id ?? "Sem usuário"}</p>
          </div>
          <div className="rounded-sm border border-border/60 bg-muted/20 p-3">
            <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">Plano alvo</p>
            <p className="mt-1 text-sm font-semibold">{incentivo.plano_alvo_label}</p>
          </div>
          <div className="rounded-sm border border-border/60 bg-muted/20 p-3">
            <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">Validade</p>
            <p className="mt-1 text-sm font-semibold">
              {new Date(incentivo.validade_inicio).toLocaleDateString("pt-BR")} - {new Date(incentivo.validade_fim).toLocaleDateString("pt-BR")}
            </p>
          </div>
        </div>

        <div className="rounded-sm border border-border/60 bg-background p-3 space-y-2">
          <p className="text-[10px] uppercase font-black tracking-widest text-muted-foreground">Motivo</p>
          <p className="text-sm text-foreground/80 leading-relaxed">{incentivo.motivo}</p>
          <p className="text-[11px] text-muted-foreground">
            Origem: <span className="font-semibold text-foreground">{incentivo.origem_label}</span>
          </p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            className="rounded-sm text-xs font-bold gap-1.5"
            onClick={handleAprovar}
            disabled={aprovarMut.isPending || reprovarMut.isPending}
          >
            <CheckCircle2 data-icon="inline-start" />
            Aprovar
          </Button>
          <Button
            variant="outline"
            className="rounded-sm text-xs font-bold gap-1.5"
            onClick={handleReprovar}
            disabled={aprovarMut.isPending || reprovarMut.isPending}
          >
            <XCircle data-icon="inline-start" />
            Reprovar
          </Button>
          <Button
            variant="ghost"
            className="rounded-sm text-xs font-bold gap-1.5"
            onClick={() => router.push("/dashboard/settings/support")}
          >
            <MessageCircle data-icon="inline-start" />
            Falar com especialista
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
