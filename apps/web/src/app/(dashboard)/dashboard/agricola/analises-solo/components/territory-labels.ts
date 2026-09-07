export interface TalhaoTerritorialRef {
    id: string;
    nome: string;
    unidade_produtiva_id?: string | null;
}

export interface UnidadeProdutivaRef {
    id: string;
    nome: string;
}

export function formatTalhaoLabel(
    talhao: TalhaoTerritorialRef,
    unidadesProdutivas: UnidadeProdutivaRef[],
): string {
    const unidade = unidadesProdutivas.find(
        item => item.id === talhao.unidade_produtiva_id,
    );
    return unidade ? `${unidade.nome} · ${talhao.nome}` : talhao.nome;
}
