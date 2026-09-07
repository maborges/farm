"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { AlertTriangle, CheckCircle, Clock, Eye, Filter, Flame, History, Waves, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

interface Alerta {
    id: string;
    fazenda_nome?: string;
    tipo: string;
    severidade: string;
    status: string;
    area_ha?: number;
    descricao?: string;
    fonte?: string;
    talhao_nome?: string;
    data_deteccao: string;
    data_resolucao?: string;
    resolucao_descricao?: string;
}

const SEV_COLOR: Record<string, string> = {
    BAIXA:  "bg-green-100 text-green-700",
    MEDIA:  "bg-yellow-100 text-yellow-700",
    ALTA:   "bg-orange-100 text-orange-700",
    CRITICA:"bg-red-100 text-red-700",
};

const TIPO_ICONS: Record<string, React.ReactNode> = {
    DESMATAMENTO: <AlertTriangle size={16} className="text-red-500" />,
    QUEIMADA:     <Flame size={16} className="text-orange-500" />,
    INUNDACAO:    <Waves size={16} className="text-blue-500" />,
    EROSAO:       <AlertTriangle size={16} className="text-amber-500" />,
    OUTRO:        <Eye size={16} className="text-muted-foreground" />,
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
    NOVO:       <Clock size={14} className="text-red-500" />,
    EM_ANALISE: <Clock size={14} className="text-blue-500" />,
    RESOLVIDO:  <CheckCircle size={14} className="text-green-500" />,
    IGNORADO:   <XCircle size={14} className="text-muted-foreground" />,
};
const FILTER_KEY = "ambiental.monitoramento.historico.filters";

