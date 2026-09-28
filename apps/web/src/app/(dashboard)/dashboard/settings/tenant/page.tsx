import { apiFetchServer } from "@/lib/api-server";
import { TenantSettingsClient } from "./tenant-settings-client";

interface TenantData {
    tenant: {
        id: string;
        nome: string;
        documento: string;
        modulos_ativos: string[];
        max_usuarios: number;
        created_at: string;
        email_responsavel: string | null;
        telefone_responsavel: string | null;
        idioma_padrao: string | null;
        logo_url_grupo: string | null;
    };
    assinatura: {
        plano: string;
        valor: number;
        status: string;
        data_inicio: string;
        proximo_vencimento: string | null;
    } | null;
}

interface TenantInvoice {
    id: string;
    plano_nome: string;
    valor: number;
    data_vencimento: string;
    status: string;
    url_comprovante: string | null;
    justificativa_rejeicao: string | null;
}

export default async function TenantSettingsPage() {
    let initialTenant: TenantData | null = null;
    let initialInvoices: TenantInvoice[] = [];

    try {
        const [tenantRes, invoicesRes] = await Promise.allSettled([
            apiFetchServer<TenantData>("/billing/my-account"),
            apiFetchServer<TenantInvoice[]>("/billing/invoices"),
        ]);

        if (tenantRes.status === "fulfilled") initialTenant = tenantRes.value;
        if (invoicesRes.status === "fulfilled") initialInvoices = invoicesRes.value;
    } catch {
        // Ignora erros de fetch; o componente cliente renderiza estado vazio
    }

    if (!initialTenant) {
        return (
            <div className="p-6 flex flex-col gap-4 animate-in fade-in">
                <p className="text-sm text-muted-foreground">
                    Não foi possível carregar os dados do produtor. Tente novamente mais tarde.
                </p>
            </div>
        );
    }

    return (
        <TenantSettingsClient
            initialTenant={initialTenant}
            initialInvoices={initialInvoices}
        />
    );
}
