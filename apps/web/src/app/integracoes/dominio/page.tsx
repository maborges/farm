import { Clock } from "lucide-react";
import { apiFetchServer } from "@/lib/api-server";
import { PageHeader } from "@/components/shared/page-header";
import { DominioClient, DominioConfig } from "./DominioClient";

export default async function DominioConfigPage() {
    let initialConfig: DominioConfig | null = null;
    try {
        const configs = await apiFetchServer<DominioConfig[]>("/contabilidade/integracoes?sistema=dominio");
        if (configs && configs.length > 0) {
            initialConfig = configs[0];
        }
    } catch (e) {
        // Silencia erro se a integração não estiver disponível
    }

    return (
        <div className="p-6 flex flex-col gap-6">
            <PageHeader
                title="Domínio Sistemas"
                description="Configuração de exportação contábil para o legado Domínio."
                icon={<Clock className="h-5 w-5" />}
                breadcrumbs={[
                    { label: "Integrações", href: "/integracoes" },
                    { label: "Domínio Sistemas" },
                ]}
            />
            <DominioClient initialConfig={initialConfig} />
        </div>
    );
}
