export type Severidade = "warning" | "danger";

export type TipoRisco =
  | "SEM_ABASTECIMENTO_RECENTE"
  | "OS_ABERTA_ANTIGA"
  | "MANUTENCAO_VENCIDA"
  | "DOCUMENTO_VENCIDO"
  | "CUSTO_ACIMA_MEDIA";

export interface FrotaResumo {
  total_equipamentos: number;
  ativos: number;
  parados: number;
  em_uso: number;
  em_manutencao: number;
  em_risco: number;
  os_abertas: number;
  manutencoes_vencidas: number;
  manutencoes_proximas: number;
  documentos_vencidos: number;
  custo_total_acumulado: number;
  proporcao_custo_preventivo_percentual: number;
  custo_operacional_total: number;
  custo_preventivo_total: number;
  custo_corretivo_total: number;
  hectares_totais_apontados: number;
  custo_por_hectare: number | null;
  indice_rentabilidade_operacional: number | null;
  equipamentos_ociosos: number;
}

export interface FrotaEquipamento {
  equipamento_id: string;
  nome: string;
  tipo: string;
  status: string;
  marca: string | null;
  modelo: string | null;
  unidade_produtiva_id: string | null;
  horimetro_atual: number | null;
  km_atual: number | null;
  custo_total: number;
  custo_abastecimento: number;
  custo_manutencao: number;
  custo_por_hora: number | null;
  custo_por_km: number | null;
  jornada_aberta?: boolean;
  os_abertas: number;
  manutencao_status: "OK" | "PROXIMA" | "VENCIDA" | "SEM_PLANO";
  documentos_vencidos: number;
  ultimo_abastecimento_em: string | null;
  dias_sem_abastecimento: number | null;
  risco_total: number;
  riscos: TipoRisco[];
}

export interface FrotaRankingItem {
  equipamento_id: string;
  equipamento_nome: string;
  tipo: string;
  status: string;
  custo_total: number;
  custo_abastecimento: number;
  custo_manutencao: number;
  os_abertas: number;
}

export interface FrotaAlerta {
  tipo: TipoRisco;
  titulo: string;
  severidade: Severidade;
  equipamento_id: string;
  equipamento_nome: string;
  detalhe: string;
  dias_desde_evento: number | null;
  data_referencia: string | null;
}

export interface FrotaUltimoAbastecimento {
  id: string;
  equipamento_id: string;
  equipamento_nome: string;
  data: string;
  tipo_combustivel: string;
  litros: number;
  custo_total: number;
  horimetro_na_data: number | null;
  km_na_data: number | null;
}

export interface FrotaJornadaDashboardItem {
  jornada_id: string;
  equipamento_id: string;
  equipamento_nome: string;
  operador_nome: string | null;
  tipo_operacao: string;
  data_inicio: string;
  data_fim: string | null;
  status: "ABERTA" | "FINALIZADA" | "CANCELADA";
  duracao_horas: number | null;
  horas_trabalhadas: number | null;
  km_trabalhados: number | null;
  custo_estimado: number | null;
  metrica_custo: "HORA" | "KM" | "INDISPONIVEL";
}

export interface FrotaDashboard {
  resumo: FrotaResumo;
  equipamentos: FrotaEquipamento[];
  ranking_maior_custo: FrotaRankingItem[];
  alertas_operacionais: FrotaAlerta[];
  ultimos_abastecimentos: FrotaUltimoAbastecimento[];
  ultimas_jornadas: FrotaJornadaDashboardItem[];
  gerado_em: string;
}

export interface FrotaConsumoAlerta {
  tipo: string;
  titulo: string;
  severidade: Severidade;
  equipamento_id: string;
  equipamento_nome: string;
  detalhe: string;
  data_referencia: string | null;
  dias_desde_evento: number | null;
}

export interface FrotaConsumoResumoCard {
  equipamentos_com_anomalia: number;
  total_alertas: number;
}

