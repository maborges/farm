export interface NDVIAlertaResumo {
    talhao_id: string;
    talhao_nome: string;
    tipo: "QUEDA_VIGOR" | "ESTRESSE_HIDRICO" | "NUVEM_ALTA";
    severidade: "CRITICO" | "ATENCAO";
    titulo: string;
    detalhe: string;
    indice_atual: number | null;
    variacao_pct: number | null;
    cobertura_nuvens_pct: number | null;
}

export interface NDVITalhaoResumo {
    talhao_id: string;
    talhao_nome: string;
    tipo_area: string;
    area_hectares: number | null;
    unidade_produtiva_id: string;
    total_imagens: number;
    indice_atual: number | null;
    indice_anterior: number | null;
    variacao_pct: number | null;
    cobertura_nuvens_pct: number | null;
    ultima_captura: string | null;
    tendencia: "SUBINDO" | "CAINDO" | "ESTAVEL" | null;
    classificacao: string;
    satelite: string | null;
}

export interface NDVIResumoPropriedade {
    unidade_produtiva_id: string | null;
    periodo_dias: number | null;
    total_areas_produtivas: number;
    areas_monitoradas: number;
    total_registros: number;
    media_ndvi_propriedade: number | null;
    variacao_media_pct: number | null;
    classificacao_geral: string;
    sincronizacao_automatica_disponivel: boolean;
    talhoes: NDVITalhaoResumo[];
    alertas: NDVIAlertaResumo[];
}

export interface AreaProdutivaGeo {
    id: string;
    nome: string;
    tipo: string;
    unidade_produtiva_id?: string;
    area_hectares?: number | null;
    area_hectares_manual?: number | null;
    geometria?: GeoJSON.Geometry | GeoJSON.Feature | Record<string, unknown> | null;
}

export interface SafraTalhaoApiItem {
    id: string;
    area_id: string;
    nome?: string | null;
}

export interface NdviTalhaoOption {
    id: string;
    nome: string;
}

export interface NdviGeoFeatureProperties {
    id: string;
    nome: string;
    ndvi_color: string;
    indice_atual: number | null;
    classificacao: string;
    selected: boolean;
}

/**
 * Mapeia os vínculos de talhões da safra usando area_id (cadastros_areas_rurais.id),
 * deduplicando registros repetidos para o seletor de NDVI.
 */
export function mapSafraTalhoesParaNdvi(
    items: readonly SafraTalhaoApiItem[],
): NdviTalhaoOption[] {
    const vistos = new Set<string>();
    const options: NdviTalhaoOption[] = [];
    for (const item of items) {
        if (!item.area_id || vistos.has(item.area_id)) {
            continue;
        }
        vistos.add(item.area_id);
        options.push({
            id: item.area_id,
            nome: item.nome?.trim() || "Área sem nome",
        });
    }
    return options;
}

/**
 * Retorna a cor hexadecimal correspondente à faixa de vigor NDVI.
 */
export function getNdviFillColor(indice: number | null | undefined): string {
    if (indice == null || Number.isNaN(indice)) {
        return "#94a3b8";
    }
    if (indice < 0.2) {
        return "#ef4444";
    }
    if (indice < 0.4) {
        return "#f59e0b";
    }
    if (indice < 0.6) {
        return "#22c55e";
    }
    return "#059669";
}

/**
 * Mapeia a classificação agronômica textual para a variante visual de Badge.
 */
export function getNdviStatusBadgeVariant(
    classificacao: string,
): "success" | "info" | "warning" | "danger" | "secondary" {
    const tabela: Record<string, "success" | "info" | "warning" | "danger" | "secondary"> = {
        Excelente: "success",
        Moderado: "info",
        Atenção: "warning",
        Crítico: "danger",
        "Água / Nuvem": "secondary",
        "Sem dados": "secondary",
    };
    return tabela[classificacao] ?? "secondary";
}

/**
 * Formata a variação percentual entre leituras consecutivas com sinal explícito.
 */
export function formatNdviVariation(variacaoPct: number | null | undefined): string {
    if (variacaoPct == null || Number.isNaN(variacaoPct)) {
        return "—";
    }
    const sinal = variacaoPct > 0 ? "+" : "";
    return `${sinal}${variacaoPct.toFixed(1)}%`;
}

function extractPolygonGeometry(
    raw: AreaProdutivaGeo["geometria"],
): GeoJSON.Polygon | GeoJSON.MultiPolygon | null {
    if (!raw || typeof raw !== "object" || !("type" in raw)) {
        return null;
    }
    const candidate =
        raw.type === "Feature" && "geometry" in raw ? raw.geometry : raw;
    if (!candidate || typeof candidate !== "object" || !("type" in candidate)) {
        return null;
    }
    if (
        (candidate.type === "Polygon" || candidate.type === "MultiPolygon") &&
        "coordinates" in candidate &&
        Array.isArray(candidate.coordinates)
    ) {
        return candidate as GeoJSON.Polygon | GeoJSON.MultiPolygon;
    }
    return null;
}

/**
 * Constrói uma FeatureCollection GeoJSON das áreas produtivas com cor e métricas NDVI reais.
 */
export function buildNdviGeoJsonCollection(
    areas: readonly AreaProdutivaGeo[],
    resumoPorTalhao: ReadonlyMap<string, NDVITalhaoResumo>,
    selectedTalhaoId: string | null,
): GeoJSON.FeatureCollection<GeoJSON.Geometry, NdviGeoFeatureProperties> {
    const features: GeoJSON.Feature<GeoJSON.Geometry, NdviGeoFeatureProperties>[] = [];
    for (const area of areas) {
        const geometry = extractPolygonGeometry(area.geometria);
        if (!geometry) {
            continue;
        }
        const resumo = resumoPorTalhao.get(area.id);
        const indiceAtual = resumo?.indice_atual ?? null;
        features.push({
            type: "Feature",
            geometry,
            properties: {
                id: area.id,
                nome: area.nome,
                ndvi_color: getNdviFillColor(indiceAtual),
                indice_atual: indiceAtual,
                classificacao: resumo?.classificacao ?? "Sem dados",
                selected: area.id === selectedTalhaoId,
            },
        });
    }
    return { type: "FeatureCollection", features };
}
