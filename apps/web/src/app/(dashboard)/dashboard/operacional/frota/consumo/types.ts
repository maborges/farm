export type Severidade = "warning" | "danger";

export interface ConsumoResumo {
  litros_totais: number;
  custo_total_combustivel: number;
  custo_medio_litro: number | null;
  consumo_medio_l_h: number | null;
  consumo_medio_km_l: number | null;
  equipamentos_com_anomalia: number;
  total_alertas: number;
}

export interface ConsumoRankingItem {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  metrica_principal: "HORIMETRO" | "KM" | "AMBOS" | "INDISPONIVEL";
  eficiencia_score: number | null;
  consumo_medio_l_h: number | null;
  consumo_medio_km_l: number | null;
  custo_por_hora: number | null;
  custo_por_km: number | null;
  variacao_media_frota_percent: number | null;
}

export interface ConsumoAlerta {
  tipo: string;
  titulo: string;
  severidade: Severidade;
  equipamento_id: string;
  equipamento_nome: string;
  detalhe: string;
  data_referencia: string | null;
  dias_desde_evento: number | null;
}

export interface ConsumoResponse {
  resumo: ConsumoResumo;
  ranking_eficiencia: ConsumoRankingItem[];
  alertas: ConsumoAlerta[];
}