export default function HistoricoAlertasPage() {
    const [filtroSev, setFiltroSev] = useState("todos");
    const [filtroTipo, setFiltroTipo] = useState("todos");
    const [busca, setBusca] = useState("");
    const [hydrated, setHydrated] = useState(false);

    useEffect(() => {
        const saved = window.localStorage.getItem(FILTER_KEY);
        if (saved) {
            try {
                const parsed = JSON.parse(saved) as { filtroSev?: string; filtroTipo?: string; busca?: string };
                // eslint-disable-next-line react-hooks/set-state-in-effect
                if (parsed.filtroSev) setFiltroSev(parsed.filtroSev);
                // eslint-disable-next-line react-hooks/set-state-in-effect
                if (parsed.filtroTipo) setFiltroTipo(parsed.filtroTipo);
                // eslint-disable-next-line react-hooks/set-state-in-effect
                if (parsed.busca) setBusca(parsed.busca);
            } catch {
                window.localStorage.removeItem(FILTER_KEY);
            }
        }
        setHydrated(true);
    }, []);

    useEffect(() => {
        if (!hydrated) return;
        window.localStorage.setItem(FILTER_KEY, JSON.stringify({ filtroSev, filtroTipo, busca }));
    }, [filtroSev, filtroTipo, busca, hydrated]);

    const { data: alertas = [], isLoading } = useQuery<Alerta[]>({
        queryKey: ["ambiental", "alertas", "historico"],
        queryFn: () => apiFetch("/ambiental/alertas"),
    });

    const filtrados = alertas.filter(a => {
        if (filtroSev !== "todos" && a.severidade !== filtroSev) return false;
        if (filtroTipo !== "todos" && a.tipo !== filtroTipo) return false;
        if (busca && !`${a.fazenda_nome} ${a.descricao} ${a.talhao_nome}`.toLowerCase().includes(busca.toLowerCase())) return false;
        return true;
    }).sort((a, b) => new Date(b.data_deteccao).getTime() - new Date(a.data_deteccao).getTime());

    function fmtDate(iso: string) {
        return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
    }

    return (
        <div className="w-full p-6 flex flex-col gap-6">
            <PageHeader
                title="Histórico de Alertas"
                description="Linha do tempo completa de alertas ambientais registrados."
                breadcrumbs={[
                    { label: "Dashboard", href: "/dashboard" },
                    { label: "Ambiental", href: "/dashboard/ambiental" },
                    { label: "Monitoramento" },
                    { label: "Histórico" },
                ]}
                icon={<History />}
                actions={(
                    <Button variant="outline" size="sm" asChild>
                        <Link href="/dashboard/ambiental/monitoramento/mapa">
                            Ver mapa
                        </Link>
                    </Button>
                )}
            />

            <Card>
                <CardContent className="flex flex-wrap items-center gap-3 p-4">
                    <div className="relative min-w-[220px] flex-1">
                        <Filter className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                        <Input className="h-9 pl-8 text-sm" placeholder="Buscar por fazenda, descrição..." value={busca} onChange={e => setBusca(e.target.value)} />
                    </div>
                    <Select value={filtroTipo} onValueChange={setFiltroTipo}>
                        <SelectTrigger className="h-9 w-[170px] text-sm"><SelectValue placeholder="Tipo" /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="todos">Todos os tipos</SelectItem>
                            {["DESMATAMENTO","QUEIMADA","INUNDACAO","EROSAO","OUTRO"].map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                        </SelectContent>
                    </Select>
                    <Select value={filtroSev} onValueChange={setFiltroSev}>
                        <SelectTrigger className="h-9 w-[170px] text-sm"><SelectValue placeholder="Severidade" /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="todos">Todas</SelectItem>
                            {["BAIXA","MEDIA","ALTA","CRITICA"].map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                        </SelectContent>
                    </Select>
                </CardContent>
            </Card>

            {isLoading ? (
                <div className="flex flex-col gap-3">{[1,2,3,4].map(i => <Skeleton key={i} className="h-20 w-full rounded-lg" />)}</div>
            ) : filtrados.length === 0 ? (
                <Card><CardContent className="flex flex-col items-center gap-2 py-10 text-center">
                    <CheckCircle className="text-green-400" />
                    <p className="text-sm text-muted-foreground">Nenhum alerta encontrado para os filtros selecionados.</p>
                </CardContent></Card>
            ) : (
                <div className="relative">
                    <div className="absolute left-5 top-0 bottom-0 w-px bg-border" />
                    <div className="flex flex-col gap-4">
                        {filtrados.map(a => (
                            <div key={a.id} className="relative pl-12">
                                <div className="absolute left-3 top-3 w-5 h-5 rounded-full bg-background border-2 border-border flex items-center justify-center">
                                    {TIPO_ICONS[a.tipo]}
                                </div>
                                <Card className="hover:shadow-sm transition-shadow">
                                    <CardContent className="py-3">
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="font-medium text-sm">{a.tipo}</span>
                                                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${SEV_COLOR[a.severidade]}`}>{a.severidade}</span>
                                                    <div className="flex items-center gap-1 text-xs text-muted-foreground">{STATUS_ICONS[a.status]} {a.status.replace("_", " ")}</div>
                                                </div>
                                                <p className="text-xs text-muted-foreground mt-0.5">
                                                    {a.fazenda_nome ?? "Fazenda não informada"}
                                                    {a.talhao_nome && ` — ${a.talhao_nome}`}
                                                    {a.area_ha && ` — ${a.area_ha} ha`}
                                                </p>
                                                {a.descricao && <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{a.descricao}</p>}
                                                {a.status === "RESOLVIDO" && a.resolucao_descricao && (
                                                    <p className="text-xs text-green-700 bg-green-50 rounded px-2 py-1 mt-1">{a.resolucao_descricao}</p>
                                                )}
                                            </div>
                                            <div className="text-right shrink-0">
                                                <p className="text-xs text-muted-foreground">{fmtDate(a.data_deteccao)}</p>
                                                {a.data_resolucao && <p className="text-xs text-green-600">Resolvido: {fmtDate(a.data_resolucao)}</p>}
                                                {a.fonte && <p className="text-xs text-muted-foreground">{a.fonte}</p>}
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
