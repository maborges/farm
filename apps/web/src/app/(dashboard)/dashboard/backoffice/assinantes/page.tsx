import { apiFetchServer } from "@/lib/api-server";
import AssinantesClient from "./assinantes-client";

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

interface AssinanteStats {
    total_assinantes: number;
    ativos: number;
    inativos: number;
    vencendo_30d: number;
    receita_mensal: number;
    por_plano: Record<string, number>;
    por_status: Record<string, number>;
}

export default async function AssinantesBackofficePage() {
    const [tenants, plans, stats] = await Promise.all([
        apiFetchServer<Tenant[]>("/backoffice/tenants"),
        apiFetchServer<Plan[]>("/backoffice/plans"),
        apiFetchServer<AssinanteStats>("/backoffice/tenants/stats").catch(() => null),
    ]);

    return (
        <AssinantesClient
            initialTenants={tenants}
            initialPlans={plans}
            initialStats={stats}
        />
    );
}
