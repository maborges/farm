import { apiFetch } from "@/lib/api";

export type TipoEvidencia = "DOCUMENTO_PDF" | "FOTO_CAMPO" | "DADO_SATELITE" | "OUTRO";
export type SeveridadeNaoConformidade = "MENOR" | "MAIOR" | "CRITICA";
export type StatusNaoConformidade = "ABERTA" | "EM_ANALISE" | "EM_CORRECAO" | "RESOLVIDA" | "CANCELADA";
export type PrioridadePlanoAcao = "BAIXA" | "MEDIA" | "ALTA" | "URGENTE";
export type StatusPlanoAcao = "PENDENTE" | "EM_ANDAMENTO" | "CONCLUIDO" | "ATRASADO" | "CANCELADO";
export type StatusRelatorioESG = "RASCUNHO" | "EM_REVISAO" | "PUBLICADO" | "CANCELADO";
export type StatusPassaporte = "RASCUNHO" | "EM_VALIDACAO" | "PUBLICADO" | "REVOGADO";
export type TipoEventoPassaporte = "GERADO" | "VALIDADO" | "PUBLICADO" | "REVOGADO" | "ATUALIZADO";
export type TipoCertificacao = "ORGANICO" | "GLOBALGAP" | "REGENAGRI" | "ESG_INTERNO" | "OUTRO";

export interface ProgramaCertificacao {
  id: string;
  tenant_id: string;
  nome: string;
  tipo_certificacao: TipoCertificacao;
  status_programa: "ATIVO" | "INATIVO" | "SUSPENSO";
  data_inicio: string;
  data_fim?: string | null;
  organismo_certificador?: string | null;
  escopo?: string | null;
  observacoes?: string | null;
}

export type CreateProgramaCertificacaoPayload = Omit<ProgramaCertificacao, "id" | "tenant_id">;
export type UpdateProgramaCertificacaoPayload = Partial<CreateProgramaCertificacaoPayload>;

