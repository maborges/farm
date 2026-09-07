"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
    Map as MapIcon,
    Layers,
    Box,
    FileUp,
    Activity,
    Save,
    Settings2
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";

export default function ConfigMapasPage() {
    const queryClient = useQueryClient();

    const { data: configs, isLoading } = useQuery({
        queryKey: ["tenant-configs", "mapas"],
        queryFn: () => apiFetch<any[]>("/config/tenant?categoria=mapas")
    });

    const mutation = useMutation({
        mutationFn: (vars: { chave: string, valor: any }) =>
            apiFetch(`/config/tenant/mapas/${vars.chave}`, {
                method: "PUT",
                body: JSON.stringify({ valor: vars.valor })
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["tenant-configs", "mapas"] });
            toast.success("Configuração atualizada!");
        }
    });

    const toggleConfig = (chave: string, currentValue: boolean) => {
        mutation.mutate({ chave, valor: { ...configs?.find(c => c.chave === chave)?.valor, enabled: !currentValue } });
    };

    if (isLoading) return <div className="p-8 space-y-4"><Skeleton className="h-12 w-1/3" /><Skeleton className="h-64 w-full" /></div>;

    const getConfig = (chave: string) => configs?.find(c => c.chave === chave);

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Configurações Geoespaciais"
                description="Gerencie as funcionalidades avançadas do motor de mapas da sua fazenda."
                icon={<MapIcon className="h-8 w-8 text-primary" />}
            />

            <div className="grid gap-6">
                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader className="pb-4">
                        <div className="flex items-center gap-2 text-primary">
                            <Box size={18} />
                            <CardTitle className="text-lg font-bold">Visualização 3D</CardTitle>
                        </div>
                        <CardDescription>Habilita o motor de renderização de relevo e altimetria.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="flex items-center justify-between p-4 bg-background/50 rounded-sm border border-primary/5">
                            <div className="space-y-0.5">
                                <Label className="text-sm font-bold">Relevo Topográfico (Hillshading)</Label>
                                <p className="text-xs text-muted-foreground">Exibe sombras baseadas na elevação do terreno.</p>
                            </div>
                            <Switch
                                checked={getConfig("enable_3d_terrain")?.valor?.enabled}
                                onCheckedChange={() => toggleConfig("enable_3d_terrain", getConfig("enable_3d_terrain")?.valor?.enabled)}
                            />
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-primary">
                    <CardHeader className="pb-4">
                        <div className="flex items-center gap-2 text-primary">
                            <FileUp size={18} />
                            <CardTitle className="text-lg font-bold">Interoperabilidade</CardTitle>
                        </div>
                        <CardDescription>Configurações de importação de dados externos.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between p-4 bg-background/50 rounded-sm border border-primary/5">
                            <div className="space-y-0.5">
                                <Label className="text-sm font-bold">Importação KML / Shapefile</Label>
                                <p className="text-xs text-muted-foreground">Permite carregar perímetros de GPS externos.</p>
                            </div>
                            <Switch
                                checked={getConfig("kml_import")?.valor?.enabled}
                                onCheckedChange={() => toggleConfig("kml_import", getConfig("kml_import")?.valor?.enabled)}
                            />
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-l-[3px] border-l-orange-500">
                    <CardHeader className="pb-4">
                        <div className="flex items-center gap-2 text-orange-600">
                            <Activity size={18} />
                            <CardTitle className="text-lg font-bold">Telemetria de Máquinas</CardTitle>
                        </div>
                        <CardDescription>Análise histórica de movimentação da frota.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between p-4 bg-background/50 rounded-sm border border-primary/5">
                            <div className="space-y-0.5">
                                <Label className="text-sm font-bold">Rastro de Operação (Machine Trail)</Label>
                                <p className="text-xs text-muted-foreground">Exibe a linha de percurso das últimas 12 horas.</p>
                            </div>
                            <Switch
                                checked={getConfig("telemetry_trail")?.valor?.enabled}
                                onCheckedChange={() => toggleConfig("telemetry_trail", getConfig("telemetry_trail")?.valor?.enabled)}
                            />
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
