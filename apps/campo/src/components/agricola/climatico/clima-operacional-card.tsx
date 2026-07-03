import { useLiveQuery } from "dexie-react-hooks";
import { db } from "@/lib/db";
import { AlertCircle, AlertTriangle, CheckCircle2, Clock, CloudOff } from "lucide-react";

interface ClimaOperacionalCardProps {
  fazendaId: string;
  tipoOperacao: string;
}

export function ClimaOperacionalCard({ fazendaId, tipoOperacao }: ClimaOperacionalCardProps) {
  const recomendacao = useLiveQuery(
    () => db.recomendacoes_climaticas.get(`${fazendaId}-${tipoOperacao}`),
    [fazendaId, tipoOperacao]
  );

  if (!recomendacao) {
    return (
      <div className="flex items-center gap-3 rounded-md border border-border bg-card p-3 text-sm text-muted-foreground">
        <CloudOff className="size-5 shrink-0" />
        <div>
          <p className="font-semibold text-foreground">Sem dados climáticos</p>
          <p className="text-xs">Sincronize para obter recomendações</p>
        </div>
      </div>
    );
  }

  // Verifica se o dado está vencido
  const dataReferencia = new Date(recomendacao.data_referencia);
  const dataExpiracao = new Date(dataReferencia.getTime() + recomendacao.validade_horas * 60 * 60 * 1000);
  const agora = new Date();
  const isVencido = agora > dataExpiracao;

  // Formata a última atualização
  const timeStr = dataReferencia.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

  if (isVencido) {
    return (
      <div className="flex items-center gap-3 rounded-md border border-orange-200 bg-orange-50 p-3 text-sm text-orange-900 dark:border-orange-900/50 dark:bg-orange-950/20 dark:text-orange-200">
        <Clock className="size-5 shrink-0" />
        <div>
          <p className="font-semibold">Dados climáticos desatualizados</p>
          <p className="text-xs opacity-90">Última atualização às {timeStr}. Sincronize novamente.</p>
        </div>
      </div>
    );
  }

  // Estilização baseada no status
  let styles = "border-border bg-card text-foreground";
  let Icon = AlertCircle;

  if (recomendacao.status === "RECOMENDADO") {
    styles = "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/20 dark:text-emerald-200";
    Icon = CheckCircle2;
  } else if (recomendacao.status === "ATENCAO") {
    styles = "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-200";
    Icon = AlertTriangle;
  } else if (recomendacao.status === "NAO_RECOMENDADO") {
    styles = "border-red-200 bg-red-50 text-red-900 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-200";
    Icon = AlertCircle;
  }

  return (
    <div className={`flex flex-col gap-2 rounded-md border p-3 text-sm transition-colors ${styles}`}>
      <div className="flex items-start gap-3">
        <Icon className="size-5 shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="font-semibold uppercase tracking-wider text-xs opacity-80 mb-0.5">
            Clima: {recomendacao.status.replace("_", " ")}
          </p>
          <p className="leading-snug">{recomendacao.motivo}</p>
        </div>
      </div>
      <div className="mt-1 flex items-center justify-end gap-1.5 text-xs opacity-70">
        <Clock className="size-3" />
        <span>Atualizado às {timeStr}</span>
      </div>
    </div>
  );
}
