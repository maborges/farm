"use client";

import { useAnalisesSolo } from "@/hooks/use-agricola";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Beaker, Plus, TestTube2, AlertCircle, Eye, BrainCircuit } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { SoilDiagnosisDialog } from "@/components/agricola/soil-diagnosis-dialog";

export default function AnaliseSoloPage() {
    const { data: analises = [], isLoading } = useAnalisesSolo();
    const [selectedAnaliseId, setSelectedAnaliseId] = useState<string | null>(null);

    const analiseColumns: ColumnDef<any>[] = [
        {
            id: "talhao",
            header: "Talhão",
            accessorKey: "talhao_nome",
            sortable: true,
        },
        {
            id: "laboratorio",
            header: "Laboratório",
            accessorKey: "laboratorio",
            sortable: true,
        },
        {
            id: "data",
            header: "Data Coleta",
            accessorKey: "data_coleta",
            sortable: true,
            cell: (value) => value ? new Date(value).toLocaleDateString('pt-BR') : "-",
        },
        {
            id: "vencida",
            header: "Status",
            accessorKey: "vencida",
            cell: (value) => (
                <Badge variant={value ? "destructive" : "secondary"} className={cn("rounded-sm", !value && "bg-green-500/10 text-green-700 border-green-500/20")}>
                    {value ? "Vencida" : "Vigente"}
                </Badge>
            ),
        },
        {
            id: "actions",
            header: "Ações",
            cell: (analise) => (
                <div className="flex gap-2">
                    <Button 
                        variant="ghost" 
                        size="sm" 
                        className="hover:text-primary p-0 h-auto"
                        onClick={() => setSelectedAnaliseId(analise.id)}
                    >
                        <BrainCircuit className="mr-1 h-4 w-4" />
                        Diagnóstico
                    </Button>
                    <Button variant="ghost" size="sm" className="p-0 h-auto">
                        <Eye className="h-4 w-4" />
                    </Button>
                </div>
            )
        }
    ];

    return (
        <div className="flex flex-col gap-6">
            <PageHeader
                title="Análises de Solo"
                description="Gestão de laudos, fertilidade e corretivos."
                icon={<Beaker className="h-7 w-7 text-primary" />}
                actions={
                    <Button variant="outline" size="sm" className="border-primary text-primary rounded-sm">
                        <Plus className="mr-2 h-4 w-4" />
                        Nova Análise
                    </Button>
                }
            />

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                <Card className="border-0 bg-primary/5 rounded-sm">
                    <CardContent className="p-6">
                        <div className="flex items-center gap-3 mb-4">
                            <TestTube2 className="text-primary" size={20} />
                            <h3 className="font-bold">IA Agronômica</h3>
                        </div>
                        <p className="text-xs text-muted-foreground mb-4">
                            Converta laudos em tarefas de calagem e adubação automaticamente.
                        </p>
                    </CardContent>
                </Card>

                <Card variant="warning">
                    <CardContent className="p-6">
                        <div className="flex items-center gap-3 mb-4">
                            <AlertCircle className="text-alert-warning-icon" size={20} />
                            <h3 className="font-bold">Alertas de Solo</h3>
                        </div>
                        <p className="text-xs text-card-description mb-4">
                            {analises.filter(a => a.vencida).length} análise(s) com recomendação vencida.
                        </p>
                    </CardContent>
                </Card>
            </div>

            <Card className="border-0 shadow-sm rounded-sm">
                <CardContent className="p-6">
                    <DataTable
                        data={analises}
                        columns={analiseColumns}
                        searchable={true}
                        searchPlaceholder="Buscar por talhão..."
                        isLoading={isLoading}
                    />
                </CardContent>
            </Card>

            <SoilDiagnosisDialog 
                analiseId={selectedAnaliseId} 
                onClose={() => setSelectedAnaliseId(null)} 
            />
        </div>
    );
}
