import { apiFetchServer } from "@/lib/api-server";
import { ImoveisClient, ImovelRural, UnidadeProdutiva } from "./ImoveisClient";

export default async function ImoveisPage() {
    let initialImoveis: ImovelRural[] = [];
    let initialFazendas: UnidadeProdutiva[] = [];

    try {
        const [imoveisRes, fazendasRes] = await Promise.allSettled([
            apiFetchServer<ImovelRural[]>("imoveis/"),
            apiFetchServer<UnidadeProdutiva[]>("unidades-produtivas"),
        ]);

        if (imoveisRes.status === "fulfilled") initialImoveis = imoveisRes.value;
        if (fazendasRes.status === "fulfilled") initialFazendas = fazendasRes.value;
    } catch (e) {
        // Ignora erros
    }

    return (
        <ImoveisClient 
            initialImoveis={initialImoveis} 
            initialFazendas={initialFazendas} 
            initialActiveFazendaId={undefined} 
        />
    );
}
