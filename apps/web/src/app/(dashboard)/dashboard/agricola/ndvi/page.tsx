"use client";

import { useAppStore } from "@/lib/stores/app-store";
import { PageHeader } from "@/components/shared";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Satellite, Calendar, Filter, Maximize2, Layers, Camera } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

type NDVIItem = {
    id: string;
    talhao: string;
    media: number;
    status: string;
    data: string;
    variacao: string;
};

const ndviColumns: ColumnDef<NDVIItem>[] = [
    {
        id: "talhao",
        header: "Talhão",
        accessorKey: "talhao",
        sortable: true,
    },
    {
        id: "media",
        header: "Média NDVI",
        accessorKey: "media",
        sortable: true,
        cell: (value) => (value as number).toFixed(2),
    },
    {
        id: "status",
        header: "Status",
        accessorKey: "status",
        sortable: true,
        cell: (value) => (
            <Badge
                variant="ghost"
                className={cn(
                    "border-none text-[9px] font-black uppercase px-2.5 shadow-sm",
                    value === "Excelente" ? "bg-green-500/10 text-green-700" :
                        value === "Atenção" ? "bg-red-500/10 text-red-700" :
                            "bg-blue-500/10 text-blue-700"
                )}
            >
                {value}
            </Badge>
        ),
    },
    {
        id: "variacao",
        header: "Variação",
        accessorKey: "variacao",
        sortable: true,
        cell: (value) => (
            <span className={value.startsWith('+') ? 'text-green-600 font-black' : 'text-red-600 font-black'}>
                {value}
            </span>
        ),
    },
];

