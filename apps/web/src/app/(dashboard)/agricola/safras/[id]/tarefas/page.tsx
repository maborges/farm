import { apiFetchServer } from "@/lib/api-server";
import { SafraTarefas } from "@/components/agricola/safra-tarefas";
import { ListTodo } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { getSafraLabel } from "@/lib/safra-label";

interface Safra {
    id: string;
    ano_safra: string;
    cultura: string;
    status: string;
}

interface PageProps {
    params: Promise<{ id: string }>;
}

export default async function SafraTarefasPage({ params }: PageProps) {
    const { id } = await params;
    
    let safra: Safra | null = null;
    try {
        safra = await apiFetchServer<Safra>(`/safras/${id}`);
    } catch (e) {
        console.error("Erro ao buscar safra no servidor:", e);
    }
    const safraLabel = getSafraLabel(safra);

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Manutenção de Tarefas"
                icon={<ListTodo className="text-primary" size={22} />}
                description={safraLabel}
            />

            <SafraTarefas 
                safraId={id} 
                isFullPage={true} 
            />
        </div>
    );
}
