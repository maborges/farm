"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface PropriedadeVisaoResumo {
  id: string;
  nome: string;
  ativo: boolean;
  cpf_cnpj?: string | null;
  inscricao_estadual?: string | null;
}

export interface AreaOperacionalResumo {
  id: string;
  tenant_id: string;
  unidade_produtiva_id: string;
  parent_id?: string | null;
  tipo: string;
  nome: string;
  codigo?: string | null;
  area_hectares?: string | number | null;
  ativo: boolean;
}

export interface ExploracaoRuralResumo {
  id: string;
  tenant_id: string;
  propriedade_id: string;
  unidade_produtiva_id: string;
  natureza: string;
  data_inicio: string;
  data_fim?: string | null;
  numero_contrato?: string | null;
  valor_anual?: string | number | null;
  percentual_producao?: string | number | null;
  area_explorada_ha?: string | number | null;
  ativo: boolean;
  observacoes?: string | null;
}

export interface CartorioResumo {
  id: string;
  nome: string;
  comarca: string;
  uf: string;
}

export interface DocumentoFundiarioResumo {
  id: string;
  tipo: string;
  descricao?: string | null;
  numero_documento?: string | null;
  status: string;
  versao: number;
  data_emissao?: string | null;
  data_vencimento?: string | null;
  restrito: boolean;
  created_at: string;
}

export interface MatriculaFundiariaResumo {
  id: string;
  numero_matricula: string;
  cartorio_nome?: string | null;
  area_matricula_ha?: string | number | null;
  data_transmissao?: string | null;
  tipo_transmissao?: string | null;
  ativo: boolean;
}

export interface ImovelFundiarioResumo {
  id: string;
  tenant_id: string;
  nome: string;
  municipio: string;
  uf: string;
  area_total_ha: string | number;
  area_app_ha?: string | number | null;
  area_rl_ha?: string | number | null;
  nirf?: string | null;
  car_numero?: string | null;
  ccir_numero?: string | null;
  numero_matricula?: string | null;
  sigef_codigo?: string | null;
  cartorio?: CartorioResumo | null;
  documentos_resumo: DocumentoFundiarioResumo[];
  matriculas_resumo: MatriculaFundiariaResumo[];
}

export interface VinculoTerritorialResumo {
  id: string;
  tenant_id: string;
  tipo_vinculo: string;
  ativo: boolean;
  data_inicio: string;
  data_fim?: string | null;
  area_vinculada?: string | number | null;
  percentual_vinculado?: string | number | null;
  vinculo_principal: boolean;
  origem_documental: string;
  origem_referencia?: string | null;
  status_documental?: string | null;
  propriedade?: PropriedadeVisaoResumo | null;
  imovel_rural?: ImovelFundiarioResumo | null;
}

export interface VisaoTerritorialRead {
  propriedade: PropriedadeVisaoResumo;
  areas_operacionais: AreaOperacionalResumo[];
  exploracoes_rurais: ExploracaoRuralResumo[];
  imoveis_rurais: ImovelFundiarioResumo[];
  vinculos: VinculoTerritorialResumo[];
}

export interface VisaoFundiariaRead {
  imovel_rural: ImovelFundiarioResumo;
  propriedades_vinculadas: PropriedadeVisaoResumo[];
  vinculos: VinculoTerritorialResumo[];
}

export function useVisaoTerritorial(propriedadeId: string) {
  return useQuery({
    queryKey: ["visao-territorial", propriedadeId],
    queryFn: () => apiFetch<VisaoTerritorialRead>(`/propriedades/${propriedadeId}/visao-territorial`),
    enabled: !!propriedadeId,
    retry: false,
  });
}

export function useVisaoFundiaria(imovelId: string) {
  return useQuery({
    queryKey: ["visao-fundiaria", imovelId],
    queryFn: () => apiFetch<VisaoFundiariaRead>(`/imoveis-rurais/${imovelId}/visao-fundiaria`),
    enabled: !!imovelId,
    retry: false,
  });
}