export interface EvidenciaCertificacao {
  id: string;
  tenant_id: string;
  programa_id: string;
  checklist_id?: string | null;
  criterio_id?: string | null;
  avaliacao_id?: string | null;
  propriedade_id?: string | null;
  imovel_rural_id?: string | null;
  propriedade_imovel_id?: string | null;
  responsavel_pessoa_id?: string | null;
  tipo_evidencia: TipoEvidencia;
  titulo: string;
  descricao: string;
  origem_tipo: string;
  origem_id: string;
  arquivo_url?: string | null;
  arquivo_hash?: string | null;
  snapshot_json?: Record<string, unknown> | null;
  snapshot_hash?: string | null;
  publico: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreateEvidenciaCertificacaoPayload {
  programa_id: string;
  tipo_evidencia: TipoEvidencia;
  titulo: string;
  descricao: string;
  origem_tipo: string;
  origem_id: string;
  publico: boolean;
}

export interface NaoConformidadeCertificacao {
  id: string;
  tenant_id: string;
  programa_id: string;
  checklist_id?: string | null;
  criterio_id?: string | null;
  avaliacao_id?: string | null;
  evidencia_id?: string | null;
  propriedade_id?: string | null;
  imovel_rural_id?: string | null;
  propriedade_imovel_id?: string | null;
  responsavel_pessoa_id?: string | null;
  titulo: string;
  descricao: string;
  severidade: SeveridadeNaoConformidade;
  status: StatusNaoConformidade;
  detectada_em: string;
  prazo_correcao?: string | null;
  resolvida_em?: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreateNaoConformidadeCertificacaoPayload {
  programa_id: string;
  titulo: string;
  descricao: string;
  severidade: SeveridadeNaoConformidade;
  status: StatusNaoConformidade;
  detectada_em: string;
  prazo_correcao?: string | null;
}

export interface PlanoAcaoCertificacao {
  id: string;
  tenant_id: string;
  programa_id: string;
  nao_conformidade_id?: string | null;
  evidencia_id?: string | null;
  responsavel_pessoa_id?: string | null;
  propriedade_id?: string | null;
  imovel_rural_id?: string | null;
  propriedade_imovel_id?: string | null;
  titulo: string;
  descricao: string;
  prioridade: PrioridadePlanoAcao;
  status: StatusPlanoAcao;
  prazo: string;
  concluido_em?: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreatePlanoAcaoCertificacaoPayload {
  programa_id: string;
  titulo: string;
  descricao: string;
  prioridade: PrioridadePlanoAcao;
  status: StatusPlanoAcao;
  prazo: string;
}

export type UpdateNaoConformidadeStatusPayload = {
  status: StatusNaoConformidade;
  resolvida_em?: string | null;
  prazo_correcao?: string | null;
};

export type UpdatePlanoAcaoStatusPayload = {
  status: StatusPlanoAcao;
  concluido_em?: string | null;
};

const BASE = "/certificacoes-esg";

export async function listarProgramas(): Promise<ProgramaCertificacao[]> {
  return apiFetch<ProgramaCertificacao[]>(`${BASE}/programas`);
}

export async function criarPrograma(payload: CreateProgramaCertificacaoPayload): Promise<ProgramaCertificacao> {
  return apiFetch<ProgramaCertificacao>(`${BASE}/programas`, { method: "POST", body: payload });
}

export async function atualizarPrograma(id: string, payload: UpdateProgramaCertificacaoPayload): Promise<ProgramaCertificacao> {
  return apiFetch<ProgramaCertificacao>(`${BASE}/programas/${id}`, { method: "PATCH", body: payload });
}

export async function listarEvidencias(): Promise<EvidenciaCertificacao[]> {
  return apiFetch<EvidenciaCertificacao[]>(`${BASE}/evidencias`);
}

export async function criarEvidencia(
  payload: CreateEvidenciaCertificacaoPayload,
): Promise<EvidenciaCertificacao> {
  return apiFetch<EvidenciaCertificacao>(`${BASE}/evidencias`, {
    method: "POST",
    body: payload,
  });
}

export async function listarNaoConformidades(): Promise<NaoConformidadeCertificacao[]> {
  return apiFetch<NaoConformidadeCertificacao[]>(`${BASE}/nao-conformidades`);
}

export async function criarNaoConformidade(
  payload: CreateNaoConformidadeCertificacaoPayload,
): Promise<NaoConformidadeCertificacao> {
  return apiFetch<NaoConformidadeCertificacao>(`${BASE}/nao-conformidades`, {
    method: "POST",
    body: payload,
  });
}

export async function listarPlanosAcao(): Promise<PlanoAcaoCertificacao[]> {
  return apiFetch<PlanoAcaoCertificacao[]>(`${BASE}/planos-acao`);
}

export async function criarPlanoAcao(
  payload: CreatePlanoAcaoCertificacaoPayload,
): Promise<PlanoAcaoCertificacao> {
  return apiFetch<PlanoAcaoCertificacao>(`${BASE}/planos-acao`, {
    method: "POST",
    body: payload,
  });
}

export async function atualizarStatusNaoConformidade(
  id: string,
  payload: UpdateNaoConformidadeStatusPayload,
): Promise<NaoConformidadeCertificacao> {
  return apiFetch<NaoConformidadeCertificacao>(`${BASE}/nao-conformidades/${id}/status`, {
    method: "PATCH",
    body: payload,
  });
}

export async function atualizarStatusPlanoAcao(
  id: string,
  payload: UpdatePlanoAcaoStatusPayload,
): Promise<PlanoAcaoCertificacao> {
  return apiFetch<PlanoAcaoCertificacao>(`${BASE}/planos-acao/${id}/status`, {
    method: "PATCH",
    body: payload,
  });
}

// Interfaces Relatórios ESG
export interface RelatorioESG {
  id: string;
  tenant_id: string;
  programa_id?: string | null;
  propriedade_id?: string | null;
  imovel_rural_id?: string | null;
  propriedade_imovel_id?: string | null;
  responsavel_pessoa_id?: string | null;
  titulo: string;
  periodo_inicio?: string | null;
  periodo_fim?: string | null;
  status: StatusRelatorioESG;
  versao: number;
  snapshot_json?: Record<string, unknown> | null;
  snapshot_hash?: string | null;
  publico: boolean;
  publicado_em?: string | null;
  cancelado_em?: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface RelatorioESGIndicador {
  id: string;
  tenant_id: string;
  relatorio_id: string;
  evidencia_id?: string | null;
  nome: string;
  categoria?: string | null;
  valor?: number | null;
  unidade?: string | null;
  score?: number | null;
  metodologia?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RelatorioESGEvidencia {
  id: string;
  tenant_id: string;
  relatorio_id: string;
  evidencia_id: string;
  created_at: string;
}

export interface PassaporteRastreabilidade {
  id: string;
  tenant_id: string;
  safra_id?: string | null;
  cultivo_id?: string | null;
  lote_rastreabilidade_id?: string | null;
  unidade_produtiva_id?: string | null;
  responsavel_pessoa_id?: string | null;
  titulo: string;
  status: StatusPassaporte;
  versao: number;
  snapshot_json?: Record<string, unknown> | null;
  snapshot_hash?: string | null;
  publico: boolean;
  public_token?: string | null;
  publicado_publicamente_em?: string | null;
  publicado_em?: string | null;
  revogado_em?: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface PassaporteRastreabilidadeEvento {
  id: string;
  tenant_id: string;
  passaporte_id: string;
  tipo_evento: TipoEventoPassaporte;
  titulo: string;
  descricao: string;
  ocorrido_em: string;
  origem_tipo: string;
  origem_id: string;
  snapshot_json?: Record<string, unknown> | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface PassaporteRastreabilidadeEvidencia {
  id: string;
  tenant_id: string;
  passaporte_id: string;
  evidencia_id: string;
  evento_id?: string | null;
  created_at: string;
}

export interface CreateRelatorioESGPayload {
  titulo: string;
  periodo_inicio?: string | null;
  periodo_fim?: string | null;
}

export interface UpdateRelatorioStatusPayload {
  status: StatusRelatorioESG;
}

export interface CreateRelatorioESGIndicadorPayload {
  nome: string;
  categoria?: string | null;
  valor?: number | null;
  unidade?: string | null;
  score?: number | null;
  metodologia?: string | null;
}

export interface CreatePassaporteRastreabilidadePayload {
  titulo: string;
}

export interface UpdatePassaporteStatusPayload {
  status: StatusPassaporte;
  publicado_em?: string | null;
  revogado_em?: string | null;
  snapshot_json?: Record<string, unknown> | null;
  snapshot_hash?: string | null;
  publico?: boolean | null;
}

export interface CreatePassaporteRastreabilidadeEventoPayload {
  tipo_evento: TipoEventoPassaporte;
  titulo: string;
  descricao: string;
  ocorrido_em: string;
  origem_tipo: string;
  origem_id: string;
}

export interface LinkEvidenciaPayload {
  evidencia_id: string;
}

// Funções Relatórios ESG
export async function listarRelatoriosESG(): Promise<RelatorioESG[]> {
  return apiFetch<RelatorioESG[]>(`${BASE}/relatorios-esg`);
}

export async function criarRelatorioESG(payload: CreateRelatorioESGPayload): Promise<RelatorioESG> {
  return apiFetch<RelatorioESG>(`${BASE}/relatorios-esg`, {
    method: "POST",
    body: payload,
  });
}

export async function atualizarStatusRelatorioESG(id: string, payload: UpdateRelatorioStatusPayload): Promise<RelatorioESG> {
  return apiFetch<RelatorioESG>(`${BASE}/relatorios-esg/${id}/status`, {
    method: "PATCH",
    body: payload,
  });
}

export async function listarIndicadoresRelatorioESG(id: string): Promise<RelatorioESGIndicador[]> {
  return apiFetch<RelatorioESGIndicador[]>(`${BASE}/relatorios-esg/${id}/indicadores`);
}

export async function adicionarIndicadorRelatorioESG(id: string, payload: CreateRelatorioESGIndicadorPayload): Promise<RelatorioESGIndicador> {
  return apiFetch<RelatorioESGIndicador>(`${BASE}/relatorios-esg/${id}/indicadores`, {
    method: "POST",
    body: payload,
  });
}

export async function listarEvidenciasRelatorioESG(id: string): Promise<EvidenciaCertificacao[]> {
  return apiFetch<EvidenciaCertificacao[]>(`${BASE}/relatorios-esg/${id}/evidencias`);
}

export async function vincularEvidenciaRelatorioESG(id: string, payload: LinkEvidenciaPayload): Promise<RelatorioESGEvidencia> {
  return apiFetch<RelatorioESGEvidencia>(`${BASE}/relatorios-esg/${id}/evidencias`, {
    method: "POST",
    body: payload,
  });
}

// Funções Passaportes Rastreabilidade
export async function listarPassaportes(): Promise<PassaporteRastreabilidade[]> {
  return apiFetch<PassaporteRastreabilidade[]>(`${BASE}/passaportes`);
}

export async function criarPassaporte(payload: CreatePassaporteRastreabilidadePayload): Promise<PassaporteRastreabilidade> {
  return apiFetch<PassaporteRastreabilidade>(`${BASE}/passaportes`, {
    method: "POST",
    body: payload,
  });
}

export async function atualizarStatusPassaporte(id: string, payload: UpdatePassaporteStatusPayload): Promise<PassaporteRastreabilidade> {
  return apiFetch<PassaporteRastreabilidade>(`${BASE}/passaportes/${id}/status`, {
    method: "PATCH",
    body: payload,
  });
}

export async function listarEventosPassaporte(id: string): Promise<PassaporteRastreabilidadeEvento[]> {
  return apiFetch<PassaporteRastreabilidadeEvento[]>(`${BASE}/passaportes/${id}/eventos`);
}

export async function adicionarEventoPassaporte(id: string, payload: CreatePassaporteRastreabilidadeEventoPayload): Promise<PassaporteRastreabilidadeEvento> {
  return apiFetch<PassaporteRastreabilidadeEvento>(`${BASE}/passaportes/${id}/eventos`, {
    method: "POST",
    body: payload,
  });
}

export async function listarEvidenciasPassaporte(id: string): Promise<EvidenciaCertificacao[]> {
  return apiFetch<EvidenciaCertificacao[]>(`${BASE}/passaportes/${id}/evidencias`);
}

export async function vincularEvidenciaPassaporte(id: string, payload: LinkEvidenciaPayload): Promise<PassaporteRastreabilidadeEvidencia> {
  return apiFetch<PassaporteRastreabilidadeEvidencia>(`${BASE}/passaportes/${id}/evidencias`, {
    method: "POST",
    body: payload,
  });
}
