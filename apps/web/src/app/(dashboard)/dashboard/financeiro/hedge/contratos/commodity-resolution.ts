export type SafraOption = {
    id: string;
    ano_safra: string;
    cultura?: string | null;
};

export type CultivoOption = {
    commodity_id?: string | null;
    cultura: string;
};

export type CommodityOption = {
    id: string;
    nome: string;
    tipo: string;
    unidade_padrao: string;
    ativo?: boolean;
    codigo?: string;
};

function normalizeKey(value: string): string {
    return value
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-zA-Z0-9]/g, "")
        .toUpperCase();
}

export function resolveCommodityFromSafra(
    safra: SafraOption | undefined,
    commodities: CommodityOption[],
): CommodityOption | null {
    const cultura = safra?.cultura?.trim();
    if (!cultura) return null;

    const culturaKey = normalizeKey(cultura);
    return commodities.find((commodity) => {
        const nomeKey = normalizeKey(commodity.nome);
        const codigoKey = commodity.codigo ? normalizeKey(commodity.codigo) : "";
        return nomeKey === culturaKey || codigoKey === culturaKey;
    }) ?? null;
}

export function resolveCommodityFromCultivos(
    cultivos: CultivoOption[] | undefined,
    commodities: CommodityOption[],
): CommodityOption | null {
    if (!cultivos || cultivos.length === 0) return null;

    const commodityIds = Array.from(
        new Set(
            cultivos
                .map((cultivo) => cultivo.commodity_id)
                .filter((commodityId): commodityId is string => Boolean(commodityId)),
        ),
    );

    if (commodityIds.length === 1) {
        return commodities.find((commodity) => commodity.id === commodityIds[0]) ?? null;
    }

    if (commodityIds.length > 1) return null;

    return resolveCommodityFromSafra(
        {
            id: "",
            ano_safra: "",
            cultura: cultivos[0]?.cultura ?? null,
        },
        commodities,
    );
}

export function resolveCommodityFromSelection(
    commodityId: string | undefined,
    commodities: CommodityOption[],
): CommodityOption | null {
    if (!commodityId) return null;
    return commodities.find((commodity) => commodity.id === commodityId) ?? null;
}