export interface FrotaConsumoRankingItem {
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

export interface FrotaConsumoDashboard {
  resumo: FrotaConsumoResumoCard;
  alertas: FrotaConsumoAlerta[];
  ranking_eficiencia: FrotaConsumoRankingItem[];
}

export interface FrotaDisponibilidadeResumo {
  disponiveis: number;
  em_uso: number;
  em_manutencao: number;
  bloqueados: number;
  checklist_pendente: number;
  nao_conformes: number;
  documentos_vencidos: number;
}

export interface FrotaDisponibilidadeDashboard {
  resumo: FrotaDisponibilidadeResumo;
}

export interface FrotaCustoResumoCard {
  custo_total_frota: number;
  custo_combustivel: number;
  custo_manutencao: number;
  custo_pecas_itens: number;
  custo_documental: number;
  custo_medio_por_equipamento: number;
  equipamento_mais_caro_nome: string | null;
  equipamento_mais_caro_total: number | null;
}

export interface FrotaCustoDashboard {
  resumo: FrotaCustoResumoCard;
}

export interface FrotaInteligenciaRankingItem {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  score_risco: number | null;
  nivel_risco: "BAIXO" | "MEDIO" | "ALTO" | "CRITICO" | null;
  detalhe: string | null;
}

export interface FrotaInteligenciaResumo {
  equipamentos_criticos: number;
  equipamentos_alto_risco: number;
}

export interface FrotaInteligenciaDashboard {
  resumo: FrotaInteligenciaResumo;
  ranking_risco: FrotaInteligenciaRankingItem[];
}

export interface FrotaAgriculturaResumo {
  horas_totais: number;
  km_totais: number;
  custo_estimado_total: number | null;
  operacao_mais_cara: string | null;
  operacao_mais_cara_custo: number | null;
  talhao_mais_caro: string | null;
  talhao_mais_caro_custo: number | null;
  equipamento_mais_usado: string | null;
  equipamento_mais_usado_valor: number | null;
  apontamentos_total: number;
  hectares_totais: number;
  quantidade_total: number;
  custo_apontamentos_total: number | null;
  produtividade_media_ha_hora: number | null;
  custo_medio_por_ha: number | null;
}

export interface FrotaAgriculturaApontamentoOperacaoItem {
  tipo_operacao: string;
  apontamentos: number;
  hectares_totais: number;
  horas_totais: number;
  custo_total: number | null;
  custo_por_ha: number | null;
  custo_por_hora: number | null;
  produtividade_ha_hora: number | null;
}

export interface FrotaAgriculturaApontamentoTalhaoItem {
  talhao_id: string | null;
  talhao_nome: string;
  safra_id: string | null;
  safra_nome: string | null;
  apontamentos: number;
  hectares_totais: number;
  horas_totais: number;
  custo_total: number | null;
  custo_por_ha: number | null;
  produtividade_ha_hora: number | null;
}

export interface FrotaAgriculturaApontamentoOperadorItem {
  operador_id: string | null;
  operador_nome: string;
  apontamentos: number;
  equipamentos_utilizados: number;
  horas_totais: number;
  hectares_totais: number;
  custo_total: number | null;
  custo_por_ha: number | null;
  produtividade_ha_hora: number | null;
}

export interface FrotaAgriculturaApontamentoEquipamentoItem {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  apontamentos: number;
  horas_totais: number;
  hectares_totais: number;
  custo_total: number | null;
  custo_por_ha: number | null;
  produtividade_ha_hora: number | null;
}

export interface FrotaAgriculturaDashboard {
  resumo: FrotaAgriculturaResumo;
  apontamentos_por_operacao: FrotaAgriculturaApontamentoOperacaoItem[];
  apontamentos_por_talhao: FrotaAgriculturaApontamentoTalhaoItem[];
  apontamentos_por_operador: FrotaAgriculturaApontamentoOperadorItem[];
  equipamentos_por_apontamento: FrotaAgriculturaApontamentoEquipamentoItem[];
}

export interface FrotaDetalheEquipamento {
  equipamento_id: string;
  nome: string;
  tipo: string;
  status: string;
  marca: string | null;
  modelo: string | null;
  unidade_produtiva_id: string | null;
  placa: string | null;
  numero_serie: string | null;
  patrimonio: string | null;
  combustivel: string | null;
  capacidade_tanque_l: number | null;
  potencia_cv: number | null;
  horimetro_atual: number | null;
  km_atual: number | null;
}

export interface FrotaDetalheIndicadores {
  periodo_dias_aplicado: number | null;
  total_os_abertas: number;
  total_os_concluidas: number;
  horas_trabalhadas_periodo: number | null;
  km_trabalhados_periodo: number | null;
  custo_total_manutencao: number;
  custo_total_abastecimento: number;
  custo_total_geral: number;
  custo_por_hora: number | null;
  custo_por_km: number | null;
  consumo_medio_km_l: number | null;
  consumo_medio_l_h: number | null;
  dias_sem_abastecimento: number | null;
  manutencao_status: "OK" | "PROXIMA" | "VENCIDA" | "SEM_PLANO";
}

export interface FrotaDetalheAbastecimento {
  id: string;
  data: string;
  tipo_combustivel: string;
  litros: number;
  preco_litro: number;
  custo_total: number;
  local: string;
  tanque_cheio: boolean;
  horimetro_na_data: number | null;
  km_na_data: number | null;
  nota_fiscal: string | null;
  observacoes: string | null;
}

export interface FrotaDetalheOs {
  id: string;
  numero_os: string;
  tipo: string;
  status: string;
  descricao_problema: string;
  diagnostico_tecnico: string | null;
  data_abertura: string;
  data_conclusao: string | null;
  horimetro_na_abertura: number | null;
  km_na_abertura: number | null;
  tecnico_responsavel: string | null;
  custo_total_pecas: number;
  custo_mao_obra: number;
  custo_total_os: number;
}

export interface FrotaDetalheRegistroManutencao {
  id: string;
  os_id: string | null;
  data_realizacao: string;
  tipo: string;
  descricao: string;
  custo_total: number;
  horimetro_na_data: number | null;
  km_na_data: number | null;
  tecnico_responsavel: string | null;
}

export interface FrotaDetalheJornada {
  id: string;
  operador_nome: string | null;
  unidade_produtiva_nome: string | null;
  safra_nome: string | null;
  talhao_nome: string | null;
  tipo_operacao: string;
  data_inicio: string;
  data_fim: string | null;
  status: "ABERTA" | "FINALIZADA" | "CANCELADA";
  horimetro_inicial: number | null;
  horimetro_final: number | null;
  km_inicial: number | null;
  km_final: number | null;
  duracao_horas: number | null;
  horas_trabalhadas: number | null;
  km_trabalhados: number | null;
  custo_estimado: number | null;
  metrica_custo: "HORA" | "KM" | "INDISPONIVEL";
  observacoes: string | null;
}

export interface FrotaDetalheDocumento {
  id: string;
  tipo: string;
  descricao: string | null;
  numero: string | null;
  data_vencimento: string | null;
  status: "VENCIDO" | "PROXIMO";
  dias_para_vencimento: number | null;
}

export interface FrotaDetalhePlano {
  id: string;
  descricao: string;
  frequencia_horas: number | null;
  frequencia_km: number | null;
  ultimo_registro_horas: number | null;
  ultimo_registro_km: number | null;
  status: "OK" | "PROXIMA" | "VENCIDA";
  restante_horas: number | null;
  restante_km: number | null;
}

export interface FrotaDetalheAlerta {
  tipo: TipoRisco;
  titulo: string;
  severidade: "warning" | "danger";
  detalhe: string;
  dias_desde_evento: number | null;
  data_referencia: string | null;
}

export interface FrotaDetalheResponse {
  equipamento: FrotaDetalheEquipamento;
  indicadores: FrotaDetalheIndicadores;
  ultimos_abastecimentos: FrotaDetalheAbastecimento[];
  ultimas_ordens_servico: FrotaDetalheOs[];
  ultimos_registros_manutencao: FrotaDetalheRegistroManutencao[];
  ultimas_jornadas: FrotaDetalheJornada[];
  documentos_alerta: FrotaDetalheDocumento[];
  planos_manutencao: FrotaDetalhePlano[];
  alertas: FrotaDetalheAlerta[];
  recomendacao_operacional: string;
  gerado_em: string;
}

export interface FrotaConsumoEquipamentoDetalhe {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  equipamento_status: string;
  litros_totais: number;
  custo_total_combustivel: number;
  custo_medio_litro: number | null;
  consumo_medio_l_h: number | null;
  consumo_medio_km_l: number | null;
  custo_por_hora: number | null;
  custo_por_km: number | null;
  variacao_media_frota_percent: number | null;
  variacao_media_historica_percent: number | null;
  eficiencia_score: number | null;
  metrica_principal: "HORIMETRO" | "KM" | "AMBOS" | "INDISPONIVEL";
  total_abastecimentos: number;
  ultimo_abastecimento_em: string | null;
  dias_sem_abastecimento: number | null;
}

export interface FrotaConsumoEquipamentoResponse {
  equipamento: FrotaConsumoEquipamentoDetalhe;
  alertas: FrotaConsumoAlerta[];
}

export interface FrotaDisponibilidadeEquipamento {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  equipamento_status: string;
  status_operacional: "DISPONIVEL" | "EM_USO" | "EM_MANUTENCAO" | "BLOQUEADO" | "CHECKLIST_PENDENTE" | "NAO_CONFORME" | "DOCUMENTO_VENCIDO";
  ultimo_checklist_em: string | null;
  checklist_pendente: boolean;
  nao_conforme: boolean;
  bloqueado_manual: boolean;
  motivo_status: string | null;
  motivo_bloqueio_manual: string | null;
  os_aberta: { numero_os: string; status: string } | null;
  documentos_vencidos: Array<{ id: string; tipo: string; data_vencimento: string | null }>;
  manutencao_preventiva_vencida: boolean;
}

export interface FrotaDisponibilidadeEquipamentoResponse {
  equipamento: FrotaDisponibilidadeEquipamento;
}

export interface FrotaCustoHistoricoItem {
  referencia: string;
  tipo: string;
  valor: number;
  data: string | null;
}

export interface FrotaCustoEquipamentoDetalhe {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
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

export interface FrotaCustoEquipamentoResponse {
  equipamento: FrotaCustoEquipamentoDetalhe;
  historico: FrotaCustoHistoricoItem[];
}

export interface FrotaInteligenciaFator {
  chave: string;
  titulo: string;
  peso: number;
  pontuacao: number;
  detalhe: string | null;
}

export interface FrotaInteligenciaEquipamento {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  equipamento_status: string;
  score_risco: number;
  nivel_risco: "BAIXO" | "MEDIO" | "ALTO" | "CRITICO";
  recomendacoes: string[];
  fatores: FrotaInteligenciaFator[];
}

export interface FrotaInteligenciaEquipamentoResponse {
  equipamento: FrotaInteligenciaEquipamento;
  ranking_risco_posicao: number | null;
}

export interface FrotaAgriculturaEquipamentoResumo {
  horas_totais: number;
  km_totais: number;
  custo_estimado_total: number | null;
  custo_hora_estimado: number | null;
  custo_km_estimado: number | null;
  operacao_mais_cara: string | null;
  operacao_mais_cara_custo: number | null;
  talhao_mais_caro: string | null;
  talhao_mais_caro_custo: number | null;
  equipamento_mais_usado: string | null;
  equipamento_mais_usado_valor: number | null;
}

export interface FrotaAgriculturaSafraItem {
  safra_id: string | null;
  safra_nome: string;
  horas_totais: number;
  km_totais: number;
  custo_estimado_total: number | null;
  custo_hora_estimado: number | null;
  custo_km_estimado: number | null;
  total_jornadas: number;
}

export interface FrotaAgriculturaTalhaoItem {
  talhao_id: string | null;
  talhao_nome: string;
  safra_id: string | null;
  safra_nome: string | null;
  horas_totais: number;
  km_totais: number;
  custo_estimado_total: number | null;
  custo_hora_estimado: number | null;
  custo_km_estimado: number | null;
  total_jornadas: number;
}

export interface FrotaAgriculturaOperacaoItem {
  tipo_operacao: string;
  horas_totais: number;
  km_totais: number;
  custo_estimado_total: number | null;
  custo_hora_estimado: number | null;
  custo_km_estimado: number | null;
  total_jornadas: number;
}

export interface FrotaAgriculturaEquipamentoResponse {
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  resumo: FrotaAgriculturaEquipamentoResumo;
  por_safra: FrotaAgriculturaSafraItem[];
  por_talhao: FrotaAgriculturaTalhaoItem[];
  por_operacao: FrotaAgriculturaOperacaoItem[];
}
