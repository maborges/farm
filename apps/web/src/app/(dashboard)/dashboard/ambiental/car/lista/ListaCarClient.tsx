"use client";

import { useEffect, useState } from "react";
import { useAppStore } from "@/lib/stores/app-store";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { AlertCircle, CheckCircle, Clock, Leaf, Pencil, Plus, RefreshCw, Trash2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody, DialogDescription } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { PermissionGuard } from "@/components/auth/permission-guard";

export interface RegistroCAR {
    id: string;
    unidade_produtiva_id: string;
    imovel_rural_id?: string | null;
    fazenda_nome: string;
    codigo_car: string;
    uf: string;
    municipio?: string;
    status: string;
    area_total_ha?: number;
    area_app_ha?: number;
    area_rl_ha?: number;
    pendencias?: string;
    data_inscricao?: string;
    created_at: string;
    origem_cadastro?: boolean;
    unidade_nome?: string;
    origem_dados?: string;
    situacao_sicar?: string;
    data_ultima_consulta_sicar?: string | null;
}

type CarForm = {
    fazenda_nome: string; codigo_car: string; uf: string; municipio: string;
    area_total_ha: string; area_app_ha: string; area_rl_ha: string;
    pendencias: string; data_inscricao: string; status: string;
};

type CarPayload = Omit<CarForm, "area_total_ha" | "area_app_ha" | "area_rl_ha"> & {
    unidade_produtiva_id: string;
    imovel_rural_id?: string;
    area_total_ha?: number; area_app_ha?: number; area_rl_ha?: number;
};

const STATUS_CFG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    CADASTRADO: { label: "Cadastrado no imóvel", color: "bg-slate-100 text-slate-700 border-slate-200", icon: <Leaf size={11} /> },
    ATIVO:      { label: "Ativo",       color: "bg-green-100 text-green-700 border-green-200",   icon: <CheckCircle size={11} /> },
    PENDENTE:   { label: "Pendente",    color: "bg-yellow-100 text-yellow-700 border-yellow-200", icon: <Clock size={11} /> },
    EM_ANALISE: { label: "Em Análise",  color: "bg-blue-100 text-blue-700 border-blue-200",      icon: <Clock size={11} /> },
    CANCELADO:  { label: "Cancelado",   color: "bg-red-100 text-red-700 border-red-200",         icon: <XCircle size={11} /> },
    SUSPENSO:   { label: "Suspenso",    color: "bg-orange-100 text-orange-700 border-orange-200", icon: <AlertCircle size={11} /> },
};

