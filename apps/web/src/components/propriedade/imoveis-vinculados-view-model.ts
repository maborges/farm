import type { VisaoTerritorialRead, VinculoTerritorialResumo } from "@/lib/hooks/use-territorial-visao";
import type { TerritoryReadView } from "@/types/global";

export interface LinkedImovelViewItem {
  id: string;
  nome: string;
  municipio: string | null;
  uf: string | null;
  areaTotalHa: string | number | null;
  matricula: string | null;
  car: string | null;
  statusDocumental: string | null;
  tipoVinculo: string | null;
  areaVinculada: string | number | null;
  percentualVinculado: string | number | null;
  principal: boolean;
}

export interface LinkedImoveisViewModel {
  items: LinkedImovelViewItem[];
  hasPrincipal: boolean;
  hasAmbiguity: boolean;
}

function withFallbackName(nome?: string | null, id?: string | null) {
  if (nome && nome.trim().length > 0) return nome;
  return id ? `Imóvel ${id.slice(0, 8)}` : "Imóvel Rural";
}

function buildItemFromVinculo(vinculo: VinculoTerritorialResumo): LinkedImovelViewItem | null {
  const imovel = vinculo.imovel_rural;
  if (!imovel) return null;

  return {
    id: imovel.id,
    nome: withFallbackName(imovel.nome, imovel.id),
    municipio: imovel.municipio ?? null,
    uf: imovel.uf ?? null,
    areaTotalHa: imovel.area_total_ha ?? null,
    matricula: imovel.numero_matricula ?? null,
    car: imovel.car_numero ?? null,
    statusDocumental: vinculo.status_documental ?? null,
    tipoVinculo: vinculo.tipo_vinculo ?? null,
    areaVinculada: vinculo.area_vinculada ?? null,
    percentualVinculado: vinculo.percentual_vinculado ?? null,
    principal: vinculo.vinculo_principal,
  };
}

function mergeItems(current: LinkedImovelViewItem, next: LinkedImovelViewItem): LinkedImovelViewItem {
  return {
    ...current,
    municipio: current.municipio ?? next.municipio,
    uf: current.uf ?? next.uf,
    areaTotalHa: current.areaTotalHa ?? next.areaTotalHa,
    matricula: current.matricula ?? next.matricula,
    car: current.car ?? next.car,
    statusDocumental: current.statusDocumental ?? next.statusDocumental,
    tipoVinculo: current.tipoVinculo ?? next.tipoVinculo,
    areaVinculada: current.areaVinculada ?? next.areaVinculada,
    percentualVinculado: current.percentualVinculado ?? next.percentualVinculado,
    principal: current.principal || next.principal,
  };
}

function fromVisaoTerritorial(data?: VisaoTerritorialRead | null): LinkedImoveisViewModel | null {
  if (!data) return null;

  const byId = new Map<string, LinkedImovelViewItem>();
  for (const vinculo of data.vinculos) {
    const item = buildItemFromVinculo(vinculo);
    if (!item) continue;
    const existing = byId.get(item.id);
    byId.set(item.id, existing ? mergeItems(existing, item) : item);
  }

  if (byId.size === 0 && data.imoveis_rurais.length > 0) {
    for (const imovel of data.imoveis_rurais) {
      byId.set(imovel.id, {
        id: imovel.id,
        nome: withFallbackName(imovel.nome, imovel.id),
        municipio: imovel.municipio ?? null,
        uf: imovel.uf ?? null,
        areaTotalHa: imovel.area_total_ha ?? null,
        matricula: imovel.numero_matricula ?? null,
        car: imovel.car_numero ?? null,
        statusDocumental: null,
        tipoVinculo: null,
        areaVinculada: null,
        percentualVinculado: null,
        principal: false,
      });
    }
  }

  const items = Array.from(byId.values()).sort((left, right) => {
    if (left.principal !== right.principal) return left.principal ? -1 : 1;
    return left.nome.localeCompare(right.nome, "pt-BR");
  });
  const principalCount = items.filter((item) => item.principal).length;

  return {
    items,
    hasPrincipal: principalCount > 0,
    hasAmbiguity: items.length > 1 && principalCount === 0,
  };
}

function fromTerritoryOverlay(territory?: TerritoryReadView | null): LinkedImoveisViewModel {
  const items: LinkedImovelViewItem[] = [];
  const byId = new Set<string>();

  const principal = territory?.imovel_principal;
  if (principal?.id) {
    byId.add(principal.id);
    const assoc = territory?.associacoes.find((item) => item.imovel_rural_id === principal.id);
    items.push({
      id: principal.id,
      nome: withFallbackName(principal.nome, principal.id),
      municipio: null,
      uf: null,
      areaTotalHa: principal.area_total_ha ?? null,
      matricula: principal.numero_matricula ?? null,
      car: principal.car_numero ?? null,
      statusDocumental: null,
      tipoVinculo: assoc?.tipo_vinculo ?? null,
      areaVinculada: null,
      percentualVinculado: null,
      principal: true,
    });
  }

  for (const imovel of territory?.imoveis_secundarios ?? []) {
    if (byId.has(imovel.id)) continue;
    const assoc = territory?.associacoes.find((item) => item.imovel_rural_id === imovel.id);
    items.push({
      id: imovel.id,
      nome: withFallbackName(imovel.nome, imovel.id),
      municipio: null,
      uf: null,
      areaTotalHa: imovel.area_total_ha ?? null,
      matricula: imovel.numero_matricula ?? null,
      car: imovel.car_numero ?? null,
      statusDocumental: null,
      tipoVinculo: assoc?.tipo_vinculo ?? null,
      areaVinculada: null,
      percentualVinculado: null,
      principal: assoc?.vinculo_principal ?? false,
    });
  }

  const principalCount = items.filter((item) => item.principal).length;
  return {
    items,
    hasPrincipal: principalCount > 0,
    hasAmbiguity: items.length > 1 && principalCount === 0,
  };
}

export function buildLinkedImoveisViewModel(
  territory?: TerritoryReadView | null,
  visaoTerritorial?: VisaoTerritorialRead | null,
): LinkedImoveisViewModel {
  return fromVisaoTerritorial(visaoTerritorial) ?? fromTerritoryOverlay(territory);
}

