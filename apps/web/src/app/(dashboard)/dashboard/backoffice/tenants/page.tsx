import { apiFetchServer } from "@/lib/api-server";
import TenantsClient from "./tenants-client";

interface Plan {
    id: string;
    nome: string;
    preco_mensal: number;
    preco_anual: number;
    ativo: boolean;
}

interface Tenant {
    id: string;
    nome: string;
    documento: string;
    data_cadastro: string;
    ativo: boolean;
    assinatura: {
        plano: string;
        plano_id: string;
        status: string;
    };
}

export default async function TenantsBackofficePage() {
    // Busca dados no servidor (RSC) usando cookies
    const tenants = await apiFetchServer<Tenant[]>("/backoffice/tenants");
    const plans = await apiFetchServer<Plan[]>("/backoffice/plans");

    return <TenantsClient initialTenants={tenants} initialPlans={plans} />;
}
