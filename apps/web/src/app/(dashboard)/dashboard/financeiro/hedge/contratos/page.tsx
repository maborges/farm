import { apiFetchServer } from "@/lib/api-server";
import { ContratosClient } from "./ContratosClient";
import { ContratoFuturo } from "../types";
import { CommodityOption, SafraOption } from "./commodity-resolution";

type PageSearchParams = {
    safra_id?: string | string[];
};

export default async function ContratosPage({ searchParams }: { searchParams?: PageSearchParams }) {
    let initialContratos: ContratoFuturo[] = [];
    let safras: SafraOption[] = [];
    let commodities: CommodityOption[] = [];

    try {
        const [contratosRes, safrasRes, commoditiesRes] = await Promise.allSettled([
            apiFetchServer<ContratoFuturo[]>("/financeiro/hedge/contratos"),
            apiFetchServer<SafraOption[]>("/safras/"),
            apiFetchServer<CommodityOption[]>("/cadastros/commodities")
        ]);

        if (contratosRes.status === "fulfilled") initialContratos = contratosRes.value;
        if (safrasRes.status === "fulfilled") safras = safrasRes.value;
        if (commoditiesRes.status === "fulfilled") commodities = commoditiesRes.value;
    } catch (e) {
        // Ignora e deixa o Client component resolver
    }

    return (
        <ContratosClient 
            initialContratos={initialContratos}
            initialSafras={safras}
            initialCommodities={commodities}
        />
    );
}
