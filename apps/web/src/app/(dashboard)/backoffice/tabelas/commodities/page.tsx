import { apiFetchServer } from "@/lib/api-server";
import { CommoditiesClient, Commodity } from "./CommoditiesClient";

export default async function BackofficeTabCommoditiesPage() {
    let initialData: Commodity[] = [];
    try {
        initialData = await apiFetchServer<Commodity[]>("/backoffice/tabelas/commodities");
    } catch (e) {
        // Ignora
    }

    return <CommoditiesClient initialData={initialData} />;
}
