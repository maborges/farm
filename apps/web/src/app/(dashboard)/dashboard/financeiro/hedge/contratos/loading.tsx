import { PageHeader } from "@/components/shared/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

export default function LoadingContratos() {
    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Contratos Futuros"
                description="Gestão de instrumentos de proteção de preço"
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Hedge" },
                    { label: "Contratos Futuros" }
                ]}
                actions={
                    <Button variant="outline" size="sm" className="rounded-sm" disabled>
                        <Plus className="size-4 mr-1" /> Novo Contrato
                    </Button>
                }
            />

            <Card className="rounded-sm">
                <CardContent className="p-4">
                    <Skeleton className="h-64 w-full rounded-sm" />
                </CardContent>
            </Card>
        </div>
    );
}
