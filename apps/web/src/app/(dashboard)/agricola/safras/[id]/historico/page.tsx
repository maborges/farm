import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { History } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { apiFetchServer } from "@/lib/api-server";
import { getSafraLabel } from "@/lib/safra-label";

export const dynamic = "force-dynamic";

interface Safra {
    id: string;
    ano_safra: string;
    cultura: string | null;
    status: string;
}

interface SafraFaseHistorico {
    id: string;
    fase_anterior: string | null;
    fase_nova: string;
    observacao: string | null;
    created_at: string;
}

interface PageProps {
    params: Promise<{ id: string }>;
}

const FASE_LABEL: Record<string, string> = {
    PLANEJADA: "Planejamento",
    PREPARO_SOLO: "Preparo do Solo",
    PLANTIO: "Plantio",
    DESENVOLVIMENTO: "Desenvolvimento",
    COLHEITA: "Colheita",
    POS_COLHEITA: "Pós-Colheita",
    ENCERRADA: "Encerrada",
    CANCELADA: "Cancelada",
};

function formatDateTime(isoDate: string) {
    return format(new Date(isoDate), "dd/MM/yyyy HH:mm", { locale: ptBR });
}

async function fetchSafraWithHistory(safraId: string) {
    const [safra, historico] = await Promise.all([
        apiFetchServer<Safra>(`/safras/${safraId}`).catch(() => null),
        apiFetchServer<SafraFaseHistorico[]>(`/safras/${safraId}/historico-fases`).catch(() => []),
    ]);
    return { safra, historico };
}

export default async function SafraHistoricoPage({ params }: PageProps) {
    const { id } = await params;
    const { safra, historico } = await fetchSafraWithHistory(id);

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Histórico de Fases"
                icon={<History className="text-primary" size={22} />}
                description={getSafraLabel(safra)}
            />

            {historico.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center border border-dashed rounded-sm bg-muted/20">
                    <History className="size-8 text-muted-foreground/40 mb-2" />
                    <p className="text-sm text-muted-foreground">Nenhuma mudança de fase registrada.</p>
                </div>
            ) : (
                <Card className="rounded-sm">
                    <CardContent className="p-4">
                        <ol className="relative border-l border-border ml-3 space-y-5 py-2">
                            {historico.map((h) => (
                                <li key={h.id} className="ml-4">
                                    <div className="absolute -left-1.5 mt-1 size-3 rounded-full bg-primary" />
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {h.fase_anterior && (
                                            <>
                                                <Badge variant="outline" className="text-xs rounded-sm">
                                                    {FASE_LABEL[h.fase_anterior] ?? h.fase_anterior}
                                                </Badge>
                                                <span className="text-muted-foreground text-xs">→</span>
                                            </>
                                        )}
                                        <Badge className="text-xs rounded-sm">{FASE_LABEL[h.fase_nova] ?? h.fase_nova}</Badge>
                                        <span className="text-xs text-muted-foreground ml-auto">{formatDateTime(h.created_at)}</span>
                                    </div>
                                    {h.observacao && (
                                        <p className="text-sm text-muted-foreground mt-1">{h.observacao}</p>
                                    )}
                                </li>
                            ))}
                        </ol>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

