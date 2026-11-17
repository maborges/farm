"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
    AlertTriangle,
    ArrowRight,
    Briefcase,
    Building2,
    CalendarClock,
    Check,
    Loader2,
    Search,
    Sprout,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";

interface CarteiraFazendaItem {
    unidade_produtiva_id: string;
    nome: string;
}

interface CarteiraTenantItem {
    tenant_id: string;
    nome_tenant: string;
    is_owner: boolean;
    perfil_nome: string | null;
    total_propriedades: number;
    safras_ativas: number;
    alertas_abertos: number;
    ultima_visita_tecnica: string | null;
    fazendas: CarteiraFazendaItem[];
}

interface CarteiraResumoResponse {
    total_tenants: number;
    total_propriedades: number;
    total_safras_ativas: number;
    total_alertas_abertos: number;
    tenants: CarteiraTenantItem[];
}

function formatDateBr(isoDate: string | null): string {
    if (!isoDate) return "—";
    const [year, month, day] = isoDate.split("-");
    if (!year || !month || !day) return isoDate;
    return `${day}/${month}/${year}`;
}

export function CarteiraClient() {
    const router = useRouter();
    const { tenant, switchTenantContext } = useAppStore();
    const [busca, setBusca] = useState("");
    const [switchingId, setSwitchingId] = useState<string | null>(null);

    const { data, isLoading, isError } = useQuery<CarteiraResumoResponse>({
        queryKey: ["my-tenants-resumo"],
        queryFn: () => apiFetch("/auth/my-tenants/resumo"),
        staleTime: 60_000,
    });

    const activeTenantId = String(tenant?.id ?? "");

    const tenantsFiltrados = useMemo(() => {
        const list = data?.tenants ?? [];
        const termo = busca.trim().toLowerCase();
        if (!termo) return list;
        return list.filter(
            (item) =>
                item.nome_tenant.toLowerCase().includes(termo) ||
                item.fazendas.some((f) => f.nome.toLowerCase().includes(termo)),
        );
    }, [data, busca]);

    async function handleAcessarFazenda(item: CarteiraTenantItem) {
        if (item.tenant_id === activeTenantId) {
            router.push("/dashboard");
            return;
        }
        setSwitchingId(item.tenant_id);
        try {
            await switchTenantContext(item.tenant_id);
            toast.success(`Contexto alterado para ${item.nome_tenant}`);
            router.push("/dashboard");
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Erro ao acessar fazenda.";
            toast.error(msg);
        } finally {
            setSwitchingId(null);
        }
    }

    if (isLoading) {
        return (
            <div className="space-y-4">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <Skeleton className="h-20 rounded-sm" />
                    <Skeleton className="h-20 rounded-sm" />
                    <Skeleton className="h-20 rounded-sm" />
                    <Skeleton className="h-20 rounded-sm" />
                </div>
                <Skeleton className="h-64 rounded-sm" />
            </div>
        );
    }

    if (isError || !data) {
        return (
            <Card className="rounded-sm">
                <CardContent className="py-8 text-center text-sm text-muted-foreground">
                    Não foi possível carregar o resumo da sua carteira no momento.
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <Card className="rounded-sm">
                    <CardContent className="pt-3 pb-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>Clientes / Contas</span>
                            <Briefcase className="size-3.5 text-primary" />
                        </div>
                        <p className="text-2xl font-bold mt-1">{data.total_tenants}</p>
                    </CardContent>
                </Card>

                <Card className="rounded-sm">
                    <CardContent className="pt-3 pb-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>Unidades Produtivas</span>
                            <Building2 className="size-3.5 text-primary" />
                        </div>
                        <p className="text-2xl font-bold mt-1">{data.total_propriedades}</p>
                    </CardContent>
                </Card>

                <Card className="rounded-sm">
                    <CardContent className="pt-3 pb-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>Safras Ativas</span>
                            <Sprout className="size-3.5 text-emerald-600" />
                        </div>
                        <p className="text-2xl font-bold mt-1 text-emerald-700 dark:text-emerald-400">
                            {data.total_safras_ativas}
                        </p>
                    </CardContent>
                </Card>

                <Card className="rounded-sm">
                    <CardContent className="pt-3 pb-3">
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                            <span>Alertas Abertos</span>
                            <AlertTriangle className="size-3.5 text-amber-600" />
                        </div>
                        <p className={cn(
                            "text-2xl font-bold mt-1",
                            data.total_alertas_abertos > 0
                                ? "text-amber-700 dark:text-amber-400"
                                : "text-muted-foreground",
                        )}>
                            {data.total_alertas_abertos}
                        </p>
                    </CardContent>
                </Card>
            </div>

            <Card className="rounded-sm">
                <CardContent className="pt-4 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <h3 className="font-semibold text-sm">Carteira de Propriedades Vinculadas</h3>
                        <div className="relative w-full sm:w-64">
                            <Search className="size-3.5 text-muted-foreground absolute left-2.5 top-2.5" />
                            <Input
                                value={busca}
                                onChange={(e) => setBusca(e.target.value)}
                                placeholder="Buscar produtor ou fazenda..."
                                className="h-8 pl-8 text-xs rounded-sm"
                            />
                        </div>
                    </div>

                    {tenantsFiltrados.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-8">
                            Nenhuma propriedade encontrada para o filtro informado.
                        </p>
                    ) : (
                        <div className="rounded-sm border overflow-x-auto">
                            <Table className="text-xs">
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="h-8">Produtor / Conta</TableHead>
                                        <TableHead className="h-8">Perfil</TableHead>
                                        <TableHead className="h-8 text-right">Unidades</TableHead>
                                        <TableHead className="h-8 text-right">Safras Ativas</TableHead>
                                        <TableHead className="h-8 text-right">Alertas</TableHead>
                                        <TableHead className="h-8 text-right">Última Visita</TableHead>
                                        <TableHead className="h-8 text-right" />
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {tenantsFiltrados.map((item) => {
                                        const isActive = item.tenant_id === activeTenantId;
                                        const isSwitching = switchingId === item.tenant_id;
                                        return (
                                            <TableRow key={item.tenant_id}>
                                                <TableCell className="font-medium">
                                                    <div className="flex items-center gap-2">
                                                        <span>{item.nome_tenant}</span>
                                                        {isActive && (
                                                            <Badge className="rounded-sm text-[10px] bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                                                                <Check className="size-2.5 mr-0.5" /> Atual
                                                            </Badge>
                                                        )}
                                                    </div>
                                                    {item.fazendas.length > 0 && (
                                                        <p className="text-[11px] text-muted-foreground truncate max-w-xs">
                                                            {item.fazendas.map((f) => f.nome).join(" · ")}
                                                        </p>
                                                    )}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant="outline" className="rounded-sm text-[11px]">
                                                        {item.perfil_nome ?? (item.is_owner ? "Proprietário" : "Membro")}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="text-right">{item.total_propriedades}</TableCell>
                                                <TableCell className="text-right font-medium">{item.safras_ativas}</TableCell>
                                                <TableCell className="text-right">
                                                    {item.alertas_abertos > 0 ? (
                                                        <Badge className="rounded-sm text-[11px] bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20">
                                                            {item.alertas_abertos}
                                                        </Badge>
                                                    ) : (
                                                        <span className="text-muted-foreground">0</span>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-right text-muted-foreground">
                                                    <span className="inline-flex items-center gap-1">
                                                        {item.ultima_visita_tecnica && <CalendarClock className="size-3" />}
                                                        {formatDateBr(item.ultima_visita_tecnica)}
                                                    </span>
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        className="rounded-sm h-7 text-xs"
                                                        disabled={isSwitching}
                                                        onClick={() => handleAcessarFazenda(item)}
                                                    >
                                                        {isSwitching ? (
                                                            <Loader2 className="size-3.5 mr-1 animate-spin" />
                                                        ) : (
                                                            <ArrowRight className="size-3.5 mr-1" />
                                                        )}
                                                        {isActive ? "Ir ao Painel" : "Acessar Fazenda"}
                                                    </Button>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })}
                                </TableBody>
                            </Table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
