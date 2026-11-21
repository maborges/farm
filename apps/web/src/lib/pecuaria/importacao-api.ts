import { apiFetch } from "@/lib/api";

export type TipoImportacaoPecuaria = "LOTES" | "ANIMAIS" | "PESAGENS";
export type ModoConflitoImportacao = "ATUALIZAR" | "IGNORAR";
export type AcaoLinhaImportacao = "CRIAR" | "ATUALIZAR" | "IGNORAR" | "ERRO";

export interface CampoMapeavelInfo {
  chave: string;
  rotulo: string;
  obrigatorio: boolean;
  descricao: string;
}

export interface LinhaImportacaoPreview {
  linha_numero: number;
  acao: AcaoLinhaImportacao;
  identificador: string;
  dados: Record<string, string | number | boolean | null | undefined>;
  erros: string[];
  avisos: string[];
}

export interface ImportacaoPreviewResponse {
  tipo: TipoImportacaoPecuaria;
  nome_arquivo: string;
  formato: string;
  colunas_arquivo: string[];
  mapeamento_aplicado: Record<string, string | null>;
  campos_disponiveis: CampoMapeavelInfo[];
  total_linhas: number;
  validas: number;
  a_criar: number;
  a_atualizar: number;
  a_ignorar: number;
  com_erro: number;
  avisos_total: number;
  preview_linhas: LinhaImportacaoPreview[];
  linhas_erro: LinhaImportacaoPreview[];
}

export interface ImportacaoExecucaoResponse {
  tipo: TipoImportacaoPecuaria;
  total_linhas: number;
  criados: number;
  atualizados: number;
  ignorados: number;
  erros: number;
  lotes_criados_automaticamente: number;
  lotes_atualizados: number;
  avisos_total: number;
  linhas_erro: LinhaImportacaoPreview[];
}

export interface ImportacaoRequestParams {
  tipo: TipoImportacaoPecuaria;
  unidade_produtiva_id: string;
  modo_conflito: ModoConflitoImportacao;
  criar_lotes_automaticamente: boolean;
  ignorar_linhas_com_erro?: boolean;
  mapeamento_colunas?: Record<string, string | null> | null;
  arquivo: File;
}

function buildImportacaoFormData(params: ImportacaoRequestParams): FormData {
  const formData = new FormData();
  formData.append("tipo", params.tipo);
  formData.append("unidade_produtiva_id", params.unidade_produtiva_id);
  formData.append("modo_conflito", params.modo_conflito);
  formData.append("criar_lotes_automaticamente", String(params.criar_lotes_automaticamente));
  if (params.ignorar_linhas_com_erro !== undefined) {
    formData.append("ignorar_linhas_com_erro", String(params.ignorar_linhas_com_erro));
  }
  if (params.mapeamento_colunas) {
    formData.append("mapeamento_colunas", JSON.stringify(params.mapeamento_colunas));
  }
  formData.append("arquivo", params.arquivo);
  return formData;
}

export async function baixarTemplatePecuaria(
  tipo: TipoImportacaoPecuaria,
  formato: "xlsx" | "csv"
): Promise<void> {
  const blob = await apiFetch<Blob>(
    `/pecuaria/importacoes/template/${tipo}?formato=${formato}`,
    { responseType: "blob" }
  );
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `modelo-importacao-${tipo.toLowerCase()}.${formato}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export async function previsualizarImportacaoPecuaria(
  params: ImportacaoRequestParams
): Promise<ImportacaoPreviewResponse> {
  return apiFetch<ImportacaoPreviewResponse>("/pecuaria/importacoes/preview", {
    method: "POST",
    body: buildImportacaoFormData(params),
  });
}

export async function executarImportacaoPecuaria(
  params: ImportacaoRequestParams
): Promise<ImportacaoExecucaoResponse> {
  return apiFetch<ImportacaoExecucaoResponse>("/pecuaria/importacoes/executar", {
    method: "POST",
    body: buildImportacaoFormData(params),
  });
}
