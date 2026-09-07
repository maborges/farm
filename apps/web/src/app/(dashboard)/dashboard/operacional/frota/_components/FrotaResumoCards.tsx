import {
  AlertTriangle,
  CalendarClock,
  ClipboardList,
  DollarSign,
  Tractor,
  Wrench,
} from "lucide-react";

import { KpiCard } from "./FrotaKPICards";
import { FrotaResumo } from "./types";
import { formatCurrency } from "./utils";

interface FrotaResumoCardsProps {
  resumo: FrotaResumo;
}

export function FrotaResumoCards({ resumo }: FrotaResumoCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
      <KpiCard
        title="Equipamentos"
        value={resumo.total_equipamentos}
        description={`${resumo.ativos} ativos e ${resumo.parados} parados`}
        icon={Tractor}
      />
      <KpiCard
        title="Em manutenção"
        value={resumo.em_manutencao}
        description={`${resumo.os_abertas} OS abertas`}
        icon={Wrench}
        tone={resumo.em_manutencao > 0 ? "warning" : "default"}
      />
      <KpiCard
        title="Em uso"
        value={resumo.em_uso}
        description="Jornadas abertas agora"
        icon={CalendarClock}
        tone={resumo.em_uso > 0 ? "warning" : "default"}
      />
      <KpiCard
        title="Em risco"
        value={resumo.em_risco}
        description={`${resumo.documentos_vencidos} documentos vencidos`}
        icon={AlertTriangle}
        tone={resumo.em_risco > 0 ? "danger" : "default"}
      />
      <KpiCard
        title="Manutenções"
        value={resumo.manutencoes_vencidas}
        description={`${resumo.manutencoes_proximas} próximas do vencimento`}
        icon={ClipboardList}
        tone={resumo.manutencoes_vencidas > 0 ? "danger" : "default"}
      />
      <KpiCard
        title="Custo acumulado"
        value={formatCurrency(resumo.custo_total_acumulado)}
        description="Combustível + manutenção realizada"
        icon={DollarSign}
      />
    </div>
  );
}
