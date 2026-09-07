import { Target, TrendingUp, DollarSign, CheckCircle2 } from "lucide-react";
import { StatCard } from "@/components/shared/stat-card";
import { CRMStats } from "./types";

interface CrmStatsCardsProps {
  stats: CRMStats | null | undefined;
  formatCurrency: (val: number) => string;
}

export function CrmStatsCards({ stats, formatCurrency }: CrmStatsCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <StatCard
        icon={Target}
        label="Leads Ativos"
        value={stats?.leads_ativos ?? 0}
        color="primary"
      />
      <StatCard
        icon={TrendingUp}
        label="Convertidos"
        value={stats?.leads_convertidos ?? 0}
        color="success"
      />
      <StatCard
        icon={DollarSign}
        label="Pipeline"
        value={formatCurrency(stats?.valor_pipeline ?? 0)}
        color="warning"
      />
      <StatCard
        icon={CheckCircle2}
        label="Conversões/Mês"
        value={stats?.conversoes_mes ?? 0}
        color="backoffice"
      />
    </div>
  );
}
