export type Periodo = "30" | "90" | "180" | "all";

export interface CustoResumo {
  custo_total_frota: number;
  custo_combustivel: number;
  custo_manutencao: number;
  custo_pecas_itens: number;
  custo_documental: number;
  custo_medio_por_equipamento: number;
  equipamento_mais_caro_nome: string | null;
  equipamento_mais_caro_total: number | null;
}

export interface CustoEquipamento {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  unidade_produtiva_id: string | null;
  equipamento_status: string;
  horimetro_atual: number | null;
  km_atual: number | null;
  custo_combustivel: number;
  custo_manutencao: number;
  custo_pecas_itens: number;
  custo_documental: number;
  custo_total: number;
  custo_por_hora: number | null;
  custo_por_km: number | null;
  participacao_percentual: number | null;
}

export interface CustoRankingItem {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  custo_total: number;
  participacao_percentual: number | null;
  custo_por_hora: number | null;
  custo_por_km: number | null;
}

export interface CustoResponse {
  resumo: CustoResumo;
  equipamentos: CustoEquipamento[];
  ranking: CustoRankingItem[];
  gerado_em: string;
}
