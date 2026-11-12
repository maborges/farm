import { apiFetchServer } from "@/lib/api-server";
import { CrmClient } from "./_components/CrmClient";
import { CRMStats, Estagio, KanbanData } from "./_components/types";

export const dynamic = "force-dynamic";

export const metadata = {
    title: "CRM - DeepFarms",
    description: "Gerencie leads e oportunidades comerciais no funil de vendas.",
};

export default async function CRMPage() {
    let initialStats: CRMStats | null = null;
    let initialPipeline: Estagio[] | null = null;
    let initialKanban: KanbanData | null = null;

    const [statsResult, pipelineResult, kanbanResult] = await Promise.allSettled([
        apiFetchServer<CRMStats>("/backoffice/crm/stats"),
        apiFetchServer<Estagio[]>("/backoffice/crm/pipeline?ativo=true"),
        apiFetchServer<KanbanData>("/backoffice/crm/kanban"),
    ]);

    if (statsResult.status === "fulfilled") {
        initialStats = statsResult.value;
    } else {
        console.error("Failed to prefetch crm stats on server:", statsResult.reason);
    }

    if (pipelineResult.status === "fulfilled") {
        initialPipeline = pipelineResult.value;
    } else {
        console.error("Failed to prefetch crm pipeline on server:", pipelineResult.reason);
    }

    if (kanbanResult.status === "fulfilled") {
        initialKanban = kanbanResult.value;
    } else {
        console.error("Failed to prefetch crm kanban on server:", kanbanResult.reason);
    }

    return (
        <CrmClient
            initialStats={initialStats}
            initialPipeline={initialPipeline ?? []}
            initialKanban={initialKanban}
            initialPlans={[]}
        />
    );
}
