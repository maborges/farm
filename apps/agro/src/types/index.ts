/**
 * Tipos e contratos de domínio para o aplicativo DeepFarms Agro.
 */

export interface PrevisaoHoraria {
  hora: string;
  temperaturaC: number;
  probabilidadeChuvaPct: number;
  precipitacaoMm: number;
  umidadePct: number;
  ventoKmH: number;
  condicaoDescricao: string;
}

export interface PrevisaoDiaria {
  dataIso: string;
  diaSemana: string;
  tempMinC: number;
  tempMaxC: number;
  precipitacaoMm: number;
  probabilidadeChuvaPct: number;
  condicaoIcone: string;
}

export interface SnapshotClimaLocalidade {
  municipio: string;
  estadoUf: string;
  codigoIbge?: string;
  latitude: number;
  longitude: number;
  temperaturaAtualC: number;
  sensacaoTermicaC: number;
  umidadeRelativaPct: number;
  ventoVelocidadeKmH: number;
  descricaoCondicao: string;
  icone: string;
  fonteProvedor: string;
  dataAtualizacao: string;
  validoAte: string;
  horaria: PrevisaoHoraria[];
  semanal: PrevisaoDiaria[];
}

export interface IndicadorMercado {
  id: string;
  nome: string;
  unidade: string;
  pracaReferencia: string;
  fonteOficial: string;
  precoReferencia?: number;
  variacaoDiariaPct?: number;
  dataAtualizacao?: string;
  status: "DISPONIVEL" | "INDISPONIVEL" | "SOB_LICENCIAMENTO";
}

export interface CalculadoraConversaoUnidades {
  id: string;
  origemUnidade: string;
  destinoUnidade: string;
  fatorMultiplicador: number;
}
