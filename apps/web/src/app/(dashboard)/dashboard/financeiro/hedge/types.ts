export interface ContratoFuturo {
    id: string;
    tenant_id: string;
    safra_id: string | null;
    commodity_id: string | null;
    commodity: string;
    mercado: string | null;
    codigo_contrato: string | null;
    mes_vencimento: string | null;
    tipo_posicao: "COMPRA" | "VENDA";
    quantidade: number;
    unidade: string;
    preco_contratado: number | null;
    status: "ABERTO" | "ENCERRADO" | "LIQUIDADO";
    data_liquidacao: string | null;
    preco_liquidacao: number | null;
    resultado: number | null;
    created_at: string;
    updated_at: string;
}

export interface HedgeRegistro {
    id: string;
    tenant_id: string;
    contrato_futuro_id: string;
    safra_id: string | null;
    tipo: "ABERTURA" | "ROLAGEM" | "ENCERRAMENTO" | "AJUSTE";
    quantidade: number;
    preco: number;
    data_operacao: string;
    base: number | null;
    resultado_papel: number | null;
    resultado_fisico: number | null;
    resultado_liquido: number | null;
    observacoes: string | null;
    created_at: string;
}

export interface HedgePosicao {
    tenant_id: string;
    safra_id: string | null;
    commodity: string | null;
    total_contratos_abertos: number;
    quantidade_total_hedgeada: number;
    preco_medio_ponderado: number | null;
    unidade: string;
}

export interface HedgeExposicao {
    tenant_id: string;
    safra_id: string | null;
    commodity: string | null;
    // Componentes da Exposição Física Bruta
    producao_estimada_sc: number;
    estoque_fisico_sc: number;
    exposicao_bruta_sc: number;
    // Compromissos e Proteção
    ja_vendido_sc: number;
    ja_hedgeado_sc: number;
    // Resultados Calculados
    exposicao_liquida_sc: number;
    exposicao_aberta_sc: number;
    percentual_cobertura: number;
    hedge_ratio: number;
    // Classificação de Risco
    classificacao_risco: "DESCOBERTO" | "EQUILIBRADO" | "SOBREPROTEGIDO";
}

export interface ExposicaoConsolidadaItem {
    safra_id: string | null;
    ano_safra: string | null;
    commodity: string | null;
    exposicao_bruta_sc: number;
    ja_vendido_sc: number;
    ja_hedgeado_sc: number;
    exposicao_aberta_sc: number;
    percentual_cobertura: number;
    classificacao_risco: "DESCOBERTO" | "EQUILIBRADO" | "SOBREPROTEGIDO";
}

export interface ExposicaoConsolidada {
    tenant_id: string;
    total_exposicao_bruta_sc: number;
    total_compromissos_sc: number;
    total_protecao_sc: number;
    total_exposicao_aberta_sc: number;
    percentual_cobertura_global: number;
    classificacao_risco_global: "DESCOBERTO" | "EQUILIBRADO" | "SOBREPROTEGIDO";
    por_safra_commodity: ExposicaoConsolidadaItem[];
}

export interface ExposicaoHistoricoItem {
    data_referencia: string;
    exposicao_fisica_sc: number;
    protecao_financeira_sc: number;
    exposicao_aberta_sc: number;
    hedge_ratio: number;
    pnl_nao_realizado: number;
}

export interface HedgePositionSnapshot {
    id: string;
    tenant_id: string;
    contrato_futuro_id: string;
    safra_id: string | null;
    commodity_id: string | null;
    data_referencia: string;
    quantidade_aberta: number;
    preco_contratado: number;
    preco_mercado: number;
    moeda: string;
    unidade: string;
    mtm_valor: number;
    pnl_nao_realizado: number;
    fonte_preco: string | null;
    calculado_em: string;
    created_at: string;
}

export interface SimulacaoExposicaoRequest {
    safra_id?: string | null;
    commodity?: string | null;
    unidade_produtiva_id?: string | null;
    variacao_producao_sc: number;
    variacao_estoque_sc: number;
    variacao_venda_sc: number;
    variacao_hedge_sc: number;
}

export interface SimulacaoExposicaoResponse {
    cenario_atual: HedgeExposicao;
    cenario_simulado: HedgeExposicao;
    alertas: string[];
}
