export type DomainType = "MERCADO" | "CLIMA" | "INSUMOS" | "CONJUNTURA";
export type TipoLicencaType = "DADO_PUBLICO_GOV" | "PARCEIRO_AUTORIZADO" | "LINK_HOMOLOGADO_APENAS";
export type EstrategiaColetaType = "NIVEL1_DETERMINISTICO" | "NIVEL2_IA_PDF_HTML" | "GENERICO_PARCEIRO";
export type AutoPublishPolicyType = "AUTO_SE_GUARDRAILS_OK" | "SEMPRE_REVISAO_HUMANA";
export type RunStatusType = "SUCESSO" | "PARCIAL" | "QUARENTENA" | "SKIPPED_UNCHANGED" | "FALHA";
export type StatusRevisaoType = "PENDENTE_REVISAO" | "APROVADO" | "REJEITADO" | "AUTO_APROVADO";

export interface CollectorSourceItem {
  id: string;
  domain: DomainType;
  slug: string;
  nome: string;
  sigla: string;
  tipo_licenca: TipoLicencaType;
  termo_autorizacao_ref?: string | null;
  atribuicao_obrigatoria?: string | null;
  uf_padrao: string;
  praca_padrao?: string | null;
  dominios_whitelist: string[];
  url_principal: string;
  url_indice?: string | null;
  estrategia_coleta: EstrategiaColetaType;
  config_extrator: Record<string, unknown>;
  cron_ou_intervalo_seg: number;
  auto_publish_policy: AutoPublishPolicyType;
  max_variacao_pct: string | number;
  max_defasagem_dias: number;
  prioridade_exibicao: number;
  ativo: boolean;
  falhas_consecutivas: number;
  ultima_execucao_em?: string | null;
  ultimo_sucesso_em?: string | null;
  proximo_ciclo_em?: string | null;
  pendentes_revisao: number;
}

export interface CollectorSourcesListResponse {
  sources: CollectorSourceItem[];
  total: number;
  pendentes_quarentena_total: number;
}

export interface CollectorDryRunObservationItem {
  commodity_id: string;
  uf: string;
  praca: string;
  data_referencia: string;
  valor_normalizado: string | number;
  unidade_normalizada: string;
  trecho_evidencia: string;
  flags_anomalia: string[];
  bloqueado_para_publicacao: boolean;
}

export interface CollectorDryRunResponse {
  source_slug: string;
  url_efetiva: string;
  sha256_bruto: string;
  modelo_ia?: string | null;
  tokens_entrada: number;
  tokens_saida: number;
  custo_estimado_usd: string | number;
  total_extraidos: number;
  itens: CollectorDryRunObservationItem[];
}

export interface CollectorRunSummary {
  run_id: string;
  source_slug: string;
  status: RunStatusType;
  skipped_unchanged: boolean;
  total_extraidos: number;
  total_publicados: number;
  total_quarentena: number;
  total_rejeitados: number;
  erro_resumo?: string | null;
  sugestao_sentinela?: SentinelSuggestion | null;
}

export interface SentinelSuggestion {
  url_sugerida: string;
  evidencia: string;
  candidatos_avaliados?: number;
  gerado_em?: string;
  aplicada_em?: string;
}

export interface CollectorRunItem {
  id: string;
  source_id: string;
  source_slug: string;
  source_sigla: string;
  status: RunStatusType;
  trigger_tipo: "AGENDADO" | "MANUAL" | "REPROCESSAMENTO";
  executado_por?: string | null;
  url_efetiva?: string | null;
  http_status?: number | null;
  sha256_bruto?: string | null;
  tamanho_bytes?: number | null;
  skipped_unchanged: boolean;
  modelo_ia?: string | null;
  tokens_entrada: number;
  tokens_saida: number;
  custo_estimado_usd: string | number;
  total_extraidos: number;
  total_publicados: number;
  total_quarentena: number;
  total_rejeitados: number;
  erro_resumo?: string | null;
  sugestao_sentinela?: SentinelSuggestion | null;
  has_artifact: boolean;
  artifact_expurgado: boolean;
  iniciado_em: string;
  finalizado_em?: string | null;
}

export interface CollectorRunsListResponse {
  runs: CollectorRunItem[];
  total: number;
}

export interface CollectorStagingItem {
  id: string;
  run_id: string;
  source_id: string;
  source_slug: string;
  source_sigla: string;
  commodity_id: string;
  uf: string;
  praca: string;
  tipo_preco: string;
  periodicidade: string;
  data_referencia: string;
  valor_normalizado: string | number;
  moeda: string;
  unidade_normalizada: string;
  valor_original: string | number;
  unidade_original: string;
  fator_conversao: string | number;
  transformacao_aplicada?: string | null;
  trecho_evidencia: string;
  registro_origem?: string | null;
  confianca_extracao: string | number;
  flags_anomalia: string[];
  status_revisao: StatusRevisaoType;
  ultimo_valor_ativo?: string | number | null;
  variacao_contra_ativo_pct?: string | number | null;
  revisado_em?: string | null;
  justificativa_revisao?: string | null;
  created_at: string;
}

export interface CollectorStagingListResponse {
  items: CollectorStagingItem[];
  total: number;
  pendentes_total: number;
}

export interface CollectorBulkReviewResponse {
  processados: number;
  aprovados: number;
  rejeitados: number;
}