function StatusBadge({ status }: { status: string }) {
    const cfg = STATUS_CFG[status] ?? { label: status, color: "bg-muted text-muted-foreground border-border", icon: null };
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${cfg.color}`}>
            {cfg.icon} {cfg.label}
        </span>
    );
}

const UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];
const EMPTY = { fazenda_nome: "", codigo_car: "", uf: "", municipio: "", area_total_ha: "", area_app_ha: "", area_rl_ha: "", pendencias: "", data_inscricao: "", status: "PENDENTE" };
const FILTER_KEY = "ambiental.car.lista.status";

export function ListaCarClient({ initialData }: { initialData: RegistroCAR[] }) {
    const activeFazendaId = useAppStore((state) => state.activeFazendaId);
    const unidadeSelecionada = useAppStore((state) => state.unidadesProdutivasAutorizadas.find((item) => item.id === state.activeFazendaId));
    const unidadesAutorizadas = useAppStore((state) => state.unidadesProdutivasAutorizadas);
    const qc = useQueryClient();
    const [filtroStatus, setFiltroStatus] = useState("todos");
    const [hydrated, setHydrated] = useState(false);
    const [showForm, setShowForm] = useState(false);
    const [editando, setEditando] = useState<RegistroCAR | null>(null);
    const [excluindo, setExcluindo] = useState<RegistroCAR | null>(null);
    const [form, setForm] = useState(EMPTY);

    useEffect(() => {
        const saved = window.localStorage.getItem(FILTER_KEY);
        // eslint-disable-next-line react-hooks/set-state-in-effect
        if (saved && saved !== "CADASTRADO") setFiltroStatus(saved);
        setHydrated(true);
    }, []);

    useEffect(() => {
        if (!hydrated) return;
        window.localStorage.setItem(FILTER_KEY, filtroStatus);
    }, [filtroStatus, hydrated]);

    const statusApi = filtroStatus !== "todos" && filtroStatus !== "CADASTRADO" ? filtroStatus : "todos";
    const qs = statusApi !== "todos" ? `?status=${statusApi}` : "";
    const { data: cars = [], isLoading } = useQuery<RegistroCAR[]>({
        queryKey: ["ambiental", "car", statusApi],
        queryFn: () => apiFetch(`/ambiental/car${qs}`),
        initialData: filtroStatus === "todos" ? initialData : undefined,
    });
    const { data: contextosFundiarios = [], isLoading: carregandoContextos, error: erroContexto } = useQuery<Array<{
        unidade_produtiva_id: string;
        unidade_nome: string;
        imovel_rural_id: string;
        nome: string;
        car_numero?: string | null;
        uf?: string | null;
        municipio?: string | null;
        area_total_ha?: number | null;
        area_app_ha?: number | null;
        area_rl_ha?: number | null;
    }>>({
        queryKey: ["ambiental", "contexto-fundiario-consolidado"],
        queryFn: () => apiFetch("/ambiental/contexto-fundiario"),
    });
    const carsDoCadastro = contextosFundiarios
        .filter((imovel) => imovel.car_numero && !cars.some((car) => car.imovel_rural_id === imovel.imovel_rural_id || car.codigo_car === imovel.car_numero))
        .map((imovel): RegistroCAR => ({
            id: `cadastro-${imovel.imovel_rural_id}`,
            unidade_produtiva_id: imovel.unidade_produtiva_id,
            imovel_rural_id: imovel.imovel_rural_id,
            fazenda_nome: imovel.nome,
            codigo_car: imovel.car_numero ?? "",
            uf: imovel.uf ?? unidadeSelecionada?.uf ?? "",
            municipio: imovel.municipio ?? unidadeSelecionada?.municipio ?? undefined,
            status: "CADASTRADO",
            area_total_ha: imovel.area_total_ha ?? undefined,
            area_app_ha: imovel.area_app_ha ?? undefined,
            area_rl_ha: imovel.area_rl_ha ?? undefined,
            created_at: "",
            origem_cadastro: true,
            unidade_nome: imovel.unidade_nome,
        }));
    const carsExibidos = [...cars, ...carsDoCadastro];

    const criarMut = useMutation({
        mutationFn: (d: CarPayload) => apiFetch("/ambiental/car", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["ambiental"] }); fechar(); toast.success("CAR registrado."); },
        onError: (e: Error) => toast.error(e.message),
    });
    const editarMut = useMutation({
        mutationFn: ({ id, d }: { id: string; d: CarPayload }) => apiFetch(`/ambiental/car/${id}`, { method: "PATCH", body: JSON.stringify(d) }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["ambiental"] }); fechar(); toast.success("CAR atualizado."); },
        onError: (e: Error) => toast.error(e.message),
    });
    const excluirMut = useMutation({
        mutationFn: (id: string) => apiFetch(`/ambiental/car/${id}`, { method: "DELETE" }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["ambiental"] }); setExcluindo(null); toast.success("CAR excluído."); },
        onError: (e: Error) => toast.error(e.message),
    });
    const consultarSicarMut = useMutation<RegistroCAR, Error, string>({
        mutationFn: (id) => apiFetch(`/ambiental/car/${id}/consultar-sicar`, { method: "POST" }),
        onSuccess: () => { qc.invalidateQueries({ queryKey: ["ambiental"] }); toast.success("Consulta SICAR concluída."); },
        onError: (e: Error) => toast.error(e.message),
    });

    function fechar() { setShowForm(false); setEditando(null); setForm(EMPTY); }
    function abrirEditar(c: RegistroCAR) {
        setEditando(c);
        setForm({ fazenda_nome: c.fazenda_nome, codigo_car: c.codigo_car, uf: c.uf, municipio: c.municipio ?? "", area_total_ha: c.area_total_ha?.toString() ?? "", area_app_ha: c.area_app_ha?.toString() ?? "", area_rl_ha: c.area_rl_ha?.toString() ?? "", pendencias: c.pendencias ?? "", data_inscricao: c.data_inscricao ?? "", status: c.status });
    }
    function salvar() {
        if (!activeFazendaId) { toast.error("Selecione uma fazenda antes de cadastrar o CAR."); return; }
        if (!editando && !contextosFundiarios[0]?.imovel_rural_id) { toast.error("Vincule um imóvel rural antes de registrar o CAR."); return; }
        if (!form.fazenda_nome || !form.codigo_car || !form.uf) { toast.error("Nome, código CAR e UF são obrigatórios."); return; }
        const p: CarPayload = {
            unidade_produtiva_id: activeFazendaId,
            ...(editando?.imovel_rural_id || contextosFundiarios[0]?.imovel_rural_id
                ? { imovel_rural_id: editando?.imovel_rural_id ?? contextosFundiarios[0].imovel_rural_id }
                : {}),
            fazenda_nome: form.fazenda_nome, codigo_car: form.codigo_car, uf: form.uf,
            status: form.status, municipio: form.municipio, pendencias: form.pendencias,
            data_inscricao: form.data_inscricao,
            ...(form.area_total_ha ? { area_total_ha: parseFloat(form.area_total_ha) } : {}),
            ...(form.area_app_ha ? { area_app_ha: parseFloat(form.area_app_ha) } : {}),
            ...(form.area_rl_ha ? { area_rl_ha: parseFloat(form.area_rl_ha) } : {}),
        };
        if (editando) editarMut.mutate({ id: editando.id, d: p });
        else criarMut.mutate(p);
    }

    return (
        <div className="w-full p-6 flex flex-col gap-6">
            <PageHeader
                title="Meus CARs"
                description="Visão consolidada dos CARs de todas as unidades produtivas."
                breadcrumbs={[
                    { label: "Dashboard", href: "/dashboard" },
                    { label: "Ambiental", href: "/dashboard/ambiental" },
                    { label: "CAR" },
                    { label: "Lista" },
                ]}
                icon={<Leaf />}
                actions={(
                    <PermissionGuard permission="ambiental:car:create">
                        <Button size="sm" onClick={() => { fechar(); setShowForm(true); }}>
                            <Plus data-icon="inline-start" />
                            Novo CAR
                        </Button>
                    </PermissionGuard>
                )}
            />

            <div role="status" className="rounded-sm border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-sm text-violet-800 dark:text-violet-200">
                <strong>Lista consolidada:</strong> os CARs exibidos pertencem a todas as unidades produtivas autorizadas, e cada cartão identifica sua unidade de origem.
            </div>

            <Card>
                <CardContent className="flex items-center gap-3 p-4">
                    <Select value={filtroStatus} onValueChange={setFiltroStatus}>
                        <SelectTrigger className="w-[180px] h-9 text-sm"><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="todos">Todos</SelectItem>
                            {Object.entries(STATUS_CFG).filter(([k]) => k !== "CADASTRADO").map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
                        </SelectContent>
                    </Select>
                    <Button variant="outline" size="sm" asChild>
                        <Link href="/dashboard/ambiental/car/importar">
                            <Leaf data-icon="inline-start" />
                            Registrar CAR
                        </Link>
                    </Button>
                </CardContent>
            </Card>

            {isLoading || carregandoContextos ? (
                <div className="flex flex-col gap-3">{[1,2,3].map(i => <Skeleton key={i} className="h-24 w-full rounded-lg" />)}</div>
            ) : erroContexto ? (
                <Card><CardContent className="py-8 text-center text-sm text-destructive">
                    Não foi possível carregar os imóveis vinculados às unidades. Tente atualizar a página.
                </CardContent></Card>
            ) : carsExibidos.length === 0 ? (
                <Card><CardContent className="flex flex-col items-center gap-3 py-12 text-center">
                    <Leaf className="text-muted-foreground/40" />
                    <p className="text-sm text-muted-foreground">Nenhum CAR cadastrado.</p>
                    <Button size="sm" variant="outline" onClick={() => setShowForm(true)}>
                        <Plus data-icon="inline-start" />
                        Registrar CAR
                    </Button>
                </CardContent></Card>
            ) : (
                <div className="grid gap-3 md:grid-cols-2">
                    {carsExibidos.map(c => (
                        <Card key={c.id} className="hover:shadow-sm transition-shadow">
                            <CardContent className="flex flex-col gap-2 py-4">
                                <div className="flex items-start justify-between gap-2">
                                    <div>
                                        <p className="font-semibold text-sm">{c.fazenda_nome}</p>
                                        <p className="text-xs text-muted-foreground">{c.unidade_nome ?? unidadesAutorizadas.find((unidade) => unidade.id === c.unidade_produtiva_id)?.nome ?? "Unidade produtiva"}</p>
                                        <p className="font-mono text-xs text-muted-foreground">{c.codigo_car}</p>
                                    </div>
                                    {!c.origem_cadastro && <div className="flex gap-1">
                                        <PermissionGuard permission="ambiental:car:edit">
                                            <Button size="icon-sm" variant="ghost" title="Consultar no SICAR" onClick={() => consultarSicarMut.mutate(c.id)} disabled={consultarSicarMut.isPending}>
                                                <RefreshCw className={consultarSicarMut.isPending ? "animate-spin" : ""} data-icon="inline-start" />
                                            </Button>
                                        </PermissionGuard>
                                        <PermissionGuard permission="ambiental:car:edit">
                                            <Button size="icon-sm" variant="ghost" onClick={() => abrirEditar(c)}>
                                                <Pencil data-icon="inline-start" />
                                            </Button>
                                        </PermissionGuard>
                                        <PermissionGuard permission="ambiental:car:delete">
                                            <Button size="icon-sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => setExcluindo(c)}>
                                                <Trash2 data-icon="inline-start" />
                                            </Button>
                                        </PermissionGuard>
                                    </div>}
                                </div>
                                <div className="flex items-center gap-2 flex-wrap">
                                    <StatusBadge status={c.status} />
                                    <span className="text-xs text-muted-foreground">{c.uf}{c.municipio ? ` — ${c.municipio}` : ""}</span>
                                </div>
                                {c.situacao_sicar && <p className="text-xs text-muted-foreground">SICAR: {c.situacao_sicar === "VALIDO" ? "consultado" : c.situacao_sicar === "ERRO_CONSULTA" ? "consulta com erro" : "não consultado"}{c.data_ultima_consulta_sicar ? ` em ${c.data_ultima_consulta_sicar}` : ""}.</p>}
                                {c.origem_cadastro && <p className="text-xs text-muted-foreground">Informação proveniente do cadastro do imóvel rural. Registre o CAR para acompanhar dados ambientais.</p>}
                                {c.area_total_ha && (
                                    <div className="flex gap-4 text-xs text-muted-foreground">
                                        <span>Total: <strong className="text-foreground">{c.area_total_ha} ha</strong></span>
                                        {c.area_app_ha && <span>APP: <strong className="text-foreground">{c.area_app_ha} ha</strong></span>}
                                        {c.area_rl_ha && <span>RL: <strong className="text-foreground">{c.area_rl_ha} ha</strong></span>}
                                    </div>
                                )}
                                {c.pendencias && <p className="text-xs text-orange-600 bg-orange-50 rounded px-2 py-1">{c.pendencias}</p>}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}

            <Dialog open={showForm || !!editando} onOpenChange={o => !o && fechar()}>
                <DialogContent className="max-h-[90vh] overflow-hidden p-0 sm:max-w-2xl">
                    <DialogHeader className="border-b px-4 py-4">
                        <div className="flex items-start gap-3">
                            <div className="rounded-lg border bg-muted/40 p-2">
                                <Leaf />
                            </div>
                            <div className="flex flex-col gap-1">
                                <DialogTitle>{editando ? "Editar CAR" : "Registrar CAR"}</DialogTitle>
                                <DialogDescription>Informe os dados do Cadastro Ambiental Rural para manter o controle por propriedade.</DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    <DialogBody className="grid gap-4 overflow-y-auto px-4 py-3 md:grid-cols-2">
                        <div className="md:col-span-2 flex flex-col gap-2"><Label>Fazenda <span className="text-destructive">*</span></Label>
                            <Input placeholder="Nome da fazenda" value={form.fazenda_nome} readOnly={!!unidadeSelecionada?.nome} onChange={e => setForm(f => ({ ...f, fazenda_nome: e.target.value }))} /></div>
                        <div className="md:col-span-2 flex flex-col gap-2"><Label>Código CAR <span className="text-destructive">*</span></Label>
                            <Input placeholder="UF-0000000-XXXX..." value={form.codigo_car} readOnly={!!editando?.codigo_car} onChange={e => setForm(f => ({ ...f, codigo_car: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>UF <span className="text-destructive">*</span></Label>
                            <Select value={form.uf} disabled={!!unidadeSelecionada?.uf} onValueChange={v => setForm(f => ({ ...f, uf: v }))}>
                                <SelectTrigger><SelectValue placeholder="UF" /></SelectTrigger>
                                <SelectContent>{UFS.map(u => <SelectItem key={u} value={u}>{u}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div className="flex flex-col gap-2"><Label>Município</Label>
                            <Input placeholder="Nome do município" value={form.municipio} readOnly={!!unidadeSelecionada?.municipio} onChange={e => setForm(f => ({ ...f, municipio: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>Status</Label>
                            <Select value={form.status} onValueChange={v => setForm(f => ({ ...f, status: v }))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                            <SelectContent>{Object.entries(STATUS_CFG).filter(([k]) => k !== "CADASTRADO").map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div className="flex flex-col gap-2"><Label>Data Inscrição</Label>
                            <Input type="date" value={form.data_inscricao} onChange={e => setForm(f => ({ ...f, data_inscricao: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>Área Total (ha)</Label>
                            <Input type="number" placeholder="0.00" value={form.area_total_ha} onChange={e => setForm(f => ({ ...f, area_total_ha: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>APP (ha)</Label>
                            <Input type="number" placeholder="0.00" value={form.area_app_ha} onChange={e => setForm(f => ({ ...f, area_app_ha: e.target.value }))} /></div>
                        <div className="flex flex-col gap-2"><Label>RL (ha)</Label>
                            <Input type="number" placeholder="0.00" value={form.area_rl_ha} onChange={e => setForm(f => ({ ...f, area_rl_ha: e.target.value }))} /></div>
                        <div className="md:col-span-2 flex flex-col gap-2"><Label>Pendências</Label>
                            <Textarea rows={2} placeholder="Descreva pendências se houver..." value={form.pendencias} onChange={e => setForm(f => ({ ...f, pendencias: e.target.value }))} /></div>
                    </DialogBody>
                    <DialogFooter className="border-t px-4 py-4">
                        <Button variant="outline" onClick={fechar}>Cancelar</Button>
                        <Button onClick={salvar} disabled={criarMut.isPending || editarMut.isPending}>
                            {criarMut.isPending || editarMut.isPending ? "Salvando..." : editando ? "Salvar" : "Registrar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <AlertDialog open={!!excluindo} onOpenChange={o => !o && setExcluindo(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Excluir CAR?</AlertDialogTitle>
                        <AlertDialogDescription>O registro <strong>{excluindo?.codigo_car}</strong> será excluído permanentemente.</AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => excluindo && excluirMut.mutate(excluindo.id)}>Excluir</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