export default function NDVIPage() {
    const { activeFazendaId } = useAppStore();
    const [selectedDate, setSelectedDate] = useState("Últimos 30 dias");

    const ndviHistory = [
        { id: "1", talhao: "Talhão 01", media: 0.82, status: "Excelente", data: "2024-03-05", variacao: "+2%" },
        { id: "2", talhao: "Talhão 02", media: 0.75, status: "Bom", data: "2024-03-05", variacao: "-1%" },
        { id: "3", talhao: "Talhão 03", media: 0.45, status: "Atenção", data: "2024-03-05", variacao: "-5%" },
        { id: "4", talhao: "Talhão 04", media: 0.88, status: "Excelente", data: "2024-03-04", variacao: "+1%" },
    ];

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="NDVI & Monitoramento Satelital"
                description="Acompanhe o vigor vegetativo e a saúde das suas culturas via satélite."
                icon={<Satellite className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "NDVI" }]}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => {}}>
                            <Calendar className="mr-2 size-4" />
                            {selectedDate}
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => {}}>
                            <Filter className="mr-2 size-4" />
                            Filtros
                        </Button>
                    </div>
                }
            />

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="agro-glass col-span-1 md:col-span-2 overflow-hidden border-0 shadow-2xl ring-1 ring-black/5 dark:ring-white/5 rounded-sm">
                    <CardHeader className="bg-primary/5 border-b border-primary/10 p-5">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm font-black flex items-center gap-2 uppercase tracking-widest text-primary/70">
                                <Maximize2 className="size-4" />
                                Monitoramento Espacial
                            </CardTitle>
                            <Badge variant="ghost" className="bg-primary/10 text-primary border-primary/20 font-black text-[10px]">SENTINEL-2 HUB</Badge>
                        </div>
                    </CardHeader>
                    <CardContent className="p-0 h-[450px] flex items-center justify-center bg-muted/10 relative">
                        <div className="text-center p-12 space-y-4">
                            <div className="relative inline-block">
                                <Satellite className="h-20 w-20 text-primary/20" />
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <div className="w-12 h-12 bg-primary/10 rounded-full animate-ping" />
                                </div>
                            </div>
                            <h3 className="text-lg font-black text-foreground">Digital Twin em Sincronização</h3>
                            <p className="text-xs text-muted-foreground font-medium max-w-xs mx-auto uppercase tracking-wider opacity-60">Processando camadas de refletância e índices de vegetação para a safra atual.</p>
                            <Button variant="outline" size="sm" className="mt-4 rounded-sm border-primary/30 text-primary font-bold hover:bg-primary/10">Recarregar HUB</Button>
                        </div>
                        {/* Enterprise Map Overlay */}
                        <div className="absolute top-6 right-6 agro-glass p-4 rounded-sm shadow-xl ring-1 ring-black/5 text-[10px] flex flex-col gap-3 z-10">
                            <h4 className="font-black uppercase tracking-widest text-muted-foreground/60 border-b border-primary/10 pb-2">Legenda NDVI</h4>
                            <div className="flex items-center gap-3 font-bold"><div className="w-3 h-3 bg-red-500 rounded-full shadow-[0_0_8px_rgba(239,68,68,0.4)]" /> <span>0.0 - 0.2 (Solo Nu)</span></div>
                            <div className="flex items-center gap-3 font-bold"><div className="w-3 h-3 bg-yellow-400 rounded-full shadow-[0_0_8px_rgba(250,204,21,0.4)]" /> <span>0.2 - 0.5 (Stress)</span></div>
                            <div className="flex items-center gap-3 font-bold"><div className="w-3 h-3 bg-green-500 rounded-full shadow-[0_0_8px_rgba(34,197,94,0.4)]" /> <span>0.5 - 1.0 (Vigor)</span></div>
                        </div>
                    </CardContent>
                </Card>

                <div className="flex flex-col gap-6">
                    <Card className="agro-glass border-0 shadow-lg ring-1 ring-black/5 rounded-sm overflow-hidden hover-lift">
                        <CardHeader className="p-6 pb-2">
                            <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Média da Propriedade</CardTitle>
                        </CardHeader>
                        <CardContent className="p-8 pt-0 flex flex-col items-center">
                            <div className="text-6xl font-black text-primary mb-3">0.72</div>
                            <Badge variant="secondary" className="bg-green-500/10 text-green-600 border-none px-3 font-black text-[10px] uppercase">Vigor Estável</Badge>
                            <p className="text-[11px] text-muted-foreground mt-6 text-center font-medium leading-relaxed">
                                Comparado ao mesmo período <br /> do ciclo anterior: <span className="text-green-600 font-black">+4.2%</span>
                            </p>
                        </CardContent>
                    </Card>

                    <Card className="agro-glass border-0 shadow-lg ring-1 ring-black/5 rounded-sm overflow-hidden hover-lift">
                        <CardHeader className="p-6 pb-2">
                            <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Alertas Críticos</CardTitle>
                        </CardHeader>
                        <CardContent className="p-6 pt-0">
                            <div className="flex flex-col gap-4">
                                <div className="flex items-center justify-between p-4 rounded-sm bg-red-500/5 border border-red-500/10 transition-all hover:bg-red-500/10">
                                    <div className="flex items-center gap-3">
                                        <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                                        <span className="text-sm font-black text-foreground">Talhão 03</span>
                                    </div>
                                    <Badge className="bg-red-500 border-none font-black text-[9px]">QUEDA 12%</Badge>
                                </div>
                                <div className="flex items-center justify-between p-4 rounded-sm bg-amber-500/5 border border-amber-500/10 transition-all hover:bg-amber-500/10">
                                    <div className="flex items-center gap-3">
                                        <div className="w-2 h-2 rounded-full bg-amber-500" />
                                        <span className="text-sm font-black text-foreground">Talhão 05</span>
                                    </div>
                                    <Badge className="bg-amber-500 border-none font-black text-[9px]">NUVEM</Badge>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            <Card className="agro-glass border-0 shadow-2xl ring-1 ring-black/5 rounded-sm overflow-hidden mt-2">
                <CardHeader className="bg-primary/5 border-b border-primary/10 p-6">
                    <div className="flex items-center gap-3 text-primary/70">
                        <Layers className="size-6" />
                        <CardTitle className="text-lg font-black uppercase tracking-widest">Histórico de Reflectância</CardTitle>
                    </div>
                </CardHeader>
                <CardContent className="p-6">
                    <DataTable
                        data={ndviHistory}
                        columns={ndviColumns}
                        searchable={true}
                        searchPlaceholder="Buscar por talhão..."
                        exportable={true}
                        exportFileName="ndvi-historico"
                        emptyMessage="Nenhum registro de NDVI encontrado"
                    />
                </CardContent>
            </Card>
        </div>
    );
}
